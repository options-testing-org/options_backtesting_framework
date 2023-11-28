import datetime

from options_framework.config import settings
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
    sql_loader.load_data(quote_datetime=start_date, symbol='SPXW')

    assert len(options) == 4806

def test_sql_load_call_options_from_database(database_settings_file_name):
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(database_settings_file_name)
    options = []

    def on_data_loaded(quote_datetime: datetime.datetime, option_chain: list[Option]):
        nonlocal options
        options = option_chain

    sql_loader.bind(option_chain_loaded=on_data_loaded)
    sql_loader.load_data(quote_datetime=start_date, symbol='SPXW', option_type_filter=OptionType.CALL)

    assert len(options) == 2403