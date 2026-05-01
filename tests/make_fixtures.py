import datetime
import pickle
from pathlib import Path
import os
import pytest
os.environ["OPTIONS_FRAMEWORK_CONFIG_FOLDER"] = r'C:\_code\options_backtesting_framework\tests\config'
from options_framework.utils.options_db import OptionsDB, IntradayOptionsDB
from options_framework.utils.helpers import get_market_dates

def make_option_updates_fixture_data():
    ticker = 'MSFT'
    # 3/17/2026	MSFT20260410P00038000	MSFT	380	4/10/2026	put
    option_id = 'MSFT20260417P00038000'
    # strike = 370
    # expiration = datetime.date(2026, 4, 10)
    # option_type = "put"
    start = datetime.datetime(2026, 3, 17, 0, 0)

    db = OptionsDB.from_symbol(ticker)

    updates = db.get_contract_updates(option_id, start.isoformat())
    fixtures_ = Path(__file__).parent.joinpath("fixtures")
    fn = fixtures_.joinpath(f"{option_id}_daily_updates.pkl")
    with open(fn, "wb") as f:
        pickle.dump(updates, f)

def make_option_chain_fixture_data():
    ticker = 'MSFT'
    start_date = datetime.datetime(2026, 3, 17, 0, 0)
    end_date = datetime.datetime(2026, 4, 13, 0, 0)

    dates = [datetime.datetime(2026, 3, 17, 0, 0), datetime.datetime(2026, 3, 18, 0, 0), datetime.datetime(2026, 3, 19, 0, 0), datetime.datetime(2026, 3, 20, 0, 0), datetime.datetime(2026, 3, 23, 0, 0), datetime.datetime(2026, 3, 24, 0, 0), datetime.datetime(2026, 3, 25, 0, 0), datetime.datetime(2026, 3, 26, 0, 0), datetime.datetime(2026, 3, 27, 0, 0), datetime.datetime(2026, 3, 30, 0, 0), datetime.datetime(2026, 3, 31, 0, 0), datetime.datetime(2026, 4, 1, 0, 0), datetime.datetime(2026, 4, 2, 0, 0), datetime.datetime(2026, 4, 6, 0, 0), datetime.datetime(2026, 4, 7, 0, 0), datetime.datetime(2026, 4, 8, 0, 0), datetime.datetime(2026, 4, 9, 0, 0), datetime.datetime(2026, 4, 10, 0, 0), datetime.datetime(2026, 4, 13, 0, 0)]


    db = OptionsDB.from_symbol(ticker)

    mock_db = {}

    for dt in dates:
        chain = db.get_chain_at(dt.isoformat())
        mock_db[dt] = chain

    fn = fixtures_ = Path(__file__).parent.joinpath("fixtures").joinpath("MSFT_chain.pkl")
    with open(fn, "wb") as f:
        pickle.dump(mock_db, f)

def read_pickle(path):
    with open(path, "rb") as f:
        options = pickle.load(f)
    return options


if __name__ == "__main__":
    make_option_updates_fixture_data()
    pass


