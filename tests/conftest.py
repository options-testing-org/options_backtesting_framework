import datetime
import pytest
import pandas as pd
from pandas import DataFrame
import os

os.environ["OPTIONS_FRAMEWORK_CONFIG_FOLDER"] = r'C:\_code\options_backtesting_framework\tests\config'
from mocks import *
from test_data.test_option_data import *

from pprint import pprint as pp

from options_framework.config import settings, load_settings


@pytest.fixture
def incur_fees_true():
    original_setting = settings['incur_fees']
    settings['incur_fees'] = True
    yield
    settings['incur_fees'] = original_setting


@pytest.fixture
def incur_fees_false():
    original_setting = settings['incur_fees']
    settings['incur_fees'] = False
    yield
    settings['incur_fees'] = original_setting

@pytest.fixture
def intraday_file_settings():
    original_freq = settings['data_frequency']
    settings['data_frequency'] = 'intraday'
    yield
    settings['data_frequency'] = original_freq


@pytest.fixture
def daily_file_settings():
    original_freq = settings['data_frequency']
    settings['data_frequency'] = 'daily'
    yield
    settings['data_frequency'] = original_freq
    pass


@pytest.fixture
def option_chain_daily():
    def get_option_chain_daily_for_date(quote_date):
        data = daily_option_data
        end_date = datetime.datetime(2015, 1, 5, 0, 0)
        option_chain = MockOptionChain(symbol='AAPL', quote_datetime=quote_date)
        options = [x for x in data if x['quote_datetime'] == quote_date]
        expirations = list(set([x['expiration'] for x in data]))
        expirations.sort()
        expiration_strikes = [(x['expiration'], x['strike']) for x in options]
        expiration_strikes = list(set(expiration_strikes))
        expiration_strikes = sorted(expiration_strikes, key=lambda x: (x[0], x[1]))
        expiration_strikes = {exp: [s for (e, s) in expiration_strikes if e == exp] for exp in expirations}

        option_chain.option_chain = options
        option_chain.expirations = expirations
        option_chain.expiration_strikes = expiration_strikes
        return option_chain
    return get_option_chain_daily_for_date

