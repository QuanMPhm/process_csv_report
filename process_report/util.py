import datetime
import json
import logging
import sys
from decimal import Decimal

import pandas
import pyarrow

import process_report.invoices.invoice as invoice


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_institution_from_pi(institute_map, pi_uname):
    institution_key = pi_uname.split("@")[-1]
    institution_name = institute_map.get(institution_key, "")

    if institution_name == "":
        logger.warn(f"PI name {pi_uname} does not match any institution!")

    return institution_name


def load_institute_map() -> dict:
    with open("process_report/institute_map.json", "r") as f:
        institute_map = json.load(f)

    return institute_map


def get_iso8601_time():
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")


def compare_invoice_month(month_1, month_2):
    """Returns True if 1st date is later than 2nd date"""
    dt1 = datetime.datetime.strptime(month_1, "%Y-%m")
    dt2 = datetime.datetime.strptime(month_2, "%Y-%m")
    return dt1 > dt2


def get_pi_age(old_pi_df: pandas.DataFrame, pi, invoice_month):
    """Returns time difference between current invoice month and PI's first invoice month
    I.e 0 for new PIs

    Will raise an error if the PI'a age is negative, which suggests a faulty invoice, or a program bug"""
    first_invoice_month = old_pi_df.loc[
        old_pi_df[invoice.PI_PI_FIELD] == pi, invoice.PI_FIRST_MONTH
    ]
    if first_invoice_month.empty:
        return 0

    month_diff = get_month_diff(invoice_month, first_invoice_month.iat[0])
    if month_diff < 0:
        sys.exit(
            f"PI {pi} from {first_invoice_month} found in {invoice_month} invoice!"
        )
    else:
        return month_diff


def get_month_diff(month_1, month_2):
    """Returns a positive integer if month_1 is ahead in time of month_2"""
    dt1 = datetime.datetime.strptime(month_1, "%Y-%m")
    dt2 = datetime.datetime.strptime(month_2, "%Y-%m")
    return (dt1.year - dt2.year) * 12 + (dt1.month - dt2.month)


### Used by billable invoice


def remove_nonbillables(
    data: pandas.DataFrame, nonbillable_pis: list[str], nonbillable_projects: list[str]
):
    return data[
        ~data[invoice.PI_FIELD].isin(nonbillable_pis)
        & ~data[invoice.PROJECT_FIELD].isin(nonbillable_projects)
    ]


def validate_pi_names(data: pandas.DataFrame):
    invalid_pi_projects = data[pandas.isna(data[invoice.PI_FIELD])]
    for i, row in invalid_pi_projects.iterrows():
        logger.warn(f"Billable project {row[invoice.PROJECT_FIELD]} has empty PI field")
    return data[~pandas.isna(data[invoice.PI_FIELD])]


def load_old_pis(old_pi_filepath) -> pandas.DataFrame:
    try:
        old_pi_df = pandas.read_csv(
            old_pi_filepath,
            dtype={
                invoice.PI_INITIAL_CREDITS: pandas.ArrowDtype(
                    pyarrow.decimal128(21, 2)
                ),
                invoice.PI_1ST_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                invoice.PI_2ND_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
            },
        )
    except FileNotFoundError:
        sys.exit("Applying credit 0002 failed. Old PI file does not exist")

    return old_pi_df


def apply_credits_new_pi(data: pandas.DataFrame, old_pi_df: pandas.DataFrame):
    new_pi_credit_code = "0002"
    INITIAL_CREDIT_AMOUNT = 1000
    EXCLUDE_SU_TYPES = ["OpenShift GPUA100SXM4", "OpenStack GPUA100SXM4"]

    data[invoice.CREDIT_FIELD] = None
    data[invoice.CREDIT_CODE_FIELD] = None
    data[invoice.BALANCE_FIELD] = Decimal(0)

    current_pi_set = set(data[invoice.PI_FIELD])
    invoice_month = data[invoice.INVOICE_DATE_FIELD].iat[0]
    invoice_pis = old_pi_df[old_pi_df[invoice.PI_FIRST_MONTH] == invoice_month]
    if invoice_pis[invoice.PI_INITIAL_CREDITS].empty or pandas.isna(
        new_pi_credit_amount := invoice_pis[invoice.PI_INITIAL_CREDITS].iat[0]
    ):
        new_pi_credit_amount = INITIAL_CREDIT_AMOUNT

    print(f"New PI Credit set at {new_pi_credit_amount} for {invoice_month}")

    for pi in current_pi_set:
        pi_projects = data[data[invoice.PI_FIELD] == pi]
        pi_age = get_pi_age(old_pi_df, pi, invoice_month)
        pi_old_pi_entry = old_pi_df.loc[old_pi_df[invoice.PI_PI_FIELD] == pi].squeeze()

        if pi_age > 1:
            for i, row in pi_projects.iterrows():
                data.at[i, invoice.BALANCE_FIELD] = row[invoice.COST_FIELD]
        else:
            if pi_age == 0:
                if len(pi_old_pi_entry) == 0:
                    pi_entry = [pi, invoice_month, new_pi_credit_amount, 0, 0]
                    old_pi_df = pandas.concat(
                        [
                            pandas.DataFrame([pi_entry], columns=old_pi_df.columns),
                            old_pi_df,
                        ],
                        ignore_index=True,
                    )
                    pi_old_pi_entry = old_pi_df.loc[
                        old_pi_df[invoice.PI_PI_FIELD] == pi
                    ].squeeze()

                remaining_credit = new_pi_credit_amount
                credit_used_field = invoice.PI_1ST_USED
            elif pi_age == 1:
                remaining_credit = (
                    pi_old_pi_entry[invoice.PI_INITIAL_CREDITS]
                    - pi_old_pi_entry[invoice.PI_1ST_USED]
                )
                credit_used_field = invoice.PI_2ND_USED

            initial_credit = remaining_credit
            for i, row in pi_projects.iterrows():
                if (
                    remaining_credit == 0
                    or row[invoice.SU_TYPE_FIELD] in EXCLUDE_SU_TYPES
                ):
                    data.at[i, invoice.BALANCE_FIELD] = row[invoice.COST_FIELD]
                else:
                    project_cost = row[invoice.COST_FIELD]
                    applied_credit = min(project_cost, remaining_credit)

                    data.at[i, invoice.CREDIT_FIELD] = applied_credit
                    data.at[i, invoice.CREDIT_CODE_FIELD] = new_pi_credit_code
                    data.at[i, invoice.BALANCE_FIELD] = (
                        row[invoice.COST_FIELD] - applied_credit
                    )
                    remaining_credit -= applied_credit

            credits_used = initial_credit - remaining_credit
            if (pi_old_pi_entry[credit_used_field] != 0) and (
                credits_used != pi_old_pi_entry[credit_used_field]
            ):
                print(
                    f"Warning: PI file overwritten. PI {pi} previously used ${pi_old_pi_entry[credit_used_field]} of New PI credits, now uses ${credits_used}"
                )
            old_pi_df.loc[
                old_pi_df[invoice.PI_PI_FIELD] == pi, credit_used_field
            ] = credits_used

    old_pi_df = old_pi_df.astype(
        {
            invoice.PI_INITIAL_CREDITS: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
            invoice.PI_1ST_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
            invoice.PI_2ND_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
        },
    )

    return (data, old_pi_df)


def dump_old_pis(old_pi_filepath, old_pi_df: pandas.DataFrame):
    old_pi_df.to_csv(old_pi_filepath, index=False)


### End of billable invoice functions
