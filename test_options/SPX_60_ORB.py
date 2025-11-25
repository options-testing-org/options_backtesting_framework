import datetime
import sys
import os
os.environ["OPTIONS_FRAMEWORK_CONFIG_FOLDER"] = os.getcwd() + r'\config'
import pandas as pd
import numpy as np
from options_framework.spreads.vertical import Vertical
from options_framework.option_portfolio import OptionPortfolio


params = {
    'orb_time': datetime.time(10, 30),
    'stop_time': datetime.time(14, 0),
    'eod': datetime.time(15, 59),

}

max_float = sys.float_info.max
min_float = sys.float_info.min
ticker = 'SPXW'
if __name__ == "__main__":

    start_date = datetime.datetime.strptime("2016-04-15", "%Y-%m-%d")
    end_date = datetime.datetime.strptime("2016-06-27", "%Y-%m-%d")
    starting_cash = 100_000.0

    portfolio = OptionPortfolio(cash=starting_cash, start_date=start_date, end_date=end_date)

    df = pd.read_parquet(r'D:\stock_data\intraday\market\indices\SPX.parquet', engine="pyarrow")
    df = df[(df['quote_datetime'] >= start_date) & (df['quote_datetime'] <= end_date)]
    timeslots = df['quote_datetime'].unique()

    portfolio.initialize_ticker(symbol=ticker, quote_datetime=start_date)
    option_chain = portfolio.option_chains[ticker]

    timeslots = option_chain.datetimes
    dates = [x.date() for x in timeslots]
    dates = list(set(dates))
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
        position_id = None
        orb_high = min_float
        orb_low = max_float
        df_dt = df[(df['quote_datetime'] >= pd.Timestamp(dt)) & (
                df['quote_datetime'] < pd.Timestamp(dt + datetime.timedelta(days=1)))]
        for _, row in df_dt.iterrows():
            qd = row['quote_datetime']
            print(qd)
            hi = row['high']
            lo = row['low']
            open_ = row['open']
            close = row['close']
            tm = qd.time()
            if tm <= params['orb_time']:
                orb_high = hi if (hi > orb_high) else orb_high
                orb_low = lo if (lo < orb_low) else orb_low
            if tm == params['eod'] and len(portfolio.positions) > 0:
                portfolio.close_position(portfolio.positions[open_position.position_id])
            if tm > params['orb_time'] and tm < params['stop_time']:
                if len(portfolio.positions) == 0:
                    if can_open and ((hi > orb_high) or (lo < orb_low)):
                        portfolio.next(qd)
                        if len(option_chain.expirations) == 0:
                            can_open = False
                            continue
                        expiration = option_chain.expirations[0]
                        if expiration != dt:
                            can_open = False
                            continue
                        if hi > orb_high:

                            strikes = option_chain.expiration_strikes[expiration]
                            strikes = [x for x in strikes if x < orb_low]
                            strikes.sort(reverse=True)
                            short_strike = strikes[0]
                            long_strike = next(x for x in strikes if x <= short_strike - 10)
                            option_type = 'put'

                        if lo < orb_low:

                            strikes = option_chain.expiration_strikes[expiration]
                            strikes = [x for x in strikes if x > orb_high]
                            short_strike = strikes[0]
                            long_strike = next(x for x in strikes if x >= short_strike + 10)
                            option_type = 'call'

                        # open credit spread
                        vertical: Vertical = Vertical.get_vertical(option_chain=option_chain,
                                                                   expiration=expiration,
                                                                   option_type=option_type,
                                                                   long_strike=long_strike,
                                                                   short_strike=short_strike,
                                                                   quantity=-1)
                        if vertical.price > 0.70:
                            portfolio.open_position(vertical, quantity=-1)
                            position_id = vertical.position_id
                            can_open = False

                else:
                    portfolio.next(qd)
                    open_position = portfolio.positions[position_id]
                    price = open_position.price
                    pnl = open_position.get_profit_loss()
                    if pnl <= -140.0 or pnl >= 50.0:
                        portfolio.close_position(open_position)

    print(f'ending cash: {portfolio.cash}')
