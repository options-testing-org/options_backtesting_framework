import datetime
import pytest
import pandas as pd
import dill
from pathlib import Path
import os
from options_framework.data.parquet_data_loader import ParquetDataLoader
from options_framework.option import Option
import options_framework.option_chain as option_chain
from options_framework.option_types import OptionType, SelectFilter, FilterRange
from mocks import MockEventDispatcher
import pickle


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

    def on_data_loaded(quote_datetime: datetime.datetime, pickle: str, datetimes: list[datetime.datetime]):
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

    def on_data_loaded(quote_datetime: datetime.datetime, pickle: str, datetimes: list[datetime.datetime]):
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

    nexter = MockEventDispatcher()
    pickle_file = None
    def on_data_loaded(quote_datetime: datetime.datetime, pickle: str, datetimes: list[datetime.datetime]):
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

    def on_data_loaded(quote_datetime: datetime.datetime, pickle: str, datetimes: list[datetime.datetime]):
        nonlocal pickle_file
        pickle_file = pickle

    parquet_loader.bind(option_chain_loaded=on_data_loaded)
    parquet_loader.load_option_chain_data(symbol, start_date, end_date)

    df = pd.read_pickle(pickle_file)

    assert df['quote_datetime'].min().to_pydatetime() == start_date + datetime.timedelta(hours=9, minutes=31)
    assert df['quote_datetime'].max().to_pydatetime() == end_date + datetime.timedelta(hours=-7, minutes=-45)

    os.unlink(pickle_file)

def test_load_cboe_with_expiration_filter_screens_for_0dte(parquet_cboe_loader_settings):
    start_date = datetime.datetime.strptime('2016-03-08', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2016-03-10', '%Y-%m-%d')
    symbol = 'SPXW'


    # load with no screening
    select_filter = SelectFilter()
    parquet_loader = ParquetDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    pickle_file = None

    def on_data_loaded(quote_datetime: datetime.datetime, pickle: str, datetimes: list[datetime.datetime]):
        nonlocal pickle_file
        pickle_file = pickle

    parquet_loader.bind(option_chain_loaded=on_data_loaded)
    parquet_loader.load_option_chain_data(symbol, start_date, end_date)

    # Check for dte before screening
    df = pd.read_pickle(pickle_file)
    row = df.iloc[0]
    assert row['expiration'] > row['quote_datetime'].date()
    os.unlink(pickle_file)

    # set filter for 0DTE
    select_filter = SelectFilter()
    select_filter.expiration_dte = FilterRange(low=0, high=0)
    parquet_loader = ParquetDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    parquet_loader.bind(option_chain_loaded=on_data_loaded)

    pickle_file = None
    parquet_loader.load_option_chain_data(symbol, start_date, end_date)

    df = pd.read_pickle(pickle_file)
    row = df.iloc[0]
    assert row['expiration'] == row['quote_datetime'].date()

    os.unlink(pickle_file)

# This takes a very long time to run. Remove leading _ to run this test.
def _test_load_more_data_than_max_size_does_not_load_all_data(parquet_cboe_loader_settings):
    start_date = datetime.datetime.strptime('2016-03-08', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2016-04-30', '%Y-%m-%d')
    symbol = 'SPXW'

    settings['data_settings']['options_folder'] = 'D:\options_data\intraday'

    # load with 0DTE screening
    select_filter = SelectFilter()
    parquet_loader = ParquetDataLoader(start=start_date, end=end_date, select_filter=select_filter)
    pickle_file = None

    def on_data_loaded(quote_datetime: datetime.datetime, pickle: str, datetimes: list[datetime.datetime]):
        nonlocal pickle_file
        pickle_file = pickle

    parquet_loader.bind(option_chain_loaded=on_data_loaded)
    parquet_loader.load_option_chain_data(symbol, start_date, end_date)

    df = pd.read_pickle(pickle_file)
    assert df['quote_datetime'].max().month < end_date.month

    os.unlink(pickle_file)

    pass

def create_option(row: pd.Series) -> Option:
    option_id = row['option_id']
    option = Option(
        option_id=option_id,
        symbol=row['symbol'],
        expiration=row['expiration'],
        strike=row['strike'],
        option_type=OptionType.CALL if row['option_type'] == settings['data_settings']['call_value'] else OptionType.PUT,
        quote_datetime=row['quote_datetime'],
        spot_price=row['spot_price'],
        bid=row['bid'],
        ask=row['ask'],
        price=row['price'],
        delta=row['delta'] if 'delta' in row.index else None,
        gamma=row['gamma'] if 'gamma' in row.index else None,
        theta=row['theta'] if 'theta' in row.index else None,
        vega=row['vega'] if 'vega' in row.index else None,
        rho=row['rho'] if 'rho' in row.index else None,
        volume=row['volume'] if 'volume' in row.index else None,
        open_interest=row['open_interest'] if 'open_interest' in row.index else None,
        implied_volatility=row['implied_volatility'] if 'implied_volatility' in row.index else None)
    return option

def test_option_to_pickle(parquet_cboe_loader_settings):

    start_date = datetime.datetime.strptime('2016-03-08', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2016-04-30', '%Y-%m-%d')

    option_required_fields = ['option_id', 'symbol', 'strike', 'expiration', 'option_type', 'quote_datetime',
                              'spot_price', 'bid', 'ask', 'price']
    optional_fields = ['delta', 'gamma', 'theta', 'vega', 'rho', 'open_interest', 'volume',
                       'implied_volatility']

    options_folder = Path('D:\options_data\intraday\SPX')
    pickle_folder= Path('D:\options_data\intraday_pkl')
    options_files = options_folder.glob('*.parquet')
    field_mapping = settings['data_settings']['field_mapping']
    columns = [field_mapping[f] for f in option_required_fields] + [field_mapping[f] for f in
                                                                              optional_fields]
    qd_field = settings['data_settings']['field_mapping']['quote_datetime']

    for of in options_files:
        df = pd.read_parquet(of, engine="pyarrow")
        df = df.rename(columns={old: new for (new, old) in field_mapping.items()})
        df = df.sort_values(by=['quote_datetime', 'expiration', 'option_type', 'strike'])
        df['expiration'] = df['expiration'].dt.date
        df['price'] = df['price'].round(2)
        df = df.iloc[:500]
        options = []
        for _, row in df.iterrows():
            option = create_option(row)
            options.append(option)

        option_pickle_folder = pickle_folder / of.stem
        option_pickle_folder.mkdir(parents=True, exist_ok=True)
        for option in options:
            opt_pkl_name = f"{option.option_id}_{option.quote_datetime.hour:0{2}}_{option.quote_datetime.minute:0{2}}.pkl"
            opt_pkl_path = option_pickle_folder / opt_pkl_name
            with open(opt_pkl_path, 'wb') as f:
                pickle.dump(option, f, protocol=pickle.HIGHEST_PROTOCOL)
    pass



