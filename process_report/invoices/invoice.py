from dataclasses import dataclass
from typing import Any, Callable
from decimal import Decimal
import pandas
import pyarrow
import logging

import process_report.util as util


logger = logging.getLogger(__name__)


@dataclass
class InvoiceColumn:
    name: str
    dtype: Any
    default_value: Any | None = None
    default_initializer: Callable[[pandas.DataFrame], pandas.Series] | None = None


# Field type definitions
BALANCE_FIELD_TYPE = pandas.ArrowDtype(pyarrow.decimal128(21, 2))
RATE_FIELD_TYPE = pandas.ArrowDtype(pyarrow.decimal128(21, 13))
INTEGER_FIELD_TYPE = pandas.ArrowDtype(pyarrow.int64())
STRING_FIELD_TYPE = pandas.StringDtype()
BOOL_FIELD_TYPE = pandas.BooleanDtype()


### PI file field names
PI_PI_FIELD = "PI"
PI_FIRST_MONTH = "First Invoice Month"
PI_INITIAL_CREDITS = "Initial Credits"
PI_1ST_USED = "1st Month Used"
PI_2ND_USED = "2nd Month Used"
###

### Prepay files fields
PREPAY_MONTH_FIELD = "Month"
PREPAY_CREDIT_FIELD = "Credit"
PREPAY_DEBIT_FIELD = "Debit"
PREPAY_GROUP_NAME_FIELD = "Group Name"
PREPAY_GROUP_CONTACT_FIELD = "Group Contact Email"
PREPAY_MANAGED_FIELD = "MGHPCC Managed"
PREPAY_PROJECT_FIELD = "Project"
PREPAY_START_DATE_FIELD = "Start Date"
PREPAY_END_DATE_FIELD = "End Date"
###

### Nonbillable projects file fields
NONBILLABLE_PROJECT_NAME = "Project Name"
NONBILLABLE_CLUSTER_NAME = "Cluster"
NONBILLABLE_IS_TIMED = "Timed"
NONBILLABLE_IS_BILLABLE_OVERRIDE = "Is Billable Override"

### Invoice field names
INVOICE_DATE_FIELD = "Invoice Month"
PROJECT_FIELD = "Project - Allocation"
PROJECT_ID_FIELD = "Project - Allocation ID"
PI_FIELD = "Manager (PI)"
INVOICE_EMAIL_FIELD = "Invoice Email"
INVOICE_ADDRESS_FIELD = "Invoice Address"
INSTITUTION_FIELD = "Institution"
INSTITUTION_ID_FIELD = "Institution - Specific Code"
GROUP_NAME_FIELD = "Prepaid Group Name"
GROUP_INSTITUTION_FIELD = "Prepaid Group Institution"
GROUP_BALANCE_FIELD = "Prepaid Group Balance"
GROUP_BALANCE_USED_FIELD = "Prepaid Group Used"
SU_HOURS_FIELD = "SU Hours (GBhr or SUhr)"
SU_TYPE_FIELD = "SU Type"
SU_CHARGE_FIELD = "SU Charge"
LENOVO_CHARGE_FIELD = "Charge"
RATE_FIELD = "Rate"
COST_FIELD = "Cost"
CREDIT_FIELD = "Credit"
CREDIT_CODE_FIELD = "Credit Code"
SUBSIDY_FIELD = "Subsidy"
BALANCE_FIELD = "Balance"
ROYALTY_FIELD = "Royalty"
###

### Internally used field names
IS_BILLABLE_FIELD = "Is Billable"
MISSING_PI_FIELD = "Missing PI"
PI_BALANCE_FIELD = "PI Balance"
PROJECT_NAME_FIELD = "Project"
GROUP_MANAGED_FIELD = "MGHPCC Managed"
CLUSTER_NAME_FIELD = "Cluster Name"
IS_COURSE_FIELD = "Is Course"
IS_EXTERNALLY_FUNDED_FIELD = "Is Externally Funded"
###

### Initialized Column objects
INVOICE_DATE_COLUMN = InvoiceColumn(name=INVOICE_DATE_FIELD, dtype=STRING_FIELD_TYPE)
PROJECT_COLUMN = InvoiceColumn(name=PROJECT_FIELD, dtype=STRING_FIELD_TYPE)
PROJECT_ID_COLUMN = InvoiceColumn(name=PROJECT_ID_FIELD, dtype=STRING_FIELD_TYPE)
PI_COLUMN = InvoiceColumn(name=PI_FIELD, dtype=STRING_FIELD_TYPE)
INVOICE_EMAIL_COLUMN = InvoiceColumn(name=INVOICE_EMAIL_FIELD, dtype=STRING_FIELD_TYPE)
INVOICE_ADDRESS_COLUMN = InvoiceColumn(
    name=INVOICE_ADDRESS_FIELD, dtype=STRING_FIELD_TYPE
)
INSTITUTION_COLUMN = InvoiceColumn(name=INSTITUTION_FIELD, dtype=STRING_FIELD_TYPE)
INSTITUTION_ID_COLUMN = InvoiceColumn(
    name=INSTITUTION_ID_FIELD, dtype=STRING_FIELD_TYPE
)
GROUP_NAME_COLUMN = InvoiceColumn(name=GROUP_NAME_FIELD, dtype=STRING_FIELD_TYPE)
GROUP_INSTITUTION_COLUMN = InvoiceColumn(
    name=GROUP_INSTITUTION_FIELD, dtype=STRING_FIELD_TYPE
)
GROUP_BALANCE_COLUMN = InvoiceColumn(name=GROUP_BALANCE_FIELD, dtype=BALANCE_FIELD_TYPE)
GROUP_BALANCE_USED_COLUMN = InvoiceColumn(
    name=GROUP_BALANCE_USED_FIELD, dtype=BALANCE_FIELD_TYPE
)
SU_HOURS_COLUMN = InvoiceColumn(name=SU_HOURS_FIELD, dtype=INTEGER_FIELD_TYPE)
SU_TYPE_COLUMN = InvoiceColumn(name=SU_TYPE_FIELD, dtype=STRING_FIELD_TYPE)
SU_CHARGE_COLUMN = InvoiceColumn(name=SU_CHARGE_FIELD, dtype=BALANCE_FIELD_TYPE)
LENOVO_CHARGE_COLUMN = InvoiceColumn(name=LENOVO_CHARGE_FIELD, dtype=BALANCE_FIELD_TYPE)
RATE_COLUMN = InvoiceColumn(
    name=RATE_FIELD, dtype=RATE_FIELD_TYPE
)  # Using decimal to suppress scientific notation in export
COST_COLUMN = InvoiceColumn(name=COST_FIELD, dtype=BALANCE_FIELD_TYPE)
CREDIT_COLUMN = InvoiceColumn(name=CREDIT_FIELD, dtype=BALANCE_FIELD_TYPE)
CREDIT_CODE_COLUMN = InvoiceColumn(name=CREDIT_CODE_FIELD, dtype=STRING_FIELD_TYPE)
SUBSIDY_COLUMN = InvoiceColumn(
    name=SUBSIDY_FIELD, dtype=BALANCE_FIELD_TYPE, default_value=Decimal(0)
)
BALANCE_COLUMN = InvoiceColumn(
    name=BALANCE_FIELD,
    dtype=BALANCE_FIELD_TYPE,
    default_initializer=lambda df: df[COST_FIELD],
)
PI_BALANCE_COLUMN = InvoiceColumn(
    name=PI_BALANCE_FIELD,
    dtype=BALANCE_FIELD_TYPE,
    default_initializer=lambda df: df[COST_FIELD],
)

# Internally used fields
IS_BILLABLE_COLUMN = InvoiceColumn(name=IS_BILLABLE_FIELD, dtype=BOOL_FIELD_TYPE)
MISSING_PI_COLUMN = InvoiceColumn(name=MISSING_PI_FIELD, dtype=BOOL_FIELD_TYPE)
PROJECT_NAME_COLUMN = InvoiceColumn(name=PROJECT_NAME_FIELD, dtype=STRING_FIELD_TYPE)
GROUP_MANAGED_COLUMN = InvoiceColumn(name=GROUP_MANAGED_FIELD, dtype=BOOL_FIELD_TYPE)
CLUSTER_NAME_COLUMN = InvoiceColumn(name=CLUSTER_NAME_FIELD, dtype=STRING_FIELD_TYPE)
IS_COURSE_COLUMN = InvoiceColumn(
    name=IS_COURSE_FIELD, dtype=BOOL_FIELD_TYPE, default_value=False
)
IS_EXTERNALLY_FUNDED_COLUMN = InvoiceColumn(
    name=IS_EXTERNALLY_FUNDED_FIELD, dtype=BOOL_FIELD_TYPE, default_value=False
)
ROYALTY_COLUMN = InvoiceColumn(name=ROYALTY_FIELD, dtype=BALANCE_FIELD_TYPE)
###


@dataclass
class Invoice:
    export_columns_list = list()
    exported_columns_map = dict()
    initializes_columns = tuple()
    operates_on_columns = tuple()

    invoice_month: str
    data: pandas.DataFrame
    name: str = ""
    export_data = None

    def process(self):
        self._init_columns()
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

    def _init_columns(self):
        """Initializes columns specified in `initializes_columns` and cast them to appropriate types

        If column already exists, only do casting
        If no default value is given, column initialized to None
        """
        for field in self.initializes_columns:
            if field.name not in self.data.columns:
                field_default = field.default_value
                if field.default_initializer:
                    field_default = field.default_initializer(self.data)
                self.data[field.name] = field_default
            elif self.data.dtypes[field.name] != field.dtype:
                logger.warning(
                    f"Column {field.name} has dtype {self.data.dtypes[field.name]} instead of expected {field.dtype}."
                )
            self.data = self.data.astype({field.name: field.dtype})

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

    def _filter_columns(self):
        """Filters and renames columns before exporting"""
        self.export_data = self.export_data[self.export_columns_list].rename(
            columns=self.exported_columns_map
        )

    def export(self):
        self._filter_columns()
        self.export_data.to_csv(self.output_path, index=False)

    def export_s3(self, s3_bucket):
        s3_bucket.upload_file(self.output_path, self.output_s3_key)
        s3_bucket.upload_file(self.output_path, self.output_s3_archive_key)
