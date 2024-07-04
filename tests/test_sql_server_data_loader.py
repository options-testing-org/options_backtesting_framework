import datetime

import pytest

import pandas as pd

from options_framework.data.sql_data_loader import SQLServerDataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter, FilterRange

from options_framework.config import settings

@pytest.fixture
def set_settings():
    settings.DATA_LOADER_TYPE = "SQL_DATA_LOADER"
    settings.DATA_FORMAT_SETTINGS = 'sql_server_cboe_settings.toml'
    start_date = datetime.datetime(2016, 3, 1, 9, 31)
    end_date = datetime.datetime(2016, 3, 1, 9, 32)
    select_filter = SelectFilter()
    return start_date, end_date, select_filter

def test_sql_load_options_from_database(set_settings):

    start_date, end_date, select_filter = set_settings
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    #sql_loader.load_option_chain_data('SPXW', start_date)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert len(options_df) == 9612

def test_sql_load_call_options_from_database(set_settings):
    start_date, end_date, select_filter = set_settings
    select_filter.option_type = OptionType.CALL
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df[options_df['option_type'] != 1].count().sum() == 0


def test_load_with_custom_option_attribute_selection(set_settings):
    start_date, end_date, select_filter = set_settings
    additional_attributes = ['delta', 'gamma', 'theta', 'open_interest']
    select_filter.option_type = OptionType.CALL
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=additional_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    option = options_df.iloc[0]

    assert option['delta'] == 0.9999

def test_load_data_with_expiration_range(set_settings):
    start_date, end_date, select_filter = set_settings
    low_expiration = datetime.date(2016, 4, 1)
    hi_expiration = datetime.date(2016, 4, 29)
    select_filter.option_type = OptionType.CALL
    select_filter.expiration_dte = FilterRange(low=30, high=60)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['expiration'].min().to_pydatetime().date() == low_expiration
    assert options_df['expiration'].max().to_pydatetime().date() == hi_expiration


def test_load_data_with_strike_range(set_settings):
    start_date, end_date, select_filter = set_settings
    select_filter.option_type = OptionType.CALL
    select_filter.expiration_dte = FilterRange(low=30, high=60)
    select_filter.strike_offset = FilterRange(low=10, high=10)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['strike'].min() == 1940
    assert options_df['strike'].max() == 1955


def test_load_data_with_delta_range(set_settings):
    start_date, end_date, select_filter = set_settings
    extended_attributes = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility', 'open_interest']

    select_filter.option_type = OptionType.CALL
    select_filter.expiration_dte = FilterRange(low=30, high=60)
    select_filter.strike_offset = FilterRange(low=50, high=50)
    select_filter.delta_range = FilterRange(low=0.60, high=0.70)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=extended_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['delta'].min() >= 0.60
    assert options_df['delta'].max() <= 0.70

def test_load_put_data_with_delta_range(set_settings):
    start_date, end_date, select_filter = set_settings
    extended_attributes = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility', 'open_interest']

    select_filter.option_type = OptionType.PUT
    select_filter.expiration_dte = FilterRange(low=30, high=60)
    select_filter.strike_offset = FilterRange(low=50, high=50)
    select_filter.delta_range = FilterRange(low=-0.70, high=-0.60)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=extended_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['delta'].min() >= -0.70
    assert options_df['delta'].min() <= -0.60

def test_load_data_with_gamma_range(set_settings):
    start_date, end_date, select_filter = set_settings
    extended_attributes = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility', 'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.gamma_range = FilterRange(low=0.009, high=0.01)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=extended_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['gamma'].min() >= 0.009
    assert options_df['gamma'].max() <= 0.01

def test_load_data_with_theta_range(set_settings):
    start_date, end_date, select_filter = set_settings
    extended_attributes = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility', 'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.expiration_dte = FilterRange(low=30, high=60)
    select_filter.theta_range = FilterRange(low=-0.4, high=-0.3)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=extended_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['theta'].min() >= -0.4
    assert options_df['theta'].max() <= -0.3

def test_load_data_with_vega_range(set_settings):
    start_date, end_date, select_filter = set_settings
    extended_attributes = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility', 'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.vega_range = FilterRange(low=5.0, high=6.0)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=extended_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['vega'].min() >= 5.0
    assert options_df['vega'].max() <= 6.0

def test_load_data_with_rho_range(set_settings):
    start_date, end_date, select_filter = set_settings
    extended_attributes = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility', 'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.strike_offset = FilterRange(low=50, high=50)
    select_filter.rho_range = FilterRange(low=100.0, high=200.0)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=extended_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['rho'].min() >= 100.0
    assert options_df['rho'].max() <= 200.0


def test_load_data_with_open_interest_range(set_settings):
    start_date, end_date, select_filter = set_settings
    extended_attributes = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility', 'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.strike_offset = FilterRange(low=200, high=200)
    select_filter.open_interest_range = FilterRange(low=100)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=extended_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['open_interest'].min() >= 100.0

def test_load_data_with_implied_volatility_range(set_settings):
    start_date, end_date, select_filter = set_settings
    extended_attributes = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility', 'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.implied_volatility_range = FilterRange(low=0.5, high=1.0)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=extended_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert options_df['implied_volatility'].min() >= 0.5
    assert options_df['implied_volatility'].max() <= 1.0

def test_load_data_with_all_range_filters(set_settings):
    start_date, end_date, select_filter = set_settings
    extended_attributes = ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility', 'open_interest']
    select_filter.option_type = OptionType.PUT
    select_filter.expiration_range = FilterRange(low=90, high=120)
    select_filter.strike_offset = FilterRange(low=200, high=200)
    select_filter.delta_range = FilterRange(low=-0.80, high=-0.05)
    select_filter.gamma_range = FilterRange(low=0.0, high=0.0025)
    select_filter.theta_range = FilterRange(low=-0.4, high=-0.2)
    select_filter.vega_range = FilterRange(low=2.5, high=4.5)
    select_filter.rho_range = FilterRange(low=-500.0, high=-90.0)
    select_filter.open_interest_range = FilterRange(low=100, high=100_000)
    select_filter.implied_volatility_range = FilterRange(low=0.20, high=0.25)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                     extended_option_attributes=extended_attributes)
    options_df = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, options_data: pd.DataFrame):
        nonlocal options_df
        options_df = options_data

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain_data('SPXW', start_date)

    assert len(options_df) == 29
