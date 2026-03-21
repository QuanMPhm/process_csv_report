import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Coldfront info
    coldfront_api_filepaths: tuple[str, ...] = ()
    keycloak_client_id: str | None = None
    keycloak_client_secret: str | None = None

    invoice_path_template: str = "Invoices/{invoice_month}/Service Invoices/"
    invoice_month: str = (datetime.datetime.today() - relativedelta(months=1)).strftime(
        "%Y-%m"
    )
    fetch_from_s3: bool = True
    upload_to_s3: bool = False

    # S3 Files
    pi_remote_filepath: str = "PIs/PI.csv"
    alias_remote_filepath: str = "PIs/alias.csv"
    prepay_debits_remote_filepath: str = "Prepay/prepay_debits.csv"

    # Local input files
    nonbillable_pis_filepath: str = "pi.yaml"
    nonbillable_projects_filepath: str = "projects.yaml"
    prepay_projects_filepath: str = "prepaid_projects.csv"
    prepay_credits_filepath: str = "prepaid_credits.csv"
    prepay_contacts_filepath: str = "prepaid_contacts.csv"

    # nerc_rates info
    new_pi_credit_amount: Decimal | None = None
    limit_new_pi_credit_to_partners: bool | None = None
    bu_subsidy_amount: Decimal | None = None
    lenovo_charge_info: dict[str, Decimal] | None = None


invoice_settings = Settings()
