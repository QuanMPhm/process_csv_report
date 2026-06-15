import unittest
from decimal import Decimal

import pandas

from process_report.invoices import invoice
from process_report.tests import util as test_utils


class TestRoyaltyProcessor(unittest.TestCase):
    def _get_test_invoice(
        self, institutions, balances, externally_funded, royalty=None
    ):
        if royalty is None:
            royalty = [None for _ in range(len(institutions))]
        return pandas.DataFrame(
            {
                invoice.INSTITUTION_FIELD: institutions,
                invoice.BALANCE_FIELD: balances,
                invoice.IS_EXTERNALLY_FUNDED_FIELD: externally_funded,
                invoice.ROYALTY_FIELD: royalty,
            }
        )

    def test_non_moc_member_gets_royalty_but_moc_member_does_not(self):
        test_invoice = self._get_test_invoice(
            institutions=["NonMOC", "MOCMember"],
            balances=[Decimal("100.00"), Decimal("200.00")],
            externally_funded=[False, False],
        )

        answer_invoice = self._get_test_invoice(
            institutions=["NonMOC", "MOCMember"],
            balances=[Decimal("100.00"), Decimal("200.00")],
            externally_funded=[False, False],
            royalty=[Decimal("10.00"), None],
        )

        processor = test_utils.new_royalty_processor(
            invoice_month="2024-01",
            data=test_invoice,
            royalty_rate=Decimal("0.10"),
            institution_list=["MOCMember"],
        )
        processor.process()

        assert processor.data.equals(answer_invoice)

    def test_externally_funded_moc_member_gets_royalty(self):
        test_invoice = self._get_test_invoice(
            institutions=["ExternallyFundedMOC", "MOCMember"],
            balances=[Decimal("200.00"), Decimal("150.00")],
            externally_funded=[True, False],
        )

        answer_invoice = self._get_test_invoice(
            institutions=["ExternallyFundedMOC", "MOCMember"],
            balances=[Decimal("200.00"), Decimal("150.00")],
            externally_funded=[True, False],
            royalty=[Decimal("20.00"), None],
        )

        processor = test_utils.new_royalty_processor(
            invoice_month="2024-01",
            data=test_invoice,
            royalty_rate=Decimal("0.10"),
            institution_list=["ExternallyFundedMOC", "MOCMember"],
        )
        processor.process()

        assert processor.data.equals(answer_invoice)
