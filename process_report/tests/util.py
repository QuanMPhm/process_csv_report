import pandas

from process_report.invoices import (
    invoice,
    billable_invoice,
    bu_internal_invoice,
    pi_specific_invoice,
)

from process_report.processors import (
    add_institution_processor,
    validate_pi_alias_processor,
    remove_nonbillables_processor,
    validate_billable_pi_processor,
)


def new_base_invoice(
    name="",
    invoice_month="0000-00",
    data=pandas.DataFrame(),
):
    return invoice.Invoice(name, invoice_month, data)


def new_billable_invoice(
    name="",
    invoice_month="0000-00",
    data=pandas.DataFrame(),
    old_pi_filepath="",
    limit_new_pi_credit_to_partners=False,
):
    return billable_invoice.BillableInvoice(
        name,
        invoice_month,
        data,
        old_pi_filepath,
        limit_new_pi_credit_to_partners,
    )


def new_bu_internal_invoice(
    name="", invoice_month="0000-00", data=pandas.DataFrame(), subsidy_amount=0
):
    return bu_internal_invoice.BUInternalInvoice(
        name, invoice_month, data, subsidy_amount
    )


def new_pi_specific_invoice(
    name="",
    invoice_month="0000-00",
    data=pandas.DataFrame(),
):
    return pi_specific_invoice.PIInvoice(
        name,
        invoice_month,
        data,
    )


def new_add_institution_processor(
    name="",
    invoice_month="0000-00",
    data=pandas.DataFrame(),
):
    return add_institution_processor.AddInstitutionProcessor(name, invoice_month, data)


def new_validate_pi_alias_processor(
    name="", invoice_month="0000-00", data=pandas.DataFrame(), alias_map={}
):
    return validate_pi_alias_processor.ValidatePIAliasProcessor(
        name, invoice_month, data, alias_map
    )


def new_remove_nonbillables_processor(
    name="",
    invoice_month="0000-00",
    data=pandas.DataFrame(),
    nonbillable_pis=[],
    nonbillable_projects=[],
):
    return remove_nonbillables_processor.RemoveNonbillablesProcessor(
        name, invoice_month, data, nonbillable_pis, nonbillable_projects
    )


def new_validate_billable_pi_processor(
    name="", invoice_month="0000-00", data=pandas.DataFrame()
):
    return validate_billable_pi_processor.ValidateBillablePIsProcessor(
        name, invoice_month, data
    )
