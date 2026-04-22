import datetime
import pickle
from pathlib import Path
import os
import pytest
os.environ["OPTIONS_FRAMEWORK_CONFIG_FOLDER"] = r'C:\_code\options_backtesting_framework\tests\config'
from options_framework.utils.options_db import OptionsDB, IntradayOptionsDB

ticker = 'MSFT'
# 3/17/2026	MSFT20260410P00038000	MSFT	380	4/10/2026	put
option_id = 'MSFT20260410P00038000'
strike = 380
expiration = datetime.date(2026, 4, 10)
option_type = "put"
start = datetime.datetime(2026, 3, 17, 9, 31)

db = OptionsDB.from_symbol(ticker)

updates = db.get_contract_updates(option_id, start.isoformat())
fixtures_ = Path(__file__).parent.joinpath("fixtures")
fn = fixtures_.joinpath(f"{option_id}_daily_updates.pkl")
with open(fn, "wb") as f:
    pickle.dump(updates, f)
pass



