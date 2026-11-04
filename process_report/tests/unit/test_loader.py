from decimal import Decimal
import os
from unittest import TestCase, mock

from process_report.loader import Loader
from process_report.settings import Settings


class TestLoaderSettingsOverrides(TestCase):
    """Settings explicitly set to falsy values must not fall back to nerc_rates."""

    def setUp(self):
        patcher = mock.patch("process_report.loader.get_rates_info")
        self.mock_rates = patcher.start().return_value
        self.addCleanup(patcher.stop)

        # Prevent cached settings from affecting tests
        self.loader = Loader()

    def _set_env(self, **env):
        """Set env vars, re-parse Settings, so that loader module uses the updated settings."""
        env_patcher = mock.patch.dict(os.environ, env, clear=True)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)
        patcher = mock.patch("process_report.loader.invoice_settings", Settings())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_new_pi_credit_amount_zero(self):
        self._set_env(NEW_PI_CREDIT_AMOUNT="0")
        self.assertEqual(self.loader.get_new_pi_credit_amount(), Decimal(0))
        self.mock_rates.get_value_at.assert_not_called()

    def test_new_pi_credit_amount_nonzero(self):
        self._set_env(NEW_PI_CREDIT_AMOUNT="500")
        self.assertEqual(self.loader.get_new_pi_credit_amount(), Decimal(500))
        self.mock_rates.get_value_at.assert_not_called()

    def test_new_pi_credit_amount_none_uses_rates(self):
        self._set_env()
        self.mock_rates.get_value_at.return_value = Decimal(1000)
        self.assertEqual(self.loader.get_new_pi_credit_amount(), Decimal(1000))
        self.mock_rates.get_value_at.assert_called_once()

    def test_bu_subsidy_amount_zero(self):
        self._set_env(BU_SUBSIDY_AMOUNT="0")
        self.assertEqual(self.loader.get_bu_subsidy_amount(), Decimal(0))
        self.mock_rates.get_value_at.assert_not_called()

    def test_bu_subsidy_amount_nonzero(self):
        self._set_env(BU_SUBSIDY_AMOUNT="100")
        self.assertEqual(self.loader.get_bu_subsidy_amount(), Decimal(100))
        self.mock_rates.get_value_at.assert_not_called()

    def test_bu_subsidy_amount_none_uses_rates(self):
        self._set_env()
        self.mock_rates.get_value_at.return_value = Decimal(200)
        self.assertEqual(self.loader.get_bu_subsidy_amount(), Decimal(200))
        self.mock_rates.get_value_at.assert_called_once()

    def test_limit_new_pi_credit_to_partners_false(self):
        self._set_env(LIMIT_NEW_PI_CREDIT_TO_PARTNERS="false")
        self.assertIs(self.loader.get_limit_new_pi_credit_to_partners(), False)
        self.mock_rates.get_value_at.assert_not_called()

    def test_limit_new_pi_credit_to_partners_none_uses_rates(self):
        self._set_env()
        self.mock_rates.get_value_at.return_value = True
        self.assertIs(self.loader.get_limit_new_pi_credit_to_partners(), True)
        self.mock_rates.get_value_at.assert_called_once()

    def test_lenovo_charge_info_empty_dict(self):
        self._set_env(LENOVO_CHARGE_INFO="{}")
        self.assertEqual(self.loader.get_lenovo_su_charge_info(), {})
        self.mock_rates.get_value_at.assert_not_called()

    def test_lenovo_charge_info_zero_values(self):
        self._set_env(LENOVO_CHARGE_INFO='{"GPUA100SXM4": "0", "GPUH100": "0"}')
        self.assertEqual(
            self.loader.get_lenovo_su_charge_info(),
            {"GPUA100SXM4": Decimal(0), "GPUH100": Decimal(0)},
        )
        self.mock_rates.get_value_at.assert_not_called()

    def test_lenovo_charge_info_none_uses_rates(self):
        self._set_env()
        self.mock_rates.get_value_at.return_value = Decimal(1)
        self.assertEqual(
            self.loader.get_lenovo_su_charge_info(),
            {"GPUA100SXM4": Decimal(1), "GPUH100": Decimal(1)},
        )
        self.assertEqual(self.mock_rates.get_value_at.call_count, 2)
