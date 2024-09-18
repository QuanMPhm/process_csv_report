from unittest import TestCase, mock
import tempfile
import pandas
import pyarrow
import os
import uuid
import math
from textwrap import dedent

from process_report import process_report, util
from process_report.invoices import lenovo_invoice
from process_report.tests import util as test_utils


class TestGetInvoiceDate(TestCase):
    def test_get_invoice_date(self):
        # The month in sample data is not the same
        data = {"Invoice Month": ["2023-01", "2023-02", "2023-03"]}
        dataframe = pandas.DataFrame(data)

        invoice_date = process_report.get_invoice_date(dataframe)

        self.assertIsInstance(invoice_date, pandas.Timestamp)

        # Assert that the invoice_date is the first item
        expected_date = pandas.Timestamp("2023-01")
        self.assertEqual(invoice_date, expected_date)


class TestTimedProjects(TestCase):
    def setUp(self):
        # Without the dedent method, our data will have leading spaces which
        # messes up the first key. Also the '\' is imporant to ignore the first
        # new line we added so it's more readable in code.
        self.csv_data = dedent(
            """\
        Project,Start Date,End Date
        ProjectA,2022-09,2023-08
        ProjectB,2022-09,2023-09
        ProjectC,2023-09,2024-08
        ProjectD,2022-09,2024-08
        """
        )
        self.invoice_date = pandas.Timestamp("2023-09")

        self.csv_file = tempfile.NamedTemporaryFile(delete=False, mode="w")
        self.csv_file.write(self.csv_data)
        self.csv_file.close()

    def tearDown(self):
        os.remove(self.csv_file.name)

    def test_timed_projects(self):
        excluded_projects = process_report.timed_projects(
            self.csv_file.name, self.invoice_date
        )

        expected_projects = ["ProjectB", "ProjectC", "ProjectD"]
        self.assertEqual(excluded_projects, expected_projects)


class TestMergeCSV(TestCase):
    def setUp(self):
        self.header = ["ID", "Name", "Age"]
        self.data = [
            [1, "Alice", 25],
            [2, "Bob", 30],
            [3, "Charlie", 28],
        ]

        self.csv_files = []

        for _ in range(3):
            csv_file = tempfile.NamedTemporaryFile(
                delete=False, mode="w", suffix=".csv"
            )
            self.csv_files.append(csv_file)
            dataframe = pandas.DataFrame(self.data, columns=self.header)
            dataframe.to_csv(csv_file, index=False)
            csv_file.close()

    def tearDown(self):
        for csv_file in self.csv_files:
            os.remove(csv_file.name)

    def test_merge_csv(self):
        merged_dataframe = process_report.merge_csv(
            [csv_file.name for csv_file in self.csv_files]
        )

        expected_rows = len(self.data) * 3
        self.assertEqual(
            len(merged_dataframe), expected_rows
        )  # `len` for a pandas dataframe excludes the header row

        # Assert that the headers in the merged DataFrame match the expected headers
        self.assertListEqual(merged_dataframe.columns.tolist(), self.header)


class TestExportPICSV(TestCase):
    def setUp(self):
        data = {
            "Invoice Month": ["2023-01", "2023-01", "2023-01", "2023-01", "2023-01"],
            "Manager (PI)": ["PI1", "PI1", "PI1", "PI2", "PI2"],
            "Institution": ["BU", "BU", "BU", "HU", "HU"],
            "Project - Allocation": [
                "ProjectA",
                "ProjectB",
                "ProjectC",
                "ProjectD",
                "ProjectE",
            ],
            "Untouch Data Column": ["DataA", "DataB", "DataC", "DataD", "DataE"],
        }
        self.dataframe = pandas.DataFrame(data)
        self.invoice_month = data["Invoice Month"][0]

    @mock.patch("process_report.invoices.invoice.Invoice._filter_columns")
    def test_export_pi(self, mock_filter_cols):
        mock_filter_cols.return_value = self.dataframe

        output_dir = tempfile.TemporaryDirectory()
        pi_inv = test_utils.new_pi_specific_invoice(
            output_dir.name, invoice_month=self.invoice_month, data=self.dataframe
        )
        pi_inv.process()
        pi_inv.export()
        pi_csv_1 = f'{self.dataframe["Institution"][0]}_{self.dataframe["Manager (PI)"][0]} {self.dataframe["Invoice Month"][0]}.csv'
        pi_csv_2 = f'{self.dataframe["Institution"][3]}_{self.dataframe["Manager (PI)"][3]} {self.dataframe["Invoice Month"][3]}.csv'
        self.assertIn(pi_csv_1, os.listdir(output_dir.name))
        self.assertIn(pi_csv_2, os.listdir(output_dir.name))
        self.assertEqual(
            len(os.listdir(output_dir.name)),
            len(self.dataframe["Manager (PI)"].unique()),
        )

        pi_df = pandas.read_csv(output_dir.name + "/" + pi_csv_1)
        self.assertEqual(len(pi_df["Manager (PI)"].unique()), 1)
        self.assertEqual(
            pi_df["Manager (PI)"].unique()[0], self.dataframe["Manager (PI)"][0]
        )

        self.assertIn("ProjectA", pi_df["Project - Allocation"].tolist())
        self.assertIn("ProjectB", pi_df["Project - Allocation"].tolist())
        self.assertIn("ProjectC", pi_df["Project - Allocation"].tolist())

        pi_df = pandas.read_csv(output_dir.name + "/" + pi_csv_2)
        self.assertEqual(len(pi_df["Manager (PI)"].unique()), 1)
        self.assertEqual(
            pi_df["Manager (PI)"].unique()[0], self.dataframe["Manager (PI)"][3]
        )

        self.assertIn("ProjectD", pi_df["Project - Allocation"].tolist())
        self.assertIn("ProjectE", pi_df["Project - Allocation"].tolist())
        self.assertNotIn("ProjectA", pi_df["Project - Allocation"].tolist())
        self.assertNotIn("ProjectB", pi_df["Project - Allocation"].tolist())
        self.assertNotIn("ProjectC", pi_df["Project - Allocation"].tolist())


class TestAddInstituteProcessor(TestCase):
    def test_get_pi_institution(self):
        institute_map = {
            "harvard.edu": "Harvard University",
            "bu.edu": "Boston University",
            "bentley.edu": "Bentley",
            "mclean.harvard.edu": "McLean Hospital",
            "northeastern.edu": "Northeastern University",
            "childrens.harvard.edu": "Boston Children's Hospital",
            "meei.harvard.edu": "Massachusetts Eye & Ear",
            "dfci.harvard.edu": "Dana-Farber Cancer Institute",
            "bwh.harvard.edu": "Brigham and Women's Hospital",
            "bidmc.harvard.edu": "Beth Israel Deaconess Medical Center",
        }

        answers = {
            "q@bu.edu": "Boston University",
            "c@mclean.harvard.edu": "McLean Hospital",
            "b@harvard.edu": "Harvard University",
            "e@edu": "",
            "pi@northeastern.edu": "Northeastern University",
            "h@a.b.c.harvard.edu": "Harvard University",
            "c@a.childrens.harvard.edu": "Boston Children's Hospital",
            "d@a-b.meei.harvard.edu": "Massachusetts Eye & Ear",
            "e@dfci.harvard": "",
            "f@bwh.harvard.edu": "Brigham and Women's Hospital",
            "g@bidmc.harvard.edu": "Beth Israel Deaconess Medical Center",
        }

        add_institute_proc = test_utils.new_add_institution_processor()

        for pi_email, answer in answers.items():
            self.assertEqual(
                add_institute_proc._get_institution_from_pi(institute_map, pi_email),
                answer,
            )


class TestValidateAliasProcessor(TestCase):
    def test_validate_alias(self):
        alias_map = {"PI1": ["PI1_1", "PI1_2"], "PI2": ["PI2_1"]}
        test_data = pandas.DataFrame(
            {
                "Manager (PI)": ["PI1", "PI1_1", "PI1_2", "PI2_1", "PI2_1"],
            }
        )
        answer_data = pandas.DataFrame(
            {
                "Manager (PI)": ["PI1", "PI1", "PI1", "PI2", "PI2"],
            }
        )

        validate_pi_alias_proc = test_utils.new_validate_pi_alias_processor(
            data=test_data, alias_map=alias_map
        )
        validate_pi_alias_proc.process()
        self.assertTrue(answer_data.equals(validate_pi_alias_proc.data))


class TestRemoveNonbillablesProcessor(TestCase):
    def test_remove_nonbillables(self):
        pis = [uuid.uuid4().hex for x in range(10)]
        projects = [uuid.uuid4().hex for x in range(10)]
        nonbillable_pis = pis[:3]
        nonbillable_projects = projects[7:]
        billable_pis = pis[3:7]
        data = pandas.DataFrame({"Manager (PI)": pis, "Project - Allocation": projects})

        remove_nonbillables_proc = test_utils.new_remove_nonbillables_processor(
            data=data,
            nonbillable_pis=nonbillable_pis,
            nonbillable_projects=nonbillable_projects,
        )
        remove_nonbillables_proc.process()
        data = remove_nonbillables_proc.data
        data = data[data["Is Billable"]]
        self.assertTrue(data[data["Manager (PI)"].isin(nonbillable_pis)].empty)
        self.assertTrue(
            data[data["Project - Allocation"].isin(nonbillable_projects)].empty
        )
        self.assertTrue(data["Manager (PI)"].isin(billable_pis).all())


class TestValidateBillablePIProcessor(TestCase):
    def test_validate_billables(self):
        test_data = pandas.DataFrame(
            {
                "Manager (PI)": ["PI1", math.nan, "PI1", "PI2", "PI2"],
                "Project - Allocation": [
                    "ProjectA",
                    "ProjectB",
                    "ProjectC",
                    "ProjectD",
                    "ProjectE",
                ],
            }
        )
        self.assertEqual(1, len(test_data[pandas.isna(test_data["Manager (PI)"])]))
        validate_billable_pi_proc = test_utils.new_validate_billable_pi_processor(
            data=test_data
        )
        validate_billable_pi_proc.process()
        output_data = validate_billable_pi_proc.data
        output_data = output_data[~output_data["Missing PI"]]
        self.assertEqual(0, len(output_data[pandas.isna(output_data["Manager (PI)"])]))


class TestMonthUtils(TestCase):
    def test_get_month_diff(self):
        testcases = [
            (("2024-12", "2024-03"), 9),
            (("2024-12", "2023-03"), 21),
            (("2024-11", "2024-12"), -1),
            (("2024-12", "2025-03"), -3),
        ]
        for arglist, answer in testcases:
            self.assertEqual(util.get_month_diff(*arglist), answer)
        with self.assertRaises(ValueError):
            util.get_month_diff("2024-16", "2025-03")


class TestCredit0002(TestCase):
    def setUp(self):
        data = {
            "Invoice Month": [
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
            ],
            "Manager (PI)": [
                "PI1",
                "PI2",
                "PI3",
                "PI4",
                "PI4",
                "PI5",
                "PI7",
                "NewPI1",
                "NewPI1",
                "NewPI2",
                "NewPI2",
            ],
            "SU Type": [
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
            ],
            "Project - Allocation": [
                "ProjectA",
                "ProjectB",
                "ProjectC",
                "ProjectD",
                "ProjectE",
                "ProjectF",
                "ProjectG",
                "ProjectH",
                "ProjectI",
                "ProjectJ",
                "ProjectK",
            ],
            "Cost": [10, 100, 10000, 500, 100, 400, 200, 250, 250, 700, 700],
        }
        answer_df_dict = {
            "Invoice Month": [
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
            ],
            "Manager (PI)": [
                "PI1",
                "PI2",
                "PI3",
                "PI4",
                "PI4",
                "PI5",
                "PI7",
                "NewPI1",
                "NewPI1",
                "NewPI2",
                "NewPI2",
            ],
            "SU Type": [
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
                "CPU",
            ],
            "Project - Allocation": [
                "ProjectA",
                "ProjectB",
                "ProjectC",
                "ProjectD",
                "ProjectE",
                "ProjectF",
                "ProjectG",
                "ProjectH",
                "ProjectI",
                "ProjectJ",
                "ProjectK",
            ],
            "Cost": [10, 100, 10000, 500, 100, 400, 200, 250, 250, 700, 700],
            "Credit": [None, None, None, 100, None, 400, 200, 250, 250, 500, None],
            "Credit Code": [
                None,
                None,
                None,
                "0002",
                None,
                "0002",
                "0002",
                "0002",
                "0002",
                "0002",
                None,
            ],
            "Balance": [10, 100, 10000, 400, 100, 0, 0, 0, 0, 200, 700],
        }
        self.dataframe = pandas.DataFrame(data)
        self.dataframe["Credit"] = None
        self.dataframe["Credit Code"] = None
        self.dataframe["Balance"] = self.dataframe["Cost"]
        self.answer_dataframe = pandas.DataFrame(answer_df_dict)
        old_pi = [
            "PI,First Invoice Month,Initial Credits,1st Month Used,2nd Month Used",
            "PI1,2023-09,500,200,0",
            "PI2,2024-01,2000,0,0",
            "PI3,2024-01,2000,1000,500",
            "PI4,2024-02,1000,900,0",
            "PI5,2024-02,1000,300,500",
            "PI6,2024-02,1000,700,0",
            "PI7,2024-03,500,300,0",  # This as current month we're testing, new PIs should get $500
            "PI8,2024-04,1000,500,0",
        ]
        self.old_pi_df_answer = (
            pandas.DataFrame(
                {
                    "PI": [
                        "PI1",
                        "PI2",
                        "PI3",
                        "PI4",
                        "PI5",
                        "PI6",
                        "PI7",
                        "NewPI1",
                        "NewPI2",
                        "PI8",
                    ],
                    "First Invoice Month": [
                        "2023-09",
                        "2024-01",
                        "2024-01",
                        "2024-02",
                        "2024-02",
                        "2024-02",
                        "2024-03",
                        "2024-03",
                        "2024-03",
                        "2024-04",
                    ],
                    "Initial Credits": [
                        500,
                        2000,
                        2000,
                        1000,
                        1000,
                        1000,
                        500,
                        500,
                        500,
                        1000,
                    ],
                    "1st Month Used": [200, 0, 1000, 900, 300, 700, 200, 500, 500, 500],
                    "2nd Month Used": [0, 0, 500, 100, 400, 0, 0, 0, 0, 0],
                }
            )
            .astype(
                {
                    "Initial Credits": pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                    "1st Month Used": pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                    "2nd Month Used": pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                },
            )
            .sort_values(by="PI", ignore_index=True)
        )

        # Contains cases with new, one month old, two month old, older PI, and future PI that hasn't appeared in invoices yet
        # For each invoice month, test case where pi has 1 project, >1, and has spare credit
        old_pi_file = tempfile.NamedTemporaryFile(
            delete=False, mode="w+", suffix=".csv"
        )
        for pi in old_pi:
            old_pi_file.write(pi + "\n")
        self.old_pi_file = old_pi_file.name

        self.dataframe_no_gpu = pandas.DataFrame(
            {
                "Invoice Month": [
                    "2024-03",
                    "2024-03",
                    "2024-03",
                    "2024-03",
                    "2024-03",
                ],
                "Manager (PI)": ["PI1", "PI1", "PI1", "PI2", "PI2"],
                "SU Type": [
                    "GPU",
                    "OpenShift GPUA100SXM4",
                    "OpenStack GPUA100SXM4",
                    "OpenShift GPUA100SXM4",
                    "OpenStack GPUA100SXM4",
                ],
                "Cost": [500, 100, 100, 500, 500],
            }
        )
        self.dataframe_no_gpu["Credit"] = None
        self.dataframe_no_gpu["Credit Code"] = None
        self.dataframe_no_gpu["Balance"] = self.dataframe_no_gpu["Cost"]
        old_pi_no_gpu = [
            "PI,First Invoice Month,Initial Credits,1st Month Used,2nd Month Used",
            "OldPI,2024-03,500,200,0",
        ]
        old_pi_no_gpu_file = tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".csv"
        )
        for pi in old_pi_no_gpu:
            old_pi_no_gpu_file.write(pi + "\n")
        self.old_pi_no_gpu_file = old_pi_no_gpu_file.name
        self.no_gpu_df_answer = pandas.DataFrame(
            {
                "Invoice Month": [
                    "2024-03",
                    "2024-03",
                    "2024-03",
                    "2024-03",
                    "2024-03",
                ],
                "Manager (PI)": ["PI1", "PI1", "PI1", "PI2", "PI2"],
                "SU Type": [
                    "GPU",
                    "OpenShift GPUA100SXM4",
                    "OpenStack GPUA100SXM4",
                    "OpenShift GPUA100SXM4",
                    "OpenStack GPUA100SXM4",
                ],
                "Cost": [500, 100, 100, 500, 500],
                "Credit": [500, None, None, None, None],
                "Credit Code": ["0002", None, None, None, None],
                "Balance": [0.0, 100.0, 100.0, 500.0, 500.0],
            }
        )

    def tearDown(self):
        os.remove(self.old_pi_file)
        os.remove(self.old_pi_no_gpu_file)

    def test_apply_credit_0002(self):
        test_invoice = test_utils.new_billable_invoice(invoice_month="2024-03")
        old_pi_df = test_invoice._load_old_pis(self.old_pi_file)
        dataframe, updated_old_pi_df = test_invoice._apply_credits_new_pi(
            self.dataframe, old_pi_df
        )
        dataframe = dataframe.astype({"Credit": "float64", "Balance": "int64"})
        updated_old_pi_df = updated_old_pi_df.astype(
            dtype={
                "Initial Credits": pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                "1st Month Used": pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                "2nd Month Used": pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
            },
        ).sort_values(by=["PI"], ignore_index=True)
        self.assertTrue(self.answer_dataframe.equals(dataframe))
        self.assertTrue(self.old_pi_df_answer.equals(updated_old_pi_df))

    def test_no_gpu(self):
        test_invoice = test_utils.new_billable_invoice(invoice_month="2024-03")
        old_pi_df = test_invoice._load_old_pis(self.old_pi_no_gpu_file)
        dataframe, _ = test_invoice._apply_credits_new_pi(
            self.dataframe_no_gpu, old_pi_df
        )
        dataframe = dataframe.astype({"Credit": "float64", "Balance": "float64"})
        self.assertTrue(self.no_gpu_df_answer.equals(dataframe))

    def test_apply_credit_error(self):
        old_pi_df = pandas.DataFrame(
            {"PI": ["PI1"], "First Invoice Month": ["2024-04"]}
        )
        invoice_month = "2024-03"
        test_invoice = test_utils.new_billable_invoice()
        with self.assertRaises(SystemExit):
            test_invoice._get_pi_age(old_pi_df, "PI1", invoice_month)


class TestBUSubsidy(TestCase):
    def setUp(self):
        data = {
            "Invoice Month": [
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
                "2024-03",
            ],
            "Manager (PI)": ["PI1", "PI1", "PI2", "PI2", "PI3", "PI3", "PI4", "PI4"],
            "Institution": [
                "Boston University",
                "Boston University",
                "Boston University",
                "Boston University",
                "Harvard University",  # Test case for non-BU PIs
                "Harvard University",
                "Boston University",
                "Boston University",
            ],
            "Project - Allocation": [
                "ProjectA-e6413",
                "ProjectA-t575e6",  # Test case for project with >1 allocation
                "ProjectB-fddgfygg",
                "ProjectB-5t143t",
                "ProjectC-t14334",
                "ProjectD",  # Test case for correctly extracting project name
                "ProjectE-test-r25135",  # Test case for BU PI with >1 project
                "ProjectF",
            ],
            "Cost": [1050, 500, 100, 925, 10000, 1000, 1050, 100],
            "Credit": [
                1000,
                0,
                100,
                900,
                0,
                0,
                1000,
                0,
            ],  # Test cases where PI does/dones't have credits alreadys
            "Balance": [
                50,
                500,
                0,
                25,
                10000,
                1000,
                50,
                100,
            ],  # Test case where subsidy does/doesn't cover fully balance
        }
        self.dataframe = pandas.DataFrame(data)
        self.subsidy = 100

    def test_apply_BU_subsidy(self):
        test_invoice = test_utils.new_bu_internal_invoice(
            data=self.dataframe, subsidy_amount=self.subsidy
        )
        test_invoice.process()
        output_df = test_invoice.data.reset_index()

        self.assertTrue(
            set(
                [
                    process_report.INVOICE_DATE_FIELD,
                    "Project",
                    process_report.PI_FIELD,
                    process_report.COST_FIELD,
                    process_report.CREDIT_FIELD,
                    process_report.SUBSIDY_FIELD,
                    process_report.BALANCE_FIELD,
                ]
            ).issubset(output_df)
        )

        self.assertTrue(
            set(["PI1", "PI2", "PI4"]).issubset(output_df["Manager (PI)"].unique())
        )
        self.assertFalse("PI3" in output_df["Project"].unique())

        self.assertTrue(
            set(["ProjectA", "ProjectB", "ProjectE-test", "ProjectF"]).issubset(
                output_df["Project"].unique()
            )
        )
        self.assertFalse(
            set(["ProjectC-t14334", "ProjectC", "ProjectD"]).intersection(
                output_df["Project"].unique()
            )
        )

        self.assertEqual(4, len(output_df.index))
        self.assertEqual(1550, output_df.loc[0, "Cost"])
        self.assertEqual(1025, output_df.loc[1, "Cost"])
        self.assertEqual(1050, output_df.loc[2, "Cost"])
        self.assertEqual(100, output_df.loc[3, "Cost"])

        self.assertEqual(100, output_df.loc[0, "Subsidy"])
        self.assertEqual(25, output_df.loc[1, "Subsidy"])
        self.assertEqual(50, output_df.loc[2, "Subsidy"])
        self.assertEqual(50, output_df.loc[3, "Subsidy"])

        self.assertEqual(450, output_df.loc[0, "Balance"])
        self.assertEqual(0, output_df.loc[1, "Balance"])
        self.assertEqual(0, output_df.loc[2, "Balance"])
        self.assertEqual(50, output_df.loc[3, "Balance"])


class TestExportLenovo(TestCase):
    def setUp(self):
        data = {
            "Invoice Month": [
                "2023-01",
                "2023-01",
                "2023-01",
                "2023-01",
                "2023-01",
                "2023-01",
            ],
            "Project - Allocation": [
                "ProjectA",
                "ProjectB",
                "ProjectC",
                "ProjectD",
                "ProjectE",
                "ProjectF",
            ],
            "Institution": ["A", "B", "C", "D", "E", "F"],
            "SU Hours (GBhr or SUhr)": [1, 10, 100, 4, 432, 10],
            "SU Type": [
                "OpenShift GPUA100SXM4",
                "OpenShift GPUA100",
                "OpenShift GPUA100SXM4",
                "OpenStack GPUA100SXM4",
                "OpenStack CPU",
                "OpenStack GPUK80",
            ],
        }
        self.lenovo_invoice = lenovo_invoice.LenovoInvoice(
            "Lenovo", "2023-01", pandas.DataFrame(data)
        )
        self.lenovo_invoice.process()

    def test_process_lenovo(self):
        output_df = self.lenovo_invoice.data
        self.assertTrue(
            set(
                [
                    process_report.INVOICE_DATE_FIELD,
                    process_report.PROJECT_FIELD,
                    process_report.INSTITUTION_FIELD,
                    process_report.SU_TYPE_FIELD,
                    process_report.SU_HOURS_FIELD,
                    "SU Charge",
                    "Charge",
                ]
            ).issubset(output_df)
        )

        for i, row in output_df.iterrows():
            self.assertIn(
                row[process_report.SU_TYPE_FIELD],
                ["OpenShift GPUA100SXM4", "OpenStack GPUA100SXM4"],
            )
            self.assertEqual(
                row["Charge"], row["SU Charge"] * row["SU Hours (GBhr or SUhr)"]
            )


class TestUploadToS3(TestCase):
    @mock.patch("process_report.util.get_invoice_bucket")
    @mock.patch("process_report.util.get_iso8601_time")
    def test_upload_to_s3(self, mock_get_time, mock_get_bucket):
        mock_bucket = mock.MagicMock()
        mock_get_bucket.return_value = mock_bucket
        mock_get_time.return_value = "0"

        invoice_month = "2024-03"
        filenames = ["test-test", "test2.test", "test3"]
        sample_base_invoice = test_utils.new_base_invoice(invoice_month=invoice_month)

        answers = [
            (
                f"test-test {invoice_month}.csv",
                f"Invoices/{invoice_month}/test-test {invoice_month}.csv",
            ),
            (
                f"test-test {invoice_month}.csv",
                f"Invoices/{invoice_month}/Archive/test-test {invoice_month} 0.csv",
            ),
            (
                f"test2.test {invoice_month}.csv",
                f"Invoices/{invoice_month}/test2.test {invoice_month}.csv",
            ),
            (
                f"test2.test {invoice_month}.csv",
                f"Invoices/{invoice_month}/Archive/test2.test {invoice_month} 0.csv",
            ),
            (
                f"test3 {invoice_month}.csv",
                f"Invoices/{invoice_month}/test3 {invoice_month}.csv",
            ),
            (
                f"test3 {invoice_month}.csv",
                f"Invoices/{invoice_month}/Archive/test3 {invoice_month} 0.csv",
            ),
        ]

        for filename in filenames:
            sample_base_invoice.name = filename
            sample_base_invoice.export_s3(mock_bucket)

        for i, call_args in enumerate(mock_bucket.upload_file.call_args_list):
            self.assertTrue(answers[i] in call_args)


class TestNERCRates(TestCase):
    @mock.patch("process_report.util.load_institute_list")
    def test_flag_limit_new_pi_credit(self, mock_load_institute_list):
        mock_load_institute_list.return_value = [
            {"display_name": "BU", "mghpcc_partnership_start_date": "2024-02"},
            {"display_name": "HU", "mghpcc_partnership_start_date": "2024-6"},
            {"display_name": "NEU", "mghpcc_partnership_start_date": "2024-11"},
        ]
        sample_df = pandas.DataFrame(
            {
                "Institution": ["BU", "HU", "NEU", "MIT", "BC"],
            }
        )
        sample_inv = test_utils.new_billable_invoice(
            limit_new_pi_credit_to_partners=True
        )

        # When no partnerships are active
        sample_inv.invoice_month = "2024-01"
        output_df = sample_inv._filter_partners(sample_df)
        self.assertTrue(output_df.empty)

        # When some partnerships are active
        sample_inv.invoice_month = "2024-06"
        output_df = sample_inv._filter_partners(sample_df)
        answer_df = pandas.DataFrame({"Institution": ["BU", "HU"]})
        self.assertTrue(output_df.equals(answer_df))

        # When all partnerships are active
        sample_inv.invoice_month = "2024-12"
        output_df = sample_inv._filter_partners(sample_df)
        answer_df = pandas.DataFrame({"Institution": ["BU", "HU", "NEU"]})
        self.assertTrue(output_df.equals(answer_df))


class TestBaseInvoice(TestCase):
    def test_filter_exported_columns(self):
        test_invoice = pandas.DataFrame(columns=["C1", "C2", "C3", "C4", "C5"])
        answer_invoice = pandas.DataFrame(columns=["C1", "C3R", "C5R"])
        inv = test_utils.new_base_invoice(data=test_invoice)
        inv.export_columns_list = ["C1", "C3", "C5"]
        inv.exported_columns_map = {"C3": "C3R", "C5": "C5R"}
        result_invoice = inv._filter_columns()

        self.assertTrue(result_invoice.equals(answer_invoice))
