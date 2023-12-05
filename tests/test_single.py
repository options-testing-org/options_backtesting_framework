import pytest
import datetime

from options_framework.data.sql_data_loader import SQLServerDataLoader
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionType, OptionCombinationType, OptionStatus, SelectFilter, FilterRange
from options_framework.spreads.option_combo import OptionCombination
from options_framework.spreads.single import Single
from options_framework.config import settings

@pytest.fixture()
def option_chain():
    original_value_1 = settings.DATA_LOADER_TYPE
    settings.DATA_LOADER_TYPE = "SQL_DATA_LOADER"
    settings.DATA_FORMAT_SETTINGS = 'sql_server_cboe_settings.toml'
    start_date = datetime.datetime(2016,3, 1, 9, 31)
    end_date = datetime.datetime(2016, 3, 1, 9, 32)
    select_filter = SelectFilter(symbol="SPXW", option_type=OptionType.PUT,
                                 expiration_range=FilterRange(low=datetime.date(2016, 3, 1),
                                                              high=datetime.date(2016, 3, 31)),
                                 strike_range=FilterRange(low=1850,high=2150))
    data_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    data_loader.load_cache(start_date)
    option_chain = OptionChain()
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)

    # fltr = {
    #     'option_type': OptionType.PUT,
    #     'expiration': {'low': datetime.date(2016, 3, 1),
    #                    'high': datetime.date(2016, 3, 31)},
    #     'strike': {'low': 1850, 'high': 2150}
    # }
    quote_datetime = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    data_loader.get_next_option_chain(quote_datetime=quote_datetime)
    yield option_chain
    settings.DATA_LOADER_TYPE = original_value_1

@pytest.fixture
def option_values():
    expiration = datetime.date(2016, 3, 2)
    option_type = OptionType.PUT
    strike=1950
    return expiration, option_type, strike


def test_get_single_option(option_chain, option_values):
    expiration, option_type, strike = option_values
    options = option_chain.option_chain
    single_option = Single.get_single_option(options=options, expiration=expiration, option_type=option_type,
                                             strike=strike)

    assert single_option.option_combination_type == OptionCombinationType.SINGLE
    assert single_option.expiration == expiration
    assert single_option.option_type == option_type
    assert single_option.strike == strike

def test_open_single_option(option_chain, option_values):
    expiration, option_type, strike = option_values
    options = option_chain.option_chain
    single_option = Single.get_single_option(options=options, expiration=expiration, option_type=option_type,
                                             strike=strike)

    single_option.open_trade(quantity=1)

    assert OptionStatus.TRADE_IS_OPEN in single_option.option.status
    assert single_option.option.quantity == 1

