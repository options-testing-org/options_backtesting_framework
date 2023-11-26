import datetime

from options_framework.config import settings
from options_framework.data.file_data_loader import FileDataLoader
from options_framework.option_types import OptionType
from pprint import pprint as pp
from pathlib import Path

def test_file_data_loader_loads_my_data_file_settings(datafile_settings_file_name):
    # get current settings
    settings_dict = settings.as_dict()
    assert "DATA_IMPORT_NAME" not in settings_dict.keys()

    FileDataLoader(datafile_settings_file_name)

    # verify new settings after instantiating file data loader
    settings_dict = settings.as_dict()
    assert "DATA_IMPORT_NAME" in settings_dict.keys()
    assert "DATA_IMPORT_FILE_PROPERTIES" in settings_dict.keys()
    assert "FIELD_MAPPING" in settings_dict.keys()


def test_file_data_loader_maps_file_columns_to_fields(datafile_settings_file_name):
    file_data_loader = FileDataLoader(datafile_settings_file_name)
    assert file_data_loader.field_mapping['symbol'] == 1
    assert file_data_loader.field_mapping['option_type'] == 6

def test_file_data_loader_load_data_loads_options_records_from_file(datafile_settings_file_name, datafile_file_name):
    file_data_loader = FileDataLoader(datafile_settings_file_name)
    options_data = file_data_loader.load_data(symbol='MSFT', file_path=datafile_file_name)
    assert len(options_data) == 2190

def test_file_data_loader_option_type_filter(datafile_settings_file_name, datafile_file_name):
    file_data_loader = FileDataLoader(datafile_settings_file_name)
    options_data = file_data_loader.load_data(symbol='MSFT', option_type_filter=OptionType.PUT,
                                              file_path=datafile_file_name)
    assert len(options_data) == 1095

def test_cboe_file_data_loader_with_range_filters():
    settings_file_name = "cboe_settings.toml"
    data_file = "spx_11_02_2022.csv"
    file_data_loader = FileDataLoader(settings_file_name)
    range_filter = {
        'expiration': {'low': datetime.datetime.strptime("11/3/2022" , "%m/%d/%Y"),
                       'high': datetime.datetime.strptime("11/3/2022", "%m/%d/%Y")},
        'strike': {'low': 3830, 'high': 3840},
        'delta': {'low': 0.60, 'high': 0.61}}
    options_data = file_data_loader.load_data(symbol='SPXW', option_type_filter=OptionType.CALL,
                                              range_filters=range_filter, file_path=data_file)

    assert len(options_data) == 791
