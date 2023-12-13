import datetime

import pytest

from options_framework.option_chain import OptionChain
from options_framework.data.file_data_loader import FileDataLoader
from options_framework.data.sql_data_loader import SQLServerDataLoader
from options_framework.option_types import OptionType, SelectFilter
from options_framework.config import settings

@pytest.fixture
def file_data_loader():
    original_value_3 = settings.DATA_FORMAT_SETTINGS
    settings.DATA_FORMAT_SETTINGS = "custom_settings.toml"
    start_end = datetime.datetime(2023, 3, 1)
    select_filter = SelectFilter(symbol='MSFT')
    data_loader = FileDataLoader(start=start_end, end=start_end, select_filter=select_filter)
    option_chain = OptionChain()
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
    yield data_loader, option_chain
    settings.data_file_format_settings = original_value_3

@pytest.fixture()
def db_data_loader():
    original_value_3 = settings.DATA_FORMAT_SETTINGS
    settings.DATA_FORMAT_SETTINGS = "sql_server_cboe_settings.toml"
    start = datetime.datetime(2016, 3, 1, 9, 31)
    end = start = datetime.datetime(2016, 3, 1, 9, 32)
    select_filter = SelectFilter(symbol='SPXW', option_type=OptionType.CALL)
    data_loader = SQLServerDataLoader(start=start, end=end, select_filter=select_filter)
    option_chain = OptionChain()
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
    yield data_loader, option_chain, start
    settings.DATA_FORMAT_SETTINGS = original_value_3

def test_load_option_chain_from_db(db_data_loader):
    data_loader, option_chain, quote_datetime = db_data_loader
    data_loader.load_cache(quote_datetime)
    data_loader.get_option_chain(quote_datetime=quote_datetime)

    assert len(option_chain.option_chain) == 2403

def test_load_option_chain_from_file(file_data_loader):
    data_loader, option_chain = file_data_loader
    quote_datetime = datetime.datetime(2023, 3, 1) #.strptime("03/01/2023", "%m/%d/%Y")

    data_loader.get_option_chain(quote_datetime=quote_datetime)

    assert len(option_chain.option_chain) == 2190
    assert len(option_chain.expirations) == 19
    assert len(option_chain.expiration_strikes[option_chain.expirations[0]]) == 58

