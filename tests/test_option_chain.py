import datetime
import pandas as pd
from mocks import MockIntegrationDataLoader, MockEventDispatcher
import pytest

from options_framework.data.parquet_data_loader import ParquetDataLoader
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionType, SelectFilter
from options_framework.config import settings

@pytest.fixture
# Bind option chain to the mock data loader
def setup():
    symbol = 'AAPL'
    start_date = datetime.datetime.strptime('2014-02-05', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2014-02-10', '%Y-%m-%d')
    data_loader = MockIntegrationDataLoader(start=start_date, end=end_date, select_filter=SelectFilter())
    option_chain = OptionChain(symbol, start_date, end_date)
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
    data_loader.load_option_chain_data(symbol, start_date, end_date)
    return symbol, start_date, end_date, option_chain, data_loader

def test_option_chain_contains_only_quotedate_option_records(setup):
    quote_date = datetime.datetime.strptime('2014-02-05', '%Y-%m-%d')
    #sf = SelectFilter(option_type=OptionType.CALL)
    symbol, start_date, end_date, option_chain, dl = setup

    assert all([x for x in option_chain.option_chain if x.quote_datetime == quote_date])

def test_option_chain_has_new_options_after_next_event_is_emitted(setup):
    symbol, start_date, end_date, option_chain, dl = setup

    next_day = datetime.datetime.strptime('2014-02-06', '%Y-%m-%d')

    nexter = MockEventDispatcher()
    nexter.bind(next=option_chain.on_next)
    nexter.do_next(next_day)

    assert all([x for x in option_chain.option_chain if x.quote_datetime == next_day])

def test_open_option(setup):
    symbol, start_date, end_date, option_chain, dl = setup

    nexter = MockEventDispatcher()

    op = option_chain.option_chain[2]
    nexter.bind(new_position_opened=dl.on_options_opened)
    nexter.bind(next=op.next_update)

    nexter.open_option_position([op])

    first_price = op.price
    price2 = round(2.305, 2)
    price3 = round(7.175, 2)

    next_day = start_date + datetime.timedelta(days=1)
    nexter.do_next(next_day)

    assert op.quote_datetime == next_day
    assert op.price == price2

    next_day = next_day + datetime.timedelta(days=1)
    nexter.do_next(next_day)

    assert op.quote_datetime == next_day
    assert op.price == price3

# This takes a very long time to run. Remove leading _ to run this test.
def _test_option_chain_fires_load_next_data_event_when_cannot_load_quote_datetime(parquet_cboe_loader_settings):
    start_date = datetime.datetime.strptime('2016-03-08', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2016-03-21', '%Y-%m-%d')
    symbol = 'SPXW'
    settings['data_settings']['options_folder'] = 'D:\options_data\intraday'

    # create objects for testing
    data_loader = ParquetDataLoader(start=start_date, end=end_date, select_filter=SelectFilter())
    pickle_file = None

    def on_data_loaded(quote_datetime: datetime.datetime, pickle: str, datetimes: list[datetime.datetime]):
        nonlocal pickle_file
        pickle_file = pickle

    data_loader.bind(option_chain_loaded=on_data_loaded)

    option_chain = OptionChain(symbol=symbol, quote_datetime=start_date, end_datetime=end_date)

    # create bindings. This is normally done in the test manager
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
    option_chain.bind(load_next_data=data_loader.load_option_chain_data)

    # data loader starts the process by loading the first batch of data
    # this emits the option_chain_loaded event which the option chain handles
    data_loader.load_option_chain_data(symbol=symbol, start=start_date, end=end_date)
    #
    # # option chain should be loaded with data from start_date now
    first_pickle_file = pickle_file
    df = pd.read_pickle(first_pickle_file)
    last_date = df.iloc[-1]['quote_datetime']
    assert last_date < end_date

    option_chain.on_next(quote_datetime=last_date) # this should load the last date in the cache

    next_date = option_chain.datetimes[0]
    option_chain.on_next(next_date)

    assert first_pickle_file != pickle_file




