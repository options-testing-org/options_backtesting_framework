import datetime

import pytest
from conftest import create_update_cache
from options_framework.config import settings
from options_framework.data.file_data_loader import FileDataLoader
from options_framework.option_types import OptionType, SelectFilter, FilterRange
from options_framework.option import Option

@pytest.fixture
def set_settings():
    original_value_3 = settings.data_format_settings
    settings.DATA_FORMAT_SETTINGS = "custom_settings.toml"
    start_date = datetime.datetime(2023, 3, 1)
    end_date = datetime.datetime(2023, 3, 31)
    options_filter = SelectFilter(symbol='MSFT')
    yield start_date, end_date, options_filter
    settings.data_format_settings = original_value_3

def test_file_data_loader_loads_my_data_file_settings(set_settings):
    # get current settings
    start_date, end_date, options_filter = set_settings
    settings_dict = settings.as_dict()
    assert "DATA_IMPORT_NAME" not in settings_dict.keys()

    FileDataLoader(start=start_date, end=end_date, select_filter=options_filter)

    # verify new settings after instantiating file data loader
    settings_dict = settings.as_dict()
    assert "DATA_IMPORT_NAME" in settings_dict.keys()
    assert "DATA_IMPORT_FILE_PROPERTIES" in settings_dict.keys()
    assert "FIELD_MAPPING" in settings_dict.keys()

def test_file_data_loader_maps_file_columns_to_fields(set_settings):
    start_date, end_date, options_filter = set_settings
    file_data_loader = FileDataLoader(start=start_date, end=end_date, select_filter=options_filter)
    assert file_data_loader.field_mapping['symbol'] == 1
    assert file_data_loader.field_mapping['option_type'] == 6

def test_file_data_loader_load_data_loads_options_records_from_file(set_settings, datafile_file_name):
    start_date, end_date, options_filter = set_settings
    quote_datetime = datetime.datetime.strptime("03/01/2023", "%m/%d/%Y")
    file_data_loader = FileDataLoader(start=start_date, end=end_date, select_filter=options_filter)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    file_data_loader.bind(option_chain_loaded=on_data_loaded)
    file_data_loader.get_next_option_chain(quote_datetime=quote_datetime)
    assert len(options) == 2190

def test_file_data_loader_option_type_filter(set_settings, datafile_file_name):
    start_date, end_date, options_filter = set_settings
    options_filter.option_type = OptionType.PUT
    quote_datetime = datetime.datetime.strptime("03/01/2023", "%m/%d/%Y")
    file_data_loader = FileDataLoader(start=start_date, end=end_date, select_filter=options_filter)

    options_data = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options_data
        options_data = option_chain

    file_data_loader.bind(option_chain_loaded=on_data_loaded)
    file_data_loader.get_next_option_chain(quote_datetime=quote_datetime)

    assert len(options_data) == 1095

def test_cboe_file_data_loader_with_range_filters():
    start = datetime.datetime(2022, 11, 2, 9, 31) #.strptime("11/2/2022", "%m/%d/%Y")
    end = start = datetime.datetime(2022, 11, 2, 16, 15) #.strptime("11/2/2022", "%m/%d/%Y")
    settings.DATA_FORMAT_SETTINGS = "cboe_settings.toml"

    #data_file = "spx_11_02_2022.csv"
    fields = settings.SELECT_FIELDS + ['delta']

    option_filter = SelectFilter(symbol="SPXW", option_type=OptionType.CALL,
                                 expiration_range=FilterRange(low=datetime.date(2022, 11, 3),
                                                              high=datetime.date(2022, 11, 3)),
                                 strike_range=FilterRange(low=3830, high=3840),
                                 delta_range=FilterRange(low=0.60, high=0.61))
    file_data_loader = FileDataLoader(start=start, end=end, select_filter=option_filter, fields_list=fields)
    options_data = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options_data
        options_data = option_chain

    file_data_loader.bind(option_chain_loaded=on_data_loaded)

    file_data_loader.get_next_option_chain(quote_datetime=start)

    assert len(options_data) == 4
