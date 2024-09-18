from dataclasses import dataclass
import logging

import pandas

from process_report.invoices import invoice
from process_report.processors import processor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class ValidateBillablePIsProcessor(processor.Processor):
    @staticmethod
    def _validate_pi_names(data: pandas.DataFrame):
        invalid_pi_projects = data[pandas.isna(data[invoice.PI_FIELD])]
        for i, row in invalid_pi_projects.iterrows():
            logger.warn(
                f"Billable project {row[invoice.PROJECT_FIELD]} has empty PI field"
            )
        return pandas.isna(data[invoice.PI_FIELD])

    def _process(self):
        self.data["Missing PI"] = self._validate_pi_names(self.data)
