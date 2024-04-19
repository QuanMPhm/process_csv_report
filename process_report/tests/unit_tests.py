from unittest import TestCase
import tempfile
import pandas
import os
import math
from textwrap import dedent

from process_report import process_report


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


class TestRemoveNonBillables(TestCase):
    def setUp(self):
        data = {
            "Manager (PI)": ["PI1", "PI2", "PI3", "PI4", "PI5"],
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
        self.invoice_month = "2024-03"
        self.pi_to_exclude = ["PI2", "PI3"]
        self.projects_to_exclude = ["ProjectB", "ProjectD"]

    def test_remove_non_billables(self):
        billables_df = process_report.remove_non_billables(
            self.dataframe, self.pi_to_exclude, self.projects_to_exclude
        )
        result_df = process_report.export_billables(billables_df, "fake_invoice")[
            "dataframe"
        ]

        self.assertNotIn("PI2", result_df["Manager (PI)"].tolist())
        self.assertNotIn("PI3", result_df["Manager (PI)"].tolist())
        self.assertNotIn(
            "PI4", result_df["Manager (PI)"].tolist()
        )  # indirect because ProjectD was removed
        self.assertNotIn("ProjectB", result_df["Project - Allocation"].tolist())
        self.assertNotIn(
            "ProjectC", result_df["Project - Allocation"].tolist()
        )  # indirect because PI3 was removed
        self.assertNotIn("ProjectD", result_df["Project - Allocation"].tolist())

        self.assertIn("PI1", result_df["Manager (PI)"].tolist())
        self.assertIn("PI5", result_df["Manager (PI)"].tolist())
        self.assertIn("ProjectA", result_df["Project - Allocation"].tolist())
        self.assertIn("ProjectE", result_df["Project - Allocation"].tolist())

    def test_remove_billables(self):
        result_df = process_report.remove_billables(
            self.dataframe,
            self.pi_to_exclude,
            self.projects_to_exclude,
            "fake_invoice",
        )["dataframe"]

        self.assertIn("PI2", result_df["Manager (PI)"].tolist())
        self.assertIn("PI3", result_df["Manager (PI)"].tolist())
        self.assertIn("PI4", result_df["Manager (PI)"].tolist())
        self.assertIn("ProjectB", result_df["Project - Allocation"].tolist())
        self.assertIn("ProjectC", result_df["Project - Allocation"].tolist())
        self.assertIn("ProjectD", result_df["Project - Allocation"].tolist())

        self.assertNotIn("PI1", result_df["Manager (PI)"].tolist())
        self.assertNotIn("PI5", result_df["Manager (PI)"].tolist())
        self.assertNotIn("ProjectA", result_df["Project - Allocation"].tolist())
        self.assertNotIn("ProjectE", result_df["Project - Allocation"].tolist())


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

    def test_export_pi(self):
        output_dir = tempfile.TemporaryDirectory()
        process_report.export_pi_billables(
            self.dataframe, output_dir.name, self.invoice_month
        )

        pi_csv_1 = f'{self.dataframe["Institution"][0]}_{self.dataframe["Manager (PI)"][0]}_{self.dataframe["Invoice Month"][0]}.csv'
        pi_csv_2 = f'{self.dataframe["Institution"][3]}_{self.dataframe["Manager (PI)"][3]}_{self.dataframe["Invoice Month"][3]}.csv'
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


class TestGetInstitute(TestCase):
    def test_get_pi_institution(self):
        institute_map = {
            "harvard.edu": "Harvard University",
            "bu.edu": "Boston University",
            "bentley.edu": "Bentley",
            "mclean.harvard.edu": "McLean Hospital",
            "meei.harvard.edu": "Massachusetts Eye & Ear",
            "dfci.harvard.edu": "Dana-Farber Cancer Institute",
            "northeastern.edu": "Northeastern University",
        }

        self.assertEqual(
            process_report.get_institution_from_pi(institute_map, "quanmp@bu.edu"),
            "Boston University",
        )
        self.assertEqual(
            process_report.get_institution_from_pi(
                institute_map, "c@mclean.harvard.edu"
            ),
            "McLean Hospital",
        )
        self.assertEqual(
            process_report.get_institution_from_pi(institute_map, "b@harvard.edu"),
            "Harvard University",
        )
        self.assertEqual(
            process_report.get_institution_from_pi(institute_map, "fake"), ""
        )
        self.assertEqual(
            process_report.get_institution_from_pi(
                institute_map, "pi@northeastern.edu"
            ),
            "Northeastern University",
        )


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
            ],
            "Manager (PI)": ["PI1", "PI1", "PI2", "PI3", "PI4", "PI4"],
            "Project - Allocation": [
                "ProjectA",
                "ProjectB",
                "ProjectC",
                "ProjectD",
                "ProjectE",
                "ProjectF",
            ],
            "Cost": [10, 100, 10000, 5000, 800, 1000],
        }
        self.dataframe = pandas.DataFrame(data)
        old_pi = [
            "PI2,2023-09",
            "PI3,2024-02",
            "PI4,2024-03",
        ]  # Case with old and new pi in pi file
        old_pi_file = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".csv")
        for pi in old_pi:
            old_pi_file.write(pi + "\n")
        self.old_pi_file = old_pi_file.name

    def tearDown(self):
        os.remove(self.old_pi_file)

    def test_apply_credit_0002(self):
        dataframe = process_report.apply_credits_new_pi(
            self.dataframe, self.old_pi_file
        )

        self.assertTrue("Credit" in dataframe)
        self.assertTrue("Credit Code" in dataframe)
        self.assertTrue("Balance" in dataframe)

        non_credited_project = dataframe[pandas.isna(dataframe["Credit Code"])]
        credited_projects = dataframe[dataframe["Credit Code"] == "0002"]

        self.assertEqual(2, len(non_credited_project))
        self.assertEqual(
            non_credited_project.loc[2, "Cost"], non_credited_project.loc[2, "Balance"]
        )
        self.assertEqual(
            non_credited_project.loc[3, "Cost"], non_credited_project.loc[3, "Balance"]
        )

        self.assertEqual(4, len(credited_projects.index))
        self.assertTrue("PI2" not in credited_projects["Manager (PI)"].unique())
        self.assertTrue("PI3" not in credited_projects["Manager (PI)"].unique())

        self.assertEqual(10, credited_projects.loc[0, "Credit"])
        self.assertEqual(100, credited_projects.loc[1, "Credit"])
        self.assertEqual(800, credited_projects.loc[4, "Credit"])
        self.assertEqual(200, credited_projects.loc[5, "Credit"])

        self.assertEqual(0, credited_projects.loc[0, "Balance"])
        self.assertEqual(0, credited_projects.loc[1, "Balance"])
        self.assertEqual(0, credited_projects.loc[4, "Balance"])
        self.assertEqual(800, credited_projects.loc[5, "Balance"])


class TestValidateBillables(TestCase):
    def setUp(self):
        data = {
            "Manager (PI)": ["PI1", math.nan, "PI1", "PI2", "PI2"],
            "Project - Allocation": [
                "ProjectA",
                "ProjectB",
                "ProjectC",
                "ProjectD",
                "ProjectE",
            ],
        }
        self.dataframe = pandas.DataFrame(data)

    def test_validate_billables(self):
        self.assertEqual(
            1, len(self.dataframe[pandas.isna(self.dataframe["Manager (PI)"])])
        )
        validated_df = process_report.validate_pi_names(self.dataframe)
        self.assertEqual(
            0, len(validated_df[pandas.isna(validated_df["Manager (PI)"])])
        )


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
        self.dataframe = pandas.DataFrame(data)
        self.invoice_month = "2024-03"

        output_file = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".csv")
        self.output_file = output_file.name

    def tearDown(self):
        os.remove(self.output_file)

    def test_apply_credit_0002(self):
        process_report.export_lenovo(
            self.dataframe, self.invoice_month, self.output_file
        )
        output_df = pandas.read_csv(self.output_file)

        self.assertTrue(
            set(
                [
                    process_report.INVOICE_DATE_FIELD,
                    process_report.PROJECT_FIELD,
                    process_report.INSTITUTION_FIELD,
                    process_report.SU_TYPE_FIELD,
                    "SU Hours",
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
            self.assertEqual(row["Charge"], row["SU Charge"] * row["SU Hours"])
