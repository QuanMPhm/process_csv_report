from unittest import mock
import yaml

import pandas
import pytest

from process_report import settings
from process_report.tests import util as test_utils
from process_report.tests.base import BaseTestCaseWithTempDir


class TestColdfrontFetchProcessor(BaseTestCaseWithTempDir):
    def setUp(self):
        # To trigger fetch from Coldfront
        settings.invoice_settings.keycloak_client_id = "foo"
        return super().setUp()

    def _get_test_invoice(
        self,
        allocation_project_id,
        allocation_project_name=None,
        pi=None,
        institute_code=None,
        cluster_name=None,
        is_course=None,
    ):
        if not pi:
            pi = [""] * len(allocation_project_id)

        if not institute_code:
            institute_code = [""] * len(allocation_project_id)

        if not allocation_project_name:
            allocation_project_name = allocation_project_id

        if not cluster_name:
            cluster_name = [""] * len(allocation_project_id)

        if not is_course:
            is_course = [False] * len(allocation_project_id)

        return self.create_test_invoice(
            {
                "Manager (PI)": pi,
                "Project - Allocation": allocation_project_name,
                "Project - Allocation ID": allocation_project_id,
                "Institution - Specific Code": institute_code,
                "Cluster Name": cluster_name,
                "Is Course": is_course,
            }
        )

    def _get_mock_allocation_data(
        self,
        project_id_list,
        pi_list,
        institute_code_list,
        cluster_list,
        is_course_list=None,
    ):
        mock_data = []
        for i, project in enumerate(project_id_list):
            mock_project_dict = {
                "resource": {
                    "name": cluster_list[i],
                },
                "project": {
                    "pi": pi_list[i],
                },
                "attributes": {
                    "Allocated Project ID": project,
                    "Allocated Project Name": f"{project}-name",
                    "Institution-Specific Code": institute_code_list[i],
                },
            }

            if is_course_list:
                mock_project_dict["attributes"]["Is Course?"] = is_course_list[i]

            mock_data.append(mock_project_dict)

        return mock_data

    @mock.patch(
        "process_report.processors.coldfront_fetch_processor.ColdfrontFetchProcessor._fetch_coldfront_allocation_api",
    )
    def test_coldfront_fetch(self, mock_get_allocation_data):
        mock_get_allocation_data.return_value = self._get_mock_allocation_data(
            ["P1", "P2", "P3", "P4"],
            ["PI1", "PI1", "", "PI12"],
            ["IC1", "", "", "IC2"],
            ["stack"] * 4,
        )
        test_invoice = self._get_test_invoice(
            ["P1", "P1", "P2", "P3", "P4"], cluster_name=["stack"] * 5
        )
        answer_invoice = self._get_test_invoice(
            ["P1", "P1", "P2", "P3", "P4"],
            ["P1-name", "P1-name", "P2-name", "P3-name", "P4-name"],
            ["PI1", "PI1", "PI1", "", "PI12"],
            ["IC1", "IC1", "", "", "IC2"],
            ["stack"] * 5,
            is_course=[False] * 5,
        )
        test_coldfront_fetch_proc = test_utils.new_coldfront_fetch_processor(
            data=test_invoice
        )
        test_coldfront_fetch_proc.process()
        output_invoice = test_coldfront_fetch_proc.data
        assert output_invoice.equals(answer_invoice)

    @mock.patch(
        "process_report.processors.coldfront_fetch_processor.ColdfrontFetchProcessor._fetch_coldfront_allocation_api",
    )
    def test_coldfront_project_not_found(self, mock_get_allocation_data):
        """What happens when an invoice project is not found in Coldfront."""
        mock_get_allocation_data.return_value = self._get_mock_allocation_data(
            ["P1", "P2"], ["PI1", "PI1"], ["IC1", "IC2"], ["stack"] * 2
        )
        test_nonbillable_projects = pandas.DataFrame(
            {
                "Project Name": ["P3"],
                "Cluster": [None],
                "Is Timed": [False],
                "Is Billable Override": [False],
            }
        )
        test_invoice = self._get_test_invoice(
            ["P1", "P2", "P3", "P4", "P5"], cluster_name=["stack"] * 5
        )
        answer_project_set = [("P4", "stack"), ("P5", "stack")]
        test_coldfront_fetch_proc = test_utils.new_coldfront_fetch_processor(
            data=test_invoice, nonbillable_projects=test_nonbillable_projects
        )

        with pytest.raises(ValueError) as cm:
            test_coldfront_fetch_proc.process()

        assert str(cm.value) == (
            f"Projects {answer_project_set} not found in Coldfront and are billable! Please check the project names"
        )

    @mock.patch(
        "process_report.processors.coldfront_fetch_processor.ColdfrontFetchProcessor._fetch_coldfront_allocation_api",
    )
    def test_nonbillable_clusters(self, mock_get_allocation_data):
        """No errors are raised when an invoice project belonging
        to a non billable cluster (ocp-test) is not found in Coldfront"""
        mock_get_allocation_data.return_value = self._get_mock_allocation_data(
            ["P1", "P2"],
            ["PI1", "PI1"],
            ["IC1", "IC2"],
            ["ocp-prod", "stack"],
        )
        test_invoice = self._get_test_invoice(
            allocation_project_id=["P1", "P2", "P3", "P4"],
            cluster_name=["ocp-prod", "stack", "ocp-test", "ocp-test"],
        )
        answer_invoice = self._get_test_invoice(
            ["P1", "P2", "P3", "P4"],
            ["P1-name", "P2-name", "P3", "P4"],
            ["PI1", "PI1", "", ""],
            ["IC1", "IC2", "", ""],
            ["ocp-prod", "stack", "ocp-test", "ocp-test"],
            [False] * 4,
        )
        test_coldfront_fetch_proc = test_utils.new_coldfront_fetch_processor(
            data=test_invoice
        )
        test_coldfront_fetch_proc.process()
        output_invoice = test_coldfront_fetch_proc.data
        assert output_invoice.equals(answer_invoice)

    @mock.patch(
        "process_report.processors.coldfront_fetch_processor.ColdfrontFetchProcessor._fetch_coldfront_allocation_api",
    )
    def test_is_course_default_false(self, mock_get_allocation_data):
        """If 'Is Course?' is not set in the API data, the output 'Is Course' column is False"""
        mock_get_allocation_data.return_value = self._get_mock_allocation_data(
            ["P1", "P2"],
            ["PI1", "PI2"],
            ["IC1", "IC2"],
            ["stack", "stack"],
        )
        test_invoice = self._get_test_invoice(
            ["P1", "P2", "P3"],
            cluster_name=["stack", "stack", ""],
        )  # P3 not in Coldfront API data
        answer_invoice = self._get_test_invoice(
            ["P1", "P2", "P3"],
            ["P1-name", "P2-name", "P3"],
            ["PI1", "PI2", ""],
            ["IC1", "IC2", ""],
            ["stack", "stack", ""],
            [False, False, False],
        )
        nonbillable_projects = pandas.DataFrame(
            {
                "Project Name": ["P3"],
                "Cluster": [None],
                "Is Timed": [False],
                "Is Billable Override": [False],
            }
        )
        test_coldfront_fetch_proc = test_utils.new_coldfront_fetch_processor(
            data=test_invoice, nonbillable_projects=nonbillable_projects
        )
        test_coldfront_fetch_proc.process()
        output_invoice = test_coldfront_fetch_proc.data
        assert output_invoice.equals(answer_invoice)

    @mock.patch(
        "process_report.processors.coldfront_fetch_processor.ColdfrontFetchProcessor._fetch_coldfront_allocation_api",
    )
    def test_is_course_values(self, mock_get_allocation_data):
        """If 'Is Course?' is set in the API data, the output 'Is Course' column reflects True/False"""
        mock_get_allocation_data.return_value = self._get_mock_allocation_data(
            ["P1", "P2", "P3"],
            ["PI1", "PI2", "PI3"],
            ["IC1", "IC2", "IC3"],
            ["stack", "stack", "stack"],
            is_course_list=["Yes", "No", "yes"],
        )
        test_invoice = self._get_test_invoice(
            ["P1", "P2", "P3"], cluster_name=["stack", "stack", "stack"]
        )
        answer_invoice = self._get_test_invoice(
            ["P1", "P2", "P3"],
            ["P1-name", "P2-name", "P3-name"],
            ["PI1", "PI2", "PI3"],
            ["IC1", "IC2", "IC3"],
            ["stack", "stack", "stack"],
            [True, False, True],
        )
        test_coldfront_fetch_proc = test_utils.new_coldfront_fetch_processor(
            data=test_invoice
        )
        test_coldfront_fetch_proc.process()
        output_invoice = test_coldfront_fetch_proc.data
        assert output_invoice.equals(answer_invoice)

    @mock.patch(
        "process_report.processors.coldfront_fetch_processor.ColdfrontFetchProcessor._fetch_coldfront_allocation_api",
    )
    def test_missing_project_cluster_tuples(self, mock_get_allocation_data):
        # API returns allocations for P1@clusterA and P2@clusterA only
        mock_get_allocation_data.return_value = self._get_mock_allocation_data(
            ["P1", "P2"],
            ["PI1", "PI2"],
            ["IC1", "IC2"],
            ["clusterA", "clusterA"],
        )

        # Invoice contains two rows for P1 on different clusters, plus P2 and P4
        test_invoice = self._get_test_invoice(
            allocation_project_id=["P1", "P1", "P2", "P4"],
            cluster_name=["clusterA", "clusterB", "clusterA", "clusterA"],
        )

        test_coldfront_fetch_proc = test_utils.new_coldfront_fetch_processor(
            data=test_invoice
        )

        with pytest.raises(ValueError) as cm:
            test_coldfront_fetch_proc.process()

        expected_missing = [("P1", "clusterB"), ("P4", "clusterA")]
        assert str(cm.value) == (
            f"Projects {expected_missing} not found in Coldfront and are billable! Please check the project names"
        )

    @mock.patch(
        "process_report.processors.coldfront_fetch_processor.ColdfrontFetchProcessor._fetch_coldfront_allocation_api",
    )
    def test_supplement_api_data_used_when_coldfront_missing(
        self, mock_get_allocation_data
    ):
        """Supplement API rows are applied to invoice in _get_allocation_data()."""
        mock_get_allocation_data.return_value = self._get_mock_allocation_data(
            ["P1"],
            ["PI1"],
            ["IC1"],
            ["stack"],
        )

        # Supplemental data should follow same structure as Coldfront data,
        # only missing "Is Course?" and "Institution-Specific Code" fields
        supplemental_df = self._get_mock_allocation_data(
            ["P2"],
            ["PI2"],
            ["Delete Institude Code"],
            ["stack"],
        )
        del supplemental_df[0]["attributes"]["Institution-Specific Code"]

        supplemental_filepath = self.tempdir / "supplement.yaml"
        with open(supplemental_filepath, "w") as f:
            yaml.safe_dump(supplemental_df, f)

        test_invoice = self._get_test_invoice(
            ["P1", "P2"], cluster_name=["stack", "stack"]
        )

        expected_invoice = self._get_test_invoice(
            ["P1", "P2"],
            ["P1-name", "P2-name"],
            ["PI1", "PI2"],
            ["IC1", "N/A"],
            ["stack", "stack"],
            [False, False],
        )

        test_coldfront_fetch_proc = test_utils.new_coldfront_fetch_processor(
            data=test_invoice, coldfront_data_filepaths=[supplemental_filepath]
        )
        test_coldfront_fetch_proc.process()
        output_invoice = test_coldfront_fetch_proc.data

        assert output_invoice.equals(expected_invoice)

    @mock.patch(
        "process_report.processors.coldfront_fetch_processor.ColdfrontFetchProcessor._fetch_coldfront_allocation_api",
    )
    def test_duplicate_allocation_cluster_in_api_data(self, mock_get_allocation_data):
        """Test that a ValueError is raised when API data contains duplicate (allocation, cluster) pairs."""
        mock_data = [
            {
                "resource": {"name": "stack"},
                "project": {"pi": "PI1"},
                "attributes": {
                    "Allocated Project ID": "P1",
                    "Allocated Project Name": "P1-name",
                    "Institution-Specific Code": "IC1",
                },
            },
            {
                "resource": {"name": "stack"},
                "project": {"pi": "PI1"},
                "attributes": {
                    "Allocated Project ID": "P1",
                    "Allocated Project Name": "P1-name",
                    "Institution-Specific Code": "IC1",
                },
            },
        ]
        mock_get_allocation_data.return_value = mock_data

        test_invoice = self._get_test_invoice(["P1"], cluster_name=["stack"])

        test_coldfront_fetch_proc = test_utils.new_coldfront_fetch_processor(
            data=test_invoice
        )

        with pytest.raises(ValueError) as cm:
            test_coldfront_fetch_proc.process()

        assert (
            str(cm.value)
            == "Found allocations matched more than once in API data: [('P1', 'stack')]"
        )
