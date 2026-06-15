from dataclasses import dataclass

import process_report.invoices.invoice as invoice


@dataclass
class RoyaltyInvoice(invoice.Invoice):
    name: str = "Royalties"
    export_columns_list = [
        invoice.PROJECT_FIELD,
        invoice.PI_FIELD,
        invoice.CLUSTER_NAME_FIELD,
        invoice.INSTITUTION_FIELD,
        invoice.SU_TYPE_FIELD,
        invoice.BALANCE_FIELD,
        invoice.ROYALTY_FIELD,
    ]

    def _prepare_export(self):
        self.export_data = self.data[~self.data[invoice.ROYALTY_FIELD].isna()]
