from dataclasses import dataclass
import pandas

import process_report.util as util


### PI file field names
PI_PI_FIELD = "PI"
PI_FIRST_MONTH = "First Invoice Month"
PI_INITIAL_CREDITS = "Initial Credits"
PI_1ST_USED = "1st Month Used"
PI_2ND_USED = "2nd Month Used"
###

### Invoice field names
INVOICE_DATE_FIELD = "Invoice Month"
PROJECT_FIELD = "Project - Allocation"
PROJECT_ID_FIELD = "Project - Allocation ID"
PI_FIELD = "Manager (PI)"
INVOICE_EMAIL_FIELD = "Invoice Email"
INVOICE_ADDRESS_FIELD = "Invoice Address"
INSTITUTION_FIELD = "Institution"
INSTITUTION_ID_FIELD = "Institution - Specific Code"
SU_HOURS_FIELD = "SU Hours (GBhr or SUhr)"
SU_TYPE_FIELD = "SU Type"
COST_FIELD = "Cost"
CREDIT_FIELD = "Credit"
CREDIT_CODE_FIELD = "Credit Code"
SUBSIDY_FIELD = "Subsidy"
BALANCE_FIELD = "Balance"
###


@dataclass
class Invoice:
    name: str
    invoice_month: str
    data: pandas.DataFrame

    def process(self):
        self._prepare()
        self._process()
        self._prepare_export()

    @property
    def output_path(self) -> str:
        return f"{self.name} {self.invoice_month}.csv"

    @property
    def output_s3_key(self) -> str:
        return f"Invoices/{self.invoice_month}/{self.name} {self.invoice_month}.csv"

    @property
    def output_s3_archive_key(self):
        return f"Invoices/{self.invoice_month}/Archive/{self.name} {self.invoice_month} {util.get_iso8601_time()}.csv"

    def _prepare(self):
        """Prepares the data for processing.

        Implement in subclass if necessary. May add or remove columns
        necessary for processing, add or remove rows, validate the data, or
        perform simple substitutions.
        """
        pass

    def _process(self):
        """Processes the data.

        Implement in subclass if necessary. Performs necessary calculations
        on the data, e.g. applying subsidies or credits.
        """
        pass

    def _prepare_export(self):
        """Prepares the data for export.

        Implement in subclass if necessary. May add or remove columns or rows
        that should or should not be exported after processing."""
        pass

    def export(self):
        self.data.to_csv(self.output_path)

    def export_s3(self, s3_bucket):
        s3_bucket.upload_file(self.output_path, self.output_s3_key)
        s3_bucket.upload_file(self.output_path, self.output_s3_archive_key)
