import datetime

import pytest

from options_framework.config import settings
from options_framework.data.file_data_loader import FileDataLoader
from options_framework.option_types import OptionType
from options_framework.option import Option

@pytest.fixture
def set_settings():
    original_value_1 = settings.data_loader_type
    original_value_2 = settings.data_files_folder
    original_value_3 = settings.data_file_format_settings
    settings.DATA_LOADER_TYPE = "FILE_DATA_LOADER"
    settings.DATA_FILES_FOLDER = "test_data"
    settings.DATA_FILE_FORMAT_SETTINGS = "custom_settings.toml"
    yield
    settings.data_loader_type = original_value_1
    settings.data_files_folder = original_value_2
    settings.data_file_format_settings = original_value_3

def test_file_data_loader_loads_my_data_file_settings(set_settings):
    # get current settings
    settings_dict = settings.as_dict()
    assert "DATA_IMPORT_NAME" not in settings_dict.keys()

    FileDataLoader()

    # verify new settings after instantiating file data loader
    settings_dict = settings.as_dict()
    assert "DATA_IMPORT_NAME" in settings_dict.keys()
    assert "DATA_IMPORT_FILE_PROPERTIES" in settings_dict.keys()
    assert "FIELD_MAPPING" in settings_dict.keys()

def test_file_data_loader_maps_file_columns_to_fields(set_settings):
    file_data_loader = FileDataLoader()
    assert file_data_loader.field_mapping['symbol'] == 1
    assert file_data_loader.field_mapping['option_type'] == 6

def test_file_data_loader_load_data_loads_options_records_from_file(datafile_file_name):
    quote_datetime = datetime.datetime.strptime("03/01/2023", "%m/%d/%Y")
    file_data_loader = FileDataLoader()
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    file_data_loader.bind(option_chain_loaded=on_data_loaded)
    file_data_loader.load_option_chain(quote_datetime=quote_datetime,
                                       symbol='MSFT', data_file_name=datafile_file_name)
    assert len(options) == 2190

def test_file_data_loader_option_type_filter( datafile_file_name):
    quote_datetime = datetime.datetime.strptime("03/01/2023", "%m/%d/%Y")
    file_data_loader = FileDataLoader()

    options_data = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options_data
        options_data = option_chain

    file_data_loader.bind(option_chain_loaded=on_data_loaded)
    file_data_loader.load_option_chain(quote_datetime=quote_datetime,
                                       symbol='MSFT', filters={'option_type': OptionType.PUT},
                                       data_file_name=datafile_file_name)

    assert len(options_data) == 1095

def test_cboe_file_data_loader_with_range_filters():
    quote_datetime = datetime.datetime.strptime("11/2/2022", "%m/%d/%Y")
    settings.DATA_FILE_FORMAT_SETTINGS = "cboe_settings.toml"

    data_file = "spx_11_02_2022.csv"
    fields = FileDataLoader._default_fields + ['delta']
    file_data_loader = FileDataLoader(select_fields=fields)
    filter = {
        'option_type': OptionType.CALL,
        'expiration': {'low': datetime.date(2022, 11, 3), # datetime.datetime.strptime("11/3/2022" , "%m/%d/%Y"),
                       'high': datetime.date(2022, 11, 3)}, # datetime.datetime.strptime("11/3/2022", "%m/%d/%Y")},
        'strike': {'low': 3830, 'high': 3840},
        'delta': {'low': 0.60, 'high': 0.61}}
    options_data = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options_data
        options_data = option_chain

    file_data_loader.bind(option_chain_loaded=on_data_loaded)

    file_data_loader.load_option_chain(quote_datetime=quote_datetime,
                                       symbol='SPXW', filters=filter, data_file_name=data_file)

    assert len(options_data) == 4
