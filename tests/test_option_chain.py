import datetime
from pathlib import Path
from options_framework.option_chain import OptionChain
from options_framework.data.file_data_loader import FileDataLoader
from options_framework.config import settings

def test_option_chain_init_with_day_quote_time_granularity(datafile_settings_file_name, datafile_file_name):
    quote_date = datetime.datetime(2023, 3, 1)
    data_loader = FileDataLoader(datafile_settings_file_name)

    oc = OptionChain(quote_datetime=quote_date, data_loader=data_loader)

    pass