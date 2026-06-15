import sys
import logging
from dataclasses import dataclass, field

import pandas

from process_report.settings import invoice_settings
from process_report.loader import loader
from process_report import util
from process_report.invoices import invoice
from process_report.processors import discount_processor


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class PrepaymentProcessor(discount_processor.DiscountProcessor):
    IS_DISCOUNT_BY_NERC = False
    PREPAY_DEBITS_S3_FILEPATH = "Prepay/prepay_debits.csv"

    initializes_columns = (
        invoice.GROUP_NAME_COLUMN,
        invoice.GROUP_INSTITUTION_COLUMN,
        invoice.GROUP_MANAGED_COLUMN,
        invoice.GROUP_BALANCE_COLUMN,
        invoice.GROUP_BALANCE_USED_COLUMN,
    )
    operates_on_columns = (
        *initializes_columns,
        invoice.INVOICE_EMAIL_COLUMN,
        invoice.PROJECT_NAME_COLUMN,
        invoice.PI_BALANCE_COLUMN,
        invoice.BALANCE_COLUMN,
    )

    @property
    def PREPAY_DEBITS_S3_BACKUP_FILEPATH(self):
        return f"Prepay/Archive/prepay_debits {util.get_iso8601_time()}.csv"

    prepay_credits: pandas.DataFrame = field(
        default_factory=lambda: loader.load_prepay_credits()
    )
    prepay_projects: pandas.DataFrame = field(
        default_factory=lambda: loader.load_dataframe(
            invoice_settings.prepay_projects_filepath
        )
    )
    prepay_contacts: pandas.DataFrame = field(
        default_factory=lambda: loader.load_dataframe(
            invoice_settings.prepay_contacts_filepath
        )
    )
    prepay_debits_filepath: str = field(
        default_factory=lambda: loader.get_remote_filepath(
            invoice_settings.prepay_debits_remote_filepath
        )
    )
    upload_to_s3: bool = invoice_settings.upload_to_s3

    @staticmethod
    def _load_prepay_debits(prepay_debits_filepath):
        try:
            prepay_debits = pandas.read_csv(prepay_debits_filepath).astype(
                {invoice.PREPAY_DEBIT_FIELD: invoice.BALANCE_FIELD_TYPE}
            )
        except FileNotFoundError:
            sys.exit("Applying prepayments failed. prepay debits file does not exist")

        return prepay_debits

    def _prepare(self):
        self.prepay_debits = self._load_prepay_debits(self.prepay_debits_filepath)
        self.group_info_dict = self._get_prepay_group_dict()
        if self.upload_to_s3:
            self._backup_s3_prepay_debits()

    def _process(self):
        self._add_prepay_info()
        self._apply_prepayments()

        self._export_prepay_debits()
        if self.upload_to_s3:
            self._export_s3_prepay_debits()

    def _get_prepay_group_dict(self):
        """Loads prepay info into a dict for simpler indexing
        during processing step"""
        prepay_group_dict = dict()

        # Load each group's contact info, and initialize $0 balance and empty project list
        for _, group_info in self.prepay_contacts.iterrows():
            group_name = group_info[invoice.PREPAY_GROUP_NAME_FIELD]
            prepay_group_dict[group_name] = dict()
            prepay_group_dict[group_name][invoice.PREPAY_GROUP_CONTACT_FIELD] = (
                group_info[invoice.PREPAY_GROUP_CONTACT_FIELD]
            )
            prepay_group_dict[group_name][invoice.PREPAY_MANAGED_FIELD] = (
                group_info[invoice.PREPAY_MANAGED_FIELD].lower() == "yes"
            )
            prepay_group_dict[group_name][invoice.GROUP_BALANCE_FIELD] = 0
            prepay_group_dict[group_name][invoice.PREPAY_PROJECT_FIELD] = []

        # Sum up each group's credits from current and past months
        for _, group_credit in self.prepay_credits.iterrows():
            if (
                util.get_month_diff(
                    self.invoice_month, group_credit[invoice.PREPAY_MONTH_FIELD]
                )
                >= 0
            ):
                prepay_group_dict[group_credit[invoice.PREPAY_GROUP_NAME_FIELD]][
                    invoice.GROUP_BALANCE_FIELD
                ] += group_credit[invoice.PREPAY_CREDIT_FIELD]

        # Sum up each group's debits from past months. DOES NOT INCLUDE CURRENT MONTH
        for _, group_debit in self.prepay_debits.iterrows():
            if (
                util.get_month_diff(
                    self.invoice_month, group_debit[invoice.PREPAY_MONTH_FIELD]
                )
                > 0
            ):
                prepay_group_dict[group_debit[invoice.PREPAY_GROUP_NAME_FIELD]][
                    invoice.GROUP_BALANCE_FIELD
                ] -= group_debit[invoice.PREPAY_DEBIT_FIELD]

                if (
                    prepay_group_dict[group_debit[invoice.PREPAY_GROUP_NAME_FIELD]][
                        invoice.GROUP_BALANCE_FIELD
                    ]
                    < 0
                ):
                    logger.error(
                        f"Balance for prepay group {group_credit[invoice.PREPAY_GROUP_NAME_FIELD]} is negative!"
                    )
                    sys.exit(1)

        # Populate each group's list of "active" prepay projects
        # Projects' "active" period includes their start and end dates
        for _, group_project in self.prepay_projects.iterrows():
            if (
                util.get_month_diff(
                    self.invoice_month, group_project[invoice.PREPAY_START_DATE_FIELD]
                )
                >= 0
                and util.get_month_diff(
                    group_project[invoice.PREPAY_END_DATE_FIELD], self.invoice_month
                )
                >= 0
            ):
                prepay_group_dict[group_project[invoice.PREPAY_GROUP_NAME_FIELD]][
                    invoice.PREPAY_PROJECT_FIELD
                ].append(group_project[invoice.PREPAY_PROJECT_FIELD])

        return prepay_group_dict

    def _add_prepay_info(self):
        """Populate prepaid group name, institute, and MGHPCC managed field"""
        institute_list = util.load_institute_list()

        for group_name, group_dict in self.group_info_dict.items():
            group_institute = institute_list.get_institution_from_pi(
                group_dict[invoice.PREPAY_GROUP_CONTACT_FIELD]
            )

            # Prepay projects are identified by project name, not project - allocation name
            row_mask = self.data[invoice.PROJECT_NAME_FIELD].isin(
                group_dict[invoice.PREPAY_PROJECT_FIELD]
            )
            col_mask = [
                invoice.INVOICE_EMAIL_FIELD,
                invoice.GROUP_NAME_FIELD,
                invoice.GROUP_INSTITUTION_FIELD,
                invoice.GROUP_MANAGED_FIELD,
            ]
            self.data.loc[row_mask, col_mask] = [
                group_dict[invoice.PREPAY_GROUP_CONTACT_FIELD],
                group_name,
                group_institute,
                group_dict[invoice.PREPAY_MANAGED_FIELD],
            ]

    def _apply_prepayments(self):
        for group_name, group_dict in self.group_info_dict.items():
            group_projects = self.data[
                self.data[invoice.GROUP_NAME_FIELD] == group_name
            ]
            prepay_amount_used = self.apply_flat_discount(
                self.data,
                group_projects,
                invoice.PI_BALANCE_FIELD,
                group_dict[invoice.GROUP_BALANCE_FIELD],
                invoice.GROUP_BALANCE_USED_FIELD,
                invoice.BALANCE_FIELD,
            )

            remaining_prepay_balance = (
                group_dict[invoice.GROUP_BALANCE_FIELD] - prepay_amount_used
            )
            self.data.loc[
                self.data[invoice.GROUP_NAME_FIELD] == group_name,
                invoice.GROUP_BALANCE_FIELD,
            ] = remaining_prepay_balance

            # If the group has used some prepay money, check if the group
            # already has a debit entry for the current month to decide
            # whether to append a new debit entry, or overwrite the old one
            if prepay_amount_used > 0:
                debit_entry_mask = (
                    self.prepay_debits[invoice.PREPAY_MONTH_FIELD] == self.invoice_month
                ) & (self.prepay_debits[invoice.PREPAY_GROUP_NAME_FIELD] == group_name)
                if self.prepay_debits[debit_entry_mask].empty:
                    self.prepay_debits = pandas.concat(
                        [
                            self.prepay_debits,
                            pandas.DataFrame(
                                [[self.invoice_month, group_name, prepay_amount_used]],
                                columns=self.prepay_debits.columns,
                            ),
                        ],
                        ignore_index=True,
                    )
                else:
                    self.prepay_debits.loc[
                        debit_entry_mask, invoice.PREPAY_DEBIT_FIELD
                    ] = prepay_amount_used

    def _backup_s3_prepay_debits(self):
        invoice_bucket = util.get_invoice_bucket()
        invoice_bucket.upload_file(
            self.prepay_debits_filepath, self.PREPAY_DEBITS_S3_BACKUP_FILEPATH
        )

    def _export_prepay_debits(self):
        self.prepay_debits.to_csv(self.prepay_debits_filepath, index=False)

    def _export_s3_prepay_debits(self):
        invoice_bucket = util.get_invoice_bucket()
        invoice_bucket.upload_file(
            self.prepay_debits_filepath, self.PREPAY_DEBITS_S3_FILEPATH
        )
