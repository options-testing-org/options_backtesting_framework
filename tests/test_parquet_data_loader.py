import datetime
import pytest
import pandas as pd
import dill
from pathlib import Path
import os
from options_framework.data.parquet_data_loader import ParquetDataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter, FilterRange
from mocks import Nexter


from options_framework.config import settings

@pytest.fixture
def get_settings(request):
    start_date = datetime.datetime.strptime('2017-05-01', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2018-04-30', '%Y-%m-%d')
    return start_date, end_date

@pytest.fixture
def option_object(request):
    test_data_dir = Path(settings['test_data_dir'])
    option_file = test_data_dir.joinpath('data_files', 'option_object.dill')
    with open(option_file, "rb") as f:
        file_contents = f.read()
    test_option = dill.loads(file_contents)
    return test_option

@pytest.fixture
def cleanup(request):
    temp_dir = Path.cwd().joinpath('temp_data')
    if not temp_dir.exists():
        temp_dir.mkdir()
    for x in temp_dir.iterdir():
        if x.is_file():
            os.remove(x)


def test_load_daily_option_chain_data(parquet_daily_loader_settings, get_settings, cleanup):
    start_date, end_date = get_settings
    symbol = 'MSFT'

    select_filter = SelectFilter()
    parquet_loader = ParquetDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    pickle_file = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, pickle: str):
        nonlocal pickle_file
        pickle_file = pickle

    parquet_loader.bind(option_chain_loaded=on_data_loaded)
    parquet_loader.load_option_chain_data(symbol, start_date, end_date)

    df = pd.read_pickle(pickle_file)
    assert df['quote_datetime'].min().to_pydatetime() == start_date
    assert df['quote_datetime'].max().to_pydatetime() == end_date
    assert 'implied_volatility' not in df.columns
    assert 'delta' not in df.columns
    os.unlink(pickle_file)

def test_load_daily_options_chain_with_iv_and_delta(parquet_daily_loader_settings, get_settings, cleanup):
    start_date, end_date = get_settings
    symbol ='IBM'

    select_filter = SelectFilter()
    parquet_loader = ParquetDataLoader(start=start_date, end=end_date, select_filter=select_filter,
                                       extended_option_attributes=['implied_volatility', 'delta'])
    pickle_file = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, pickle: str):
        nonlocal pickle_file
        pickle_file = pickle

    parquet_loader.bind(option_chain_loaded=on_data_loaded)
    parquet_loader.load_option_chain_data(symbol, start_date, end_date)

    df = pd.read_pickle(pickle_file)
    assert 'implied_volatility' in df.columns
    assert 'delta' in df.columns
    os.unlink(pickle_file)

def test_load_daily_option_updates_when_option_is_opened_adds_updates_till_expiration(parquet_daily_loader_settings, option_object, cleanup):
    symbol = 'AAPL'
    start_date = datetime.datetime.strptime('2014-02-05', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2014-02-10', '%Y-%m-%d')
    select_filter = SelectFilter()
    parquet_loader = ParquetDataLoader(start=start_date, end=end_date, select_filter=select_filter)

    nexter = Nexter()
    pickle_file = None
    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, pickle: str):
        nonlocal pickle_file
        pickle_file = pickle

    # Set up bindings so events are fired
    # loads the data for this symbol for the test period
    parquet_loader.bind(option_chain_loaded=on_data_loaded)
    # bind data loader handler to open new position event
    nexter.bind(new_position_opened=parquet_loader.on_options_opened)
    nexter.bind(next=option_object.next_update)

    # load data for test which includes the option we are opening
    parquet_loader.load_option_chain_data(symbol, start_date, end_date)

    # option open event is fired - data loader event handler loads the updates for this option
    nexter.open_option_position([option_object])

    first_update_date = start_date + datetime.timedelta(days=1)
    last_update_date = option_object.expiration

    option_update_df = option_object.update_cache

    assert option_update_df is not None
    assert option_update_df['quote_datetime'].min().to_pydatetime() == first_update_date
    assert option_update_df['quote_datetime'].max().to_pydatetime().date() == last_update_date

    os.unlink(pickle_file)


def test_load_cboe_parquet_option_chain(parquet_cboe_loader_settings):
    start_date = datetime.datetime.strptime('2016-03-08', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2016-03-10', '%Y-%m-%d')
    symbol = 'SPXW'

    select_filter = SelectFilter()
    parquet_loader = ParquetDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    pickle_file = None

    def on_data_loaded(symbol: str, quote_datetime: datetime.datetime, pickle: str):
        nonlocal pickle_file
        pickle_file = pickle

    parquet_loader.bind(option_chain_loaded=on_data_loaded)
    parquet_loader.load_option_chain_data(symbol, start_date, end_date)

    df = pd.read_pickle(pickle_file)

    assert df['quote_datetime'].min().to_pydatetime() == start_date + datetime.timedelta(hours=9, minutes=31)
    assert df['quote_datetime'].max().to_pydatetime() == end_date + datetime.timedelta(hours=-7, minutes=-45)

    os.unlink(pickle_file)