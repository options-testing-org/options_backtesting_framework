import datetime
from tempfile import NamedTemporaryFile
from pathlib import Path
import pandas as pd
import numpy as np
import sys
from pprint import pprint as pp

from options_framework.option_types import OptionPositionType
from options_framework.spreads.single import Single
from options_framework.spreads.vertical import Vertical
from options_framework.test_manager import OptionTestManager
from options_framework.utils.helpers import temp_data_dir_cleanup
from options_framework.option_chain import OptionChain
from options_framework.config import settings

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


    tm = OptionTestManager(start_datetime=start_date, end_datetime=end_date,
                           starting_cash=starting_cash)

    files = [x for x in temp_dir.iterdir() if x.is_file()]
    assert len(files) == 0


# def test_get_parquet_test_manager(parquet_daily_loader_settings):
#     start_date = datetime.datetime(2014, 5, 1)
#     end_date = datetime.datetime(2014, 6, 30)
#     starting_cash = 100_000.0
#     symbol = 'AAPL'
#
#     tm = OptionTestManager(start_datetime=start_date, end_datetime=end_date, starting_cash=starting_cash)
#     tm.initialize_ticker(symbol, quote_datetime=start_date)
#     options = tm.option_chains[symbol].option_chain
#     option = [op for op in options if op.option_id == 'AAPL140502C00485000'][0]
#     expirations = tm.option_chains[symbol].expirations
#     expiration_strikes = tm.option_chains[symbol].expiration_strikes[expirations[0]]
#     assert isinstance(tm.option_chains, dict)
#     assert symbol in tm.option_chains
#     assert option.price == 105.95
#     assert 590.0 in expiration_strikes
#     assert len(expirations) == len(tm.option_chains[symbol].expiration_strikes.keys())
#     assert tm.portfolio.cash == 100_000


def test_cboe_initialize_data(parquet_cboe_loader_settings):
    settings['data_settings']['options_folder'] = 'D:\options_data\intraday'
    start_date = datetime.datetime.strptime("2016-03-01", "%Y-%m-%d")
    end_date = datetime.datetime.strptime("2016-04-01", "%Y-%m-%d")
    starting_cash = 100_000.0

    test_manager = OptionTestManager(start_datetime=start_date, end_datetime=end_date, starting_cash=starting_cash)
    portfolio = test_manager.portfolio

    df = pd.read_parquet(settings['data_settings']['stock_data_file'])
    df = df[(df['quote_datetime'] >= start_date) & (df['quote_datetime'] <= end_date)]

    test_manager.initialize_ticker(symbol='SPXW', quote_datetime=start_date)
    option_chain = test_manager.option_chains['SPXW']

    dates = np.unique([d.date() for d in option_chain.datetimes]).tolist()
    dates.sort()

    params = {
        'orb_time': datetime.time(10, 30),
        'stop_time': datetime.time(14, 0),
        'eod': datetime.time(15, 59),
    }

    max_float = sys.float_info.max
    min_float = sys.float_info.min

    for dt in dates:
        can_open = True
        orb_high = min_float
        orb_low = max_float
        df_dt = df[(df['quote_datetime'] >= pd.Timestamp(dt)) & (
                    df['quote_datetime'] < pd.Timestamp(dt + datetime.timedelta(days=1)))]
        for _, row in df_dt.iterrows():
            qd = row['quote_datetime']
            hi = row['high']
            lo = row['low']
            open_ = row['open']
            close = row['close']
            tm = qd.time()
            if tm <= params['orb_time']:
                orb_high = hi if (hi > orb_high) else orb_high
                orb_low = lo if (lo < orb_low) else orb_low
            if tm == params['eod'] and len(portfolio.positions) > 0:
                portfolio.close_position(portfolio.positions[0])
            if tm > params['orb_time'] and tm < params['stop_time']:
                if len(portfolio.positions) == 0:
                    if can_open and ((hi > orb_high) or (lo < orb_low)):
                        portfolio.next(qd)
                        if len(option_chain.expirations) == 0:
                            can_open = False
                            continue

                        if hi > orb_high:

                            expiration = option_chain.expirations[0]
                            strikes = option_chain.expiration_strikes[expiration]
                            strikes = [x for x in strikes if x < orb_low]

                            vertical: Vertical = Vertical.get_vertical()
                            pass
                            # open put credit spread
                        if lo < orb_low:
                            portfolio.next(qd)
                            expiration = option_chain.expirations[0]
                            strikes = option_chain.expiration_strikes[expiration]
                            strikes = [x for x in strikes if x > orb_high]
                            short_strike = strikes[0]
                            long_strike = next(x for x in strikes if x >= short_strike + 10)
                            vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain,
                                                                              expiration=expiration,
                                                                              option_type='call',
                                                                              long_strike=long_strike,
                                                                              short_strike=short_strike,
                                                                              quantity=-1)
                            # open call credit spread
                            if vertical_spread.price > 0.70:
                                portfolio.open_position(vertical_spread, quantity=-1)
                                can_open = False
                            pass
                else:
                    portfolio.next(qd)
                    open_position = portfolio.positions[0]
                    price = open_position.price
                    pnl = open_position.get_profit_loss()
                    if pnl <= -140.0 or pnl >= 50.0:
                        portfolio.close_position(open_position)
                    pass

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

