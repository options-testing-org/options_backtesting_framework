import datetime

import pytest

from options_framework.data.sql_data_loader import SQLServerDataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter, FilterRange

from options_framework.config import settings

@pytest.fixture
def set_settings():
    original_value_1 = settings.DATA_FORMAT_SETTINGS
    original_value_2 = settings.DATA_LOADER_TYPE
    settings.DATA_LOADER_TYPE = "SQL_DATA_LOADER"
    settings.DATA_FORMAT_SETTINGS = 'sql_server_cboe_settings.toml'
    start_date = datetime.datetime(2016, 3, 1, 9, 31)
    end_date = datetime.datetime(2016, 3, 1, 9, 32)
    select_filter = SelectFilter(symbol='SPXW')
    yield start_date, end_date, select_filter
    settings.DATA_LOADER_TYPE = original_value_1
    settings.DATA_FORMAT_SETTINGS = original_value_2


def test_sql_load_from_database(set_settings):
    # start_date = datetime.datetime(2016, 3, 1, 9, 31)
    # end_date = datetime.datetime(2016, 3, 1, 9, 32)
    # select_filter = SelectFilter(symbol='SPXW')
    start_date, end_date, select_filter = set_settings
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date)

    assert len(options) == 4806


def test_sql_load_call_options_from_database(set_settings):
    start_date, end_date, select_filter = set_settings
    select_filter.option_type = OptionType.CALL
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters={'option_type': OptionType.CALL})

    assert len(options) == 2403


def test_load_with_custom_field_selection(set_settings):
    start_date, end_date, select_filter = set_settings
    select_fields = settings.SELECT_FIELDS +  ['delta', 'gamma', 'theta', 'open_interest']
    #ields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'open_interest']
    select_filter.option_type = OptionType.CALL
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter, fields_list=select_fields)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters={'option_type': OptionType.CALL})

    option = options[0]

    assert option.delta is not None

#
# def test_load_data_with_only_required_fields(set_settings):
#     start_date, end_date, select_filter = set_settings
#     fields = ['option_id', 'symbol', 'expiration', 'strike', 'option_type']
#
#     sql_loader = SQLServerDataLoader(select_fields=fields,
#                                      order_by_fields=['expiration', 'strike'])
#     options = []
#
#     def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
#         nonlocal options
#         options = option_chain
#
#     sql_loader.bind(option_chain_loaded=on_data_loaded)
#     sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters={'option_type': OptionType.CALL})
#
#     option = options[0]
#
#     assert option.quote_datetime is None
#     assert option.price is None


def test_load_data_with_expiration_range(set_settings):
    start_date, end_date, select_filter = set_settings
    low_expiration = datetime.date(2016, 4, 1)
    hi_expiration = datetime.date(2016, 4, 30)
    select_filter.option_type = OptionType.CALL
    select_filter.expiration_range = FilterRange(low=low_expiration, high=hi_expiration)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 681


def test_load_data_with_strike_range(set_settings):
    start_date, end_date, select_filter = set_settings
    low_expiration = datetime.date(2016, 4, 1)
    hi_expiration = datetime.date(2016, 4, 30)
    select_filter.option_type = OptionType.CALL
    select_filter.expiration_range = FilterRange(low=low_expiration, high=hi_expiration)
    select_filter.strike_range = FilterRange(low=1940, high=1950)
    # fltr = {
    #     'option_type': OptionType.CALL,
    #     'expiration': {'low': low_expiration,
    #                    'high': hi_expiration},
    #     'strike': {'low': 1940, 'high': 1950}
    # }
    #start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 12


def test_load_data_with_delta_range(set_settings):
    start_date, end_date, select_filter = set_settings
    fields = settings.SELECT_FIELDS + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']
    low_expiration = datetime.date(2016, 4, 1)
    hi_expiration = datetime.date(2016, 4, 30)
    select_filter.option_type = OptionType.CALL
    select_filter.expiration_range = FilterRange(low=low_expiration, high=hi_expiration)
    select_filter.strike_range = FilterRange(low=1900, high=2050)
    select_filter.delta_range = FilterRange(low=0.60, high=0.70)

    # fltr = {
    #     'option_type': OptionType.CALL,
    #     'expiration': {'low': low_expiration,
    #                    'high': hi_expiration},
    #     'strike': {'low': 1900, 'high': 2050},
    #     'delta': {'low': 0.60, 'high': 0.70}
    # }
    #start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter, fields_list=fields)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 15


def test_load_data_with_gamma_range(set_settings):
    start_date, end_date, select_filter = set_settings
    fields = settings.SELECT_FIELDS + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.gamma_range = FilterRange(low=0.009, high=0.01)
    # fltr = {
    #     'option_type': OptionType.CALL,
    #     'gamma': {'low': 0.009, 'high': 0.01}
    # }
    #start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter, fields_list=fields)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 4

def test_load_data_with_theta_range(set_settings):
    start_date, end_date, select_filter = set_settings
    fields = settings.SELECT_FIELDS + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.expiration_range = FilterRange(low=datetime.date(2016, 5, 1), high=datetime.date(2016, 8, 31))
    select_filter.theta_range = FilterRange(low=-0.4, high=-0.3)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter, fields_list=fields)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 115

def test_load_data_with_vega_range(set_settings):
    start_date, end_date, select_filter = set_settings
    fields = settings.SELECT_FIELDS + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                       'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.vega_range = FilterRange(low=5.0, high=6.0)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter, fields_list=fields)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 28

def test_load_data_with_rho_range(set_settings):
    start_date, end_date, select_filter = set_settings
    fields = settings.SELECT_FIELDS + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                       'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.strike_range = FilterRange(low=1900, high=2500)
    select_filter.rho_range = FilterRange(low=100.0, high=200.0)

    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter, fields_list=fields)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 116


def test_load_data_with_open_interest_range(set_settings):
    start_date, end_date, select_filter = set_settings
    fields = settings.SELECT_FIELDS + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                       'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.strike_range = FilterRange(low=1900, high=2500)
    select_filter.open_interest_range = FilterRange(low=100)
    # fltr = {
    #     'option_type': OptionType.CALL,
    #     'strike': {'low': 1900, 'high': 2500},
    #     'open_interest': {'low': 100, 'high': 10_000_000}
    # }
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter, fields_list=fields)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 391

def test_load_data_with_implied_volatility_range(set_settings):
    start_date, end_date, select_filter = set_settings
    fields = settings.SELECT_FIELDS + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                       'open_interest']
    select_filter.option_type = OptionType.CALL
    select_filter.strike_range = FilterRange(low=1900, high=2500)
    select_filter.implied_volatility_range = FilterRange(low=0.5, high=1.0)
    fltr = {
        'option_type': OptionType.CALL,
        'strike': {'low': 1900, 'high': 2500},
        'implied_volatility': {'low': 0.5, 'high': 1.0}
    }
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter, fields_list=fields)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 7

def test_load_data_with_all_range_filters(set_settings):
    start_date, end_date, select_filter = set_settings
    fields = settings.SELECT_FIELDS + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                       'open_interest']
    select_filter.option_type = OptionType.PUT
    select_filter.expiration_range = FilterRange(low=datetime.date(2016, 5, 1), high=datetime.date(2016, 8, 31))
    select_filter.strike_range = FilterRange(low=1500, high=2500)
    select_filter.delta_range = FilterRange(low=-0.80, high=-0.05)
    select_filter.gamma_range = FilterRange(low=0.0, high=0.0025)
    select_filter.theta_range = FilterRange(low=-0.4, high=-0.2)
    select_filter.vega_range = FilterRange(low=2.5, high=4.5)
    select_filter.rho_range = FilterRange(low=-500.0, high=-90.0)
    select_filter.open_interest_range = FilterRange(low=100, high=100_000)
    select_filter.implied_volatility_range = FilterRange(low=0.20, high=0.25)
    fltr = {
        'option_type': OptionType.PUT,
        'expiration': {'low': datetime.date(2016, 5, 1),
                       'high': datetime.date(2016, 8, 31)},
        'strike': {'low': 1500, 'high': 2500},
        'delta': {'low': -0.80, 'high': -0.05},
        'gamma': {'low': 0.0, 'high': 0.0025},
        'theta': {'low': -0.4, 'high': -0.2},
        'vega': {'low': 2.5, 'high': 4.5},
        'rho': {'low': -500.0, 'high': -90.0},
        'open_interest': {'low': 100, 'high': 100_000},
        'implied_volatility': {'low': 0.20, 'high': 0.25}
    }
    sql_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter, fields_list=fields)
    sql_loader.load_cache(start_date)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.get_next_option_chain(quote_datetime=start_date) #, symbol='SPXW', filters=fltr)

    assert len(options) == 16
