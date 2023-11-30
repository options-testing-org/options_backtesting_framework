import datetime

from options_framework.data.sql_data_loader import SQLServerDataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType


def test_sql_load_from_database(database_settings_file_name):
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    end_date = datetime.datetime.strptime("2016-03-31 16:15:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(database_settings_file_name)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW')

    assert len(options) == 4806


def test_sql_load_call_options_from_database(database_settings_file_name):
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(database_settings_file_name)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters={'option_type': OptionType.CALL})

    assert len(options) == 2403


def test_load_with_custom_field_selection(database_settings_file_name):
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    fields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'open_interest']
    sql_loader = SQLServerDataLoader(database_settings_file_name, fields)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters={'option_type': OptionType.CALL})

    option = options[0]

    assert option.delta is not None


def test_load_data_with_only_required_fields(database_settings_file_name):
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    fields = ['option_id', 'symbol', 'expiration', 'strike', 'option_type']

    sql_loader = SQLServerDataLoader(settings_file=database_settings_file_name, select_fields=fields,
                                     order_by_fields=['expiration', 'strike'])
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters={'option_type': OptionType.CALL})

    option = options[0]

    assert option.quote_datetime is None
    assert option.price is None


def test_load_data_with_expiration_range(database_settings_file_name):
    low_expiration = datetime.date(2016, 4, 1)
    hi_expiration = datetime.date(2016, 4, 30)
    fltr = {
        'option_type': OptionType.CALL,
        'expiration': {'low': low_expiration,
                       'high': hi_expiration},
    }
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(database_settings_file_name)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 681


def test_load_data_with_strike_range(database_settings_file_name):
    low_expiration = datetime.date(2016, 4, 1)
    hi_expiration = datetime.date(2016, 4, 30)
    fltr = {
        'option_type': OptionType.CALL,
        'expiration': {'low': low_expiration,
                       'high': hi_expiration},
        'strike': {'low': 1940, 'high': 1950}
    }
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(database_settings_file_name)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 12


def test_load_data_with_delta_range(database_settings_file_name):
    fields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']
    low_expiration = datetime.date(2016, 4, 1)
    hi_expiration = datetime.date(2016, 4, 30)
    fltr = {
        'option_type': OptionType.CALL,
        'expiration': {'low': low_expiration,
                       'high': hi_expiration},
        'strike': {'low': 1900, 'high': 2050},
        'delta': {'low': 0.60, 'high': 0.70}
    }
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(settings_file=database_settings_file_name, select_fields=fields)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 15


def test_load_data_with_gamma_range(database_settings_file_name):
    fields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']

    fltr = {
        'option_type': OptionType.CALL,
        'gamma': {'low': 0.009, 'high': 0.01}
    }
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(settings_file=database_settings_file_name, select_fields=fields)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 4

def test_load_data_with_theta_range(database_settings_file_name):
    fields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']

    fltr = {
        'option_type': OptionType.CALL,
        'expiration': {'low': datetime.date(2016, 5, 1),
                       'high': datetime.date(2016, 8, 31)},
        'theta': {'low': -0.4, 'high': -0.3}
    }
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(settings_file=database_settings_file_name, select_fields=fields)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 115

def test_load_data_with_vega_range(database_settings_file_name):
    fields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']

    fltr = {
        'option_type': OptionType.CALL,
        'vega': {'low': 5.0, 'high': 6.0}
    }
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(settings_file=database_settings_file_name, select_fields=fields)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 28

def test_load_data_with_rho_range(database_settings_file_name):
    fields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']

    fltr = {
        'option_type': OptionType.CALL,
        'strike': {'low': 1900, 'high': 2500},
        'rho': {'low': 100.0, 'high': 200.0}
    }
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(settings_file=database_settings_file_name, select_fields=fields)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 116


def test_load_data_with_open_interest_range(database_settings_file_name):
    fields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']

    fltr = {
        'option_type': OptionType.CALL,
        'strike': {'low': 1900, 'high': 2500},
        'open_interest': {'low': 100, 'high': 10_000_000}
    }
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(settings_file=database_settings_file_name, select_fields=fields)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 391

def test_load_data_with_implied_volatility_range(database_settings_file_name):
    fields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']

    fltr = {
        'option_type': OptionType.CALL,
        'strike': {'low': 1900, 'high': 2500},
        'implied_volatility': {'low': 0.5, 'high': 1.0}
    }
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(settings_file=database_settings_file_name, select_fields=fields)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 7

def test_load_data_with_all_range_filters(database_settings_file_name):
    fields = SQLServerDataLoader._default_fields + ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility',
                                                    'open_interest']
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
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(settings_file=database_settings_file_name, select_fields=fields)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_option_chain(quote_datetime=start_date, symbol='SPXW', filters=fltr)

    assert len(options) == 16
