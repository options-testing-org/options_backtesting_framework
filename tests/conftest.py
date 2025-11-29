import datetime
import pytest
import pandas as pd
from pandas import DataFrame
import os

os.environ["OPTIONS_FRAMEWORK_CONFIG_FOLDER"] = r'C:\_code\options_backtesting_framework\tests\config'
from mocks import *
#from test_data.test_option_daily import daily_test_options, daily_test_df
from pprint import pprint as pp

from test_helpers import get_daily_option_chain_items, create_option_objects, get_daily_test_df, get_daily_option_data
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
def allow_slippage():
    settings.apply_slippage_entry=True
    settings.apply_slippage_exit=True
    yield
    settings.apply_slippage_entry = False
    settings.apply_slippage_exit = False


@pytest.fixture
def option_chain_daily():
    def get_option_chain_daily_for_date(quote_date):

        option_chain = MockOptionChain(symbol='AAPL',quote_datetime=quote_date)
        options, expirations, expiration_strikes = get_daily_option_chain_items(quote_date)
        option_chain.option_chain = options
        option_chain.expirations = expirations
        option_chain.expiration_strikes = expiration_strikes
        return option_chain
    return get_option_chain_daily_for_date

