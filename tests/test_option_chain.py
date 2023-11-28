import datetime

import pytest

from options_framework.option_chain import OptionChain
from options_framework.data.file_data_loader import FileDataLoader

@pytest.fixture
def file_data_loader(datafile_settings_file_name):
    data_loader = FileDataLoader(datafile_settings_file_name)
    option_chain = OptionChain()
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
    yield data_loader, option_chain

def test_load_option_chain(file_data_loader, datafile_file_name):
    data_loader, option_chain = file_data_loader
    quote_datetime = datetime.datetime.strptime("03/01/2023", "%m/%d/%Y")

    data_loader.load_data(quote_datetime=quote_datetime, symbol='MSFT', file_path=datafile_file_name)

    assert len(option_chain.option_chain) == 2190
    assert len(option_chain.expirations) == 19
    assert len(option_chain.expiration_strikes[0][1]) == 58