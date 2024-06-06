from dataclasses import dataclass

import process_report.invoices.invoice as invoice
import process_report.util as util


@dataclass
class BillableInvoice(invoice.Invoice):
    nonbillable_pis: list[str]
    nonbillable_projects: list[str]
    old_pi_filepath: str

    def _prepare(self):
        self.data = util.remove_nonbillables(
            self.data, self.nonbillable_pis, self.nonbillable_projects
        )
        self.data = util.validate_pi_names(self.data)

    def _process(self):
        old_pi_df = util.load_old_pis(self.old_pi_filepath)
        self.data, updated_old_pi_df = util.apply_credits_new_pi(self.data, old_pi_df)
        util.dump_old_pis(self.old_pi_filepath, updated_old_pi_df)
