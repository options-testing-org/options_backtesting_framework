import datetime
from tempfile import NamedTemporaryFile
from pathlib import Path

from options_framework.option_types import SelectFilter, OptionType, FilterRange, OptionPositionType
from options_framework.spreads.single import Single
from options_framework.test_manager import OptionTestManager
from options_framework.data.data_loader import DataLoader
from options_framework.utils.helpers import temp_data_dir_cleanup
from options_framework.option_chain import OptionChain

def test_post_init_removes_existing_files_from_temp_dir():
    temp_dir = Path.cwd().joinpath('temp_data')
    if not temp_dir.exists():
        temp_dir.mkdir()

    # create some temp files
    for i in range(5):
        with NamedTemporaryFile(delete=False, dir='./temp_data') as f:
            x = Path(f.name)

    start_date = datetime.datetime(2014, 5, 1)
    end_date = datetime.datetime(2014, 6, 30)
    starting_cash = 100_000.0
    select_filter = SelectFilter()

    tm = OptionTestManager(start_datetime=start_date, end_datetime=end_date,
                           select_filter=select_filter, starting_cash=starting_cash)

    files = [x for x in temp_dir.iterdir() if x.is_file()]
    assert len(files) == 0


def test_get_parquet_test_manager(parquet_daily_loader_settings):
    start_date = datetime.datetime(2014, 5, 1)
    end_date = datetime.datetime(2014, 6, 30)
    starting_cash = 100_000.0
    select_filter = SelectFilter()
    symbol = 'AAPL'

    tm = OptionTestManager(start_datetime=start_date, end_datetime=end_date,
                                            select_filter=select_filter, starting_cash=starting_cash)
    tm.initialize_ticker(symbol, quote_datetime=start_date)
    options = tm.option_chains[symbol].option_chain
    option = [op for op in options if op.option_id == 'AAPL140502C00485000'][0]
    expirations = tm.option_chains[symbol].expirations
    expiration_strikes = tm.option_chains[symbol].expiration_strikes[expirations[0]]
    assert isinstance(tm.data_loader, DataLoader)
    assert isinstance(tm.option_chains, dict)
    assert symbol in tm.option_chains
    assert option.price == 105.95
    assert 590.0 in expiration_strikes
    assert len(expirations) == len(tm.option_chains[symbol].expiration_strikes.keys())
    assert tm.portfolio.cash == 100_000


    # remove any pickle files created
    tm.de_initialize()

def test_get_sql_data_loader_test_manager(parquet_daily_loader_settings):
    start_date = datetime.datetime(2016, 3, 1, 9, 31)
    end_date = datetime.datetime(2016, 3, 1, 16,15)
    starting_cash = 100_000.0
    select_filter = SelectFilter()

    option_test_manager = OptionTestManager(start_datetime=start_date, end_datetime=end_date,
                                            select_filter=select_filter, starting_cash=starting_cash)
    assert isinstance(option_test_manager.data_loader, DataLoader)
    assert isinstance(option_test_manager.option_chains, dict)

# def test_manager_portfolio_open_triggers_option_updates_load():
#     start_date = datetime.datetime(2016, 3, 1, 9, 31)
#     end_date = datetime.datetime(2016, 3, 2, 16, 15)
#     starting_cash = 100_000.0
#     select_filter = SelectFilter(option_type=OptionType.CALL, strike_offset=FilterRange(low=50, high=50))
#
#     option_test_manager = OptionTestManager(start_datetime=start_date, end_datetime=end_date,
#                                             select_filter=select_filter, starting_cash=starting_cash)
#     option_test_manager.initialize_ticker('SPXW', start_date)
#
#     portfolio = option_test_manager.portfolio
#
#     option_chain = option_test_manager.option_chains['SPXW']
#     expiration = datetime.date(2016, 3, 2)
#     single = Single.get_single(option_chain=option_chain, expiration=expiration, option_type=OptionType.CALL,
#                                option_position_type= OptionPositionType.LONG, strike=1910)
#     assert single.option.update_cache is None
#     portfolio.open_position(option_position=single, quantity=1)
#     assert len(single.option.update_cache) > 0
#     assert single.option.quote_datetime == start_date
#     next_quote = datetime.datetime(2016, 3, 1, 9, 32)
#
#     # advance to the next quote
#     portfolio.next(next_quote)
#     assert single.option.quote_datetime == next_quote

