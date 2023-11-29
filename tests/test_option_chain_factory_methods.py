import datetime

import pytest

from options_framework.data.sql_data_loader import SQLServerDataLoader
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionType


@pytest.fixture()
def db_data_loader(database_settings_file_name):
    data_loader = SQLServerDataLoader(settings_file=database_settings_file_name)
    option_chain = OptionChain()
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)

    range_filter = {
        'expiration': {'low': datetime.date(2016, 3, 1),
                       'high': datetime.date(2016, 3, 31)},
        'strike': {'low': 1850, 'high': 2150}
    }
    quote_datetime = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    data_loader.load_data(quote_datetime=quote_datetime,
                          symbol='SPXW',
                          option_type_filter=OptionType.PUT,
                          range_filters=range_filter)
    yield option_chain

def test_get_single(db_data_loader):
    option_chain = db_data_loader

    single_option  = option_chain.get_single_option(expiration=datetime.date(2016, 3,2),
                                                    option_type=OptionType.PUT,
                                                    strike=1950)

    pass


