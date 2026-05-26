from unittest import TestCase, mock
import pandas

from process_report.tests import util as test_utils


class TestMocaPrepaidInvoice(TestCase):
    def _get_test_data(self, group_managed):
        return pandas.DataFrame({"MGHPCC Managed": group_managed})

    def test_prepare_export(self):
        test_data = self._get_test_data(group_managed=[True, False, True])
        inv = test_utils.new_moca_prepaid_invoice(data=test_data)
        inv._prepare_export()
        assert len(inv.export_data) == 1
        assert not inv.export_data.iloc[0]["MGHPCC Managed"]

    def test_output_path(self):
        inv = test_utils.new_moca_prepaid_invoice(invoice_month="2025-01")
        assert inv.output_path == "MOCA-A_Prepaid_Groups-2025-01-Invoice.csv"

    def test_output_s3_key(self):
        inv = test_utils.new_moca_prepaid_invoice(invoice_month="2025-01")
        assert (
            inv.output_s3_key
            == "Invoices/2025-01/MOCA-A_Prepaid_Groups-2025-01-Invoice.csv"
        )

    @mock.patch("process_report.util.get_iso8601_time")
    def test_output_s3_archive_key(self, mock_get_time):
        mock_get_time.return_value = "2025-01-01T00:00:00"
        inv = test_utils.new_moca_prepaid_invoice(invoice_month="2025-01")
        assert (
            inv.output_s3_archive_key
            == "Invoices/2025-01/Archive/MOCA-A_Prepaid_Groups-2025-01-Invoice 2025-01-01T00:00:00.csv"
        )
