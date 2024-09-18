from dataclasses import dataclass

import process_report.invoices.invoice as invoice


@dataclass
class NonbillableInvoice(invoice.Invoice):
    nonbillable_pis: list[str]
    nonbillable_projects: list[str]

    export_columns_list = [
        invoice.INVOICE_DATE_FIELD,
        invoice.PROJECT_FIELD,
        invoice.PROJECT_ID_FIELD,
        invoice.PI_FIELD,
        invoice.INVOICE_EMAIL_FIELD,
        invoice.INVOICE_ADDRESS_FIELD,
        invoice.INSTITUTION_FIELD,
        invoice.INSTITUTION_ID_FIELD,
        invoice.SU_HOURS_FIELD,
        invoice.SU_TYPE_FIELD,
        invoice.RATE_FIELD,
        invoice.COST_FIELD,
    ]

    def _prepare_export(self):
        self.data = self.data[~self.data["Is Billable"]]
