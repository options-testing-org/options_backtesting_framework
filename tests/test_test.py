import pickle

from options_framework.utils.helpers import get_market_dates
from options_framework.utils.options_db import OptionsDB
import datetime
from pathlib import Path

def test_get_market_dates():
    start_date = datetime.datetime(2026, 3, 17, 0, 0)
    end_date = datetime.datetime(2026, 4, 13, 0, 0)
    dates = get_market_dates(start_date, end_date)
    pass

def test_get_option_chain(get_mock_option_chain):
    chain = get_mock_option_chain(datetime.datetime(2026, 3, 17, 0, 0))
    print("quote_datetime:", chain.quote_datetime)
    print("spot_price:", chain.options[0]['spot_price'])
    print("expirations:", chain.expirations)
    print("strikes for first expiration:", chain.expiration_strikes[chain.expirations[0]][:10])
    print("sample option:", chain.options[0])

def test_get_pickles(daily_updates_call_390):
    keys = list(daily_updates_call_390.keys())[:2]
    for k in keys:
        print(daily_updates_call_390[k])
    pass

