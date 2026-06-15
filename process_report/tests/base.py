import tempfile
import shutil
from pathlib import Path
from unittest import TestCase

import pandas
import pyarrow


BALANCE_FIELD_TYPE = pandas.ArrowDtype(pyarrow.decimal128(21, 2))
RATE_FIELD_TYPE = pandas.ArrowDtype(pyarrow.decimal128(21, 13))
INTEGER_FIELD_TYPE = pandas.ArrowDtype(pyarrow.int64())
STRING_FIELD_TYPE = pandas.StringDtype()
BOOL_FIELD_TYPE = pandas.BooleanDtype()

FIELD_DTYPES = {
    "Invoice Month": STRING_FIELD_TYPE,
    "Project - Allocation": STRING_FIELD_TYPE,
    "Project - Allocation ID": STRING_FIELD_TYPE,
    "Manager (PI)": STRING_FIELD_TYPE,
    "Invoice Email": STRING_FIELD_TYPE,
    "Invoice Address": STRING_FIELD_TYPE,
    "Institution": STRING_FIELD_TYPE,
    "Institution - Specific Code": STRING_FIELD_TYPE,
    "Prepaid Group Name": STRING_FIELD_TYPE,
    "Prepaid Group Institution": STRING_FIELD_TYPE,
    "Prepaid Group Balance": BALANCE_FIELD_TYPE,
    "Prepaid Group Used": BALANCE_FIELD_TYPE,
    "SU Hours (GBhr or SUhr)": INTEGER_FIELD_TYPE,
    "SU Type": STRING_FIELD_TYPE,
    "SU Charge": BALANCE_FIELD_TYPE,
    "Charge": BALANCE_FIELD_TYPE,
    "Rate": RATE_FIELD_TYPE,
    "Cost": BALANCE_FIELD_TYPE,
    "Credit": BALANCE_FIELD_TYPE,
    "Credit Code": STRING_FIELD_TYPE,
    "Subsidy": BALANCE_FIELD_TYPE,
    "Balance": BALANCE_FIELD_TYPE,
    "Is Billable": BOOL_FIELD_TYPE,
    "Missing PI": BOOL_FIELD_TYPE,
    "PI Balance": BALANCE_FIELD_TYPE,
    "Project": STRING_FIELD_TYPE,
    "MGHPCC Managed": BOOL_FIELD_TYPE,
    "Cluster Name": STRING_FIELD_TYPE,
    "Is Course": BOOL_FIELD_TYPE,
    "Is Externally Funded": BOOL_FIELD_TYPE,
    "Royalty": BALANCE_FIELD_TYPE,
}


class BaseTestCase(TestCase):
    def create_test_invoice(self, data_dict: dict):
        present_cols = {
            col: dtype for col, dtype in FIELD_DTYPES.items() if col in data_dict
        }
        return pandas.DataFrame(data_dict).astype(present_cols)


class BaseTestCaseWithTempDir(BaseTestCase):
    def setUp(self):
        self.tempdir = Path(tempfile.TemporaryDirectory(delete=False).name)

    def tearDown(self):
        shutil.rmtree(self.tempdir)
