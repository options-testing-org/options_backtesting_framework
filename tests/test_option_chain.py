import datetime

import pytest

from options_framework.option_chain import OptionChain
from options_framework.data.file_data_loader import FileDataLoader
from options_framework.data.sql_data_loader import SQLServerDataLoader
from options_framework.option_types import OptionType
from options_framework.config import settings

@pytest.fixture
def file_data_loader():
    original_value_1 = settings.data_loader_type
    original_value_2 = settings.data_files_folder
    original_value_3 = settings.data_file_format_settings
    settings.DATA_LOADER_TYPE = "FILE_DATA_LOADER"
    settings.DATA_FILES_FOLDER = "test_data"
    settings.DATA_FILE_FORMAT_SETTINGS = "custom_settings.toml"
    data_loader = FileDataLoader()
    option_chain = OptionChain()
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
    yield data_loader, option_chain
    settings.data_loader_type = original_value_1
    settings.data_files_folder = original_value_2
    settings.data_file_format_settings = original_value_3

@pytest.fixture()
def db_data_loader():
    data_loader = SQLServerDataLoader()
    option_chain = OptionChain()
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
    yield data_loader, option_chain

def test_load_option_chain_from_db(db_data_loader):
    data_loader, option_chain = db_data_loader
    quote_datetime = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    data_loader.load_option_chain(quote_datetime=quote_datetime, symbol='SPXW', filters={'option_type':OptionType.CALL})

    assert len(option_chain.option_chain) == 2403

def test_load_option_chain_from_file(file_data_loader, datafile_file_name):
    data_loader, option_chain = file_data_loader
    quote_datetime = datetime.datetime.strptime("03/01/2023", "%m/%d/%Y")

    data_loader.load_option_chain(quote_datetime=quote_datetime, symbol='MSFT', data_file_name=datafile_file_name)

    assert len(option_chain.option_chain) == 2190
    assert len(option_chain.expirations) == 19
    assert len(option_chain.expiration_strikes[0][1]) == 58

