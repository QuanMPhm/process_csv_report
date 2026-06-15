from decimal import Decimal
import logging
from dataclasses import dataclass, field

from process_report.loader import loader
from process_report.settings import invoice_settings
from process_report.invoices import invoice
from process_report.processors import processor


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class RoyaltyProcessor(processor.Processor):
    """
    Given a percentage royalty rate and list of exemept institutions, creates a new `Royalty` column equal to `Balance` * royalty_rate
    """

    royalty_rate: Decimal = invoice_settings.royalty_rate
    royalty_exempt_institution_list: tuple[str] = field(
        default_factory=loader.get_royalty_exempt_institutions_list
    )

    initializes_columns = (invoice.ROYALTY_COLUMN,)
    operates_on_columns = (
        *initializes_columns,
        invoice.INSTITUTION_COLUMN,
        invoice.IS_EXTERNALLY_FUNDED_COLUMN,
        invoice.BALANCE_COLUMN,
    )

    def _process(self):
        non_moc_member_mask = ~self.data[invoice.INSTITUTION_FIELD].isin(
            self.royalty_exempt_institution_list
        )
        externally_funded_mask = self.data[invoice.INSTITUTION_FIELD].isin(
            self.royalty_exempt_institution_list
        ) & (self.data[invoice.IS_EXTERNALLY_FUNDED_FIELD] == True)  # noqa: E712

        self.data[invoice.ROYALTY_FIELD] = (
            self.data[invoice.BALANCE_FIELD] * self.royalty_rate
        ).where(non_moc_member_mask | externally_funded_mask)
