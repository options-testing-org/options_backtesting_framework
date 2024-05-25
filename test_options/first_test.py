import datetime
import math
import sys
import time
import tomllib

import backtrader as bt
import pandas as pd
from pathlib import Path

from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from pprint import pprint as pp
from options_framework.config import settings
from options_framework.option_types import OptionType, SelectFilter, FilterRange
from options_framework.spreads.vertical import Vertical
from options_framework.test_manager import OptionTestManager

with open("config\\.secrets.toml", 'rb') as f:
    db_settings = tomllib.load(f)

def get_data(database, query, index_col):
    """

    :type database: SQLAlchemy data
    """
    conn_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER='+db_settings['server']+';DATABASE='+database+';UID='+db_settings['username']+';PWD='+db_settings['password']
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": conn_string})

    engine = create_engine(connection_url)
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, index_col=index_col, parse_dates=True)

    return df

def get_price_data_query(startdate, enddate):

    price_data_query = 'SELECT ' + \
            'quote_datetime as [datetime]' + \
            ',[open]' + \
            ',[high]' + \
            ',[low]' + \
            ',[close]' + \
            ',0 as volume' + \
            ',0 as openinterest' + \
            ' FROM spx_prices' + \
            f" where quote_datetime >= CONVERT(datetime2, '{startdate}')" + \
            f" and quote_datetime <= CONVERT(datetime2, '{enddate}') " + \
            'order by quote_datetime'
    return price_data_query

def get_signals_query(startdate, enddate):
    query = 'select trade_date, sg_1_day_move from spotgamma_report ' \
            + f" where trade_date >= CONVERT(datetime2, '{startdate}')" \
            + f" and trade_date <= CONVERT(datetime2, '{enddate}') " \
            + 'order by trade_date'

    return query

"""
When price moves outside the SpotGamma expected daily move, take credit spread in the opposite direction 
for a reversion to the expected daily range
"""
class SPXSpotGammaExpectedMoveReversionCreditSpread(bt.Strategy):
    params = (
        ('start_date', None),
        ('end_date', None),
        ('test_manager', None),
        ('sg_signals', None),
        ('max_risk', 0.01),
        ('delta', None)
    )

    def log(self, txt, dt=None):
        dt = dt if dt is not None else self.dt if self.dt is not None \
            else pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        print('%s, %s' % (dt, txt))

    def __init__(self):
        self.data = self.datas[0]
        self.dt = None
        self.current_date = None
        self.one_day_move = 0
        self.sg_high = None
        self.sg_low = None
        self.highest_price = None
        self.lowest_price = None
        self.portfolio = self.p.test_manager.portfolio
        print('init complete')

    def next(self):
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        current_date = self.data.datetime.date(0)

        # Once per day
        if current_date != self.current_date:
            self.current_date = current_date

            try:
                self.one_day_move = self.p.sg_signals['sg_1_day_move'].loc[current_date]
                open_price = self.data.open[0]
                self.sg_high = open_price + (open_price * self.one_day_move)
                self.sg_low = open_price - (open_price * self.one_day_move)
                self.highest_price = 0
                self.lowest_price = 1_000_000
                self.log(f'one day move: {self.one_day_move:.4f}  high: {self.sg_high:.2f}  low: {self.sg_low:.2f}')
            except KeyError:
                print(f'missing signals for {current_date}')
                return

        # determine if today is an expiration day
        if self.current_date not in self.p.test_manager.expirations:
            return

        high_price = self.data.high[0]
        self.highest_price = high_price if high_price > self.highest_price else self.highest_price
        low_price = self.data.low[0]
        self.lowest_price = low_price if low_price < self.lowest_price else self.lowest_price
        price = self.data.close[0]

        if self.portfolio.positions:
            self.portfolio.next(self.dt.to_pydatetime())
            keys = self.portfolio.positions.keys()
            for key in list(keys):
                pos = self.portfolio.positions[key]
                close_stop = pos.user_defined['close_stop']
                if pos.get_unrealized_profit_loss() <= close_stop * -1:
                    self.portfolio.close_position(pos)
        else:
            if (((self.highest_price > self.sg_high) and (price <= self.sg_high))
                    or ((self.lowest_price < self.sg_low) and (price >= self.sg_low))):
                # only allow one trade per day
                opened_today = [p for p in self.portfolio.closed_positions.values() if p.get_open_datetime().date() == self.current_date]
                if len(opened_today) > 0:
                    return
                self.p.test_manager.get_current_option_chain(self.dt.to_pydatetime())
                chain = self.p.test_manager.option_chain.option_chain
                credit_spread = None
                if price <= self.sg_high:
                    option_candidates = [o for o in chain if
                                         o.delta <= self.p.delta and o.option_type == OptionType.CALL and o.expiration == current_date]
                    # open call credit spread to fade move outside of the daily expected range
                    short_strike = option_candidates[0].strike
                    long_strike = short_strike + 30
                    credit_spread = Vertical.get_vertical(option_chain=option_candidates, expiration=current_date,
                                           option_type=OptionType.CALL, long_strike=long_strike, short_strike=short_strike)
                    risk_amount = self.portfolio.cash * self.p.max_risk
                    if credit_spread.max_profit > 0:
                        qty = int(risk_amount / credit_spread.max_profit)
                        self.portfolio.open_position(credit_spread, quantity=qty, close_stop=qty*credit_spread.max_profit)

                if price >= self.sg_low:
                    option_candidates = [o for o in chain if
                                         o.delta >= -(self.p.delta) and o.option_type == OptionType.PUT and o.expiration == current_date][::-1]
                    short_strike = option_candidates[0].strike
                    long_strike = short_strike - 30
                    credit_spread = Vertical.get_vertical(option_chain=option_candidates, expiration=current_date,
                                          option_type=OptionType.PUT, long_strike=long_strike, short_strike=short_strike)
                    risk_amount = self.portfolio.cash * self.p.max_risk
                    if credit_spread.max_profit > 0:
                        qty = int(risk_amount / credit_spread.max_profit)
                        self.portfolio.open_position(credit_spread, quantity=qty, close_stop=qty*credit_spread.max_profit)

                if credit_spread is not None:
                    credit_spread.user_defined['one_day_move'] = self.one_day_move
                    credit_spread.user_defined['range_high'] = self.sg_high
                    credit_spread.user_defined['range_low'] = self.sg_low


    def notify_cashvalue(self, cash, value):
        if self.dt is None: return
        if self.dt.time() == datetime.time(16, 15):
            self.log(self.portfolio.cash)


if __name__ == "__main__":
    pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())
    s = sys.argv[1] if len(sys.argv) >= 3 else '09-02-2020'
    e = sys.argv[2] if len(sys.argv) >= 3 else '09-30-2020'
    startdate = datetime.datetime.strptime(s, "%m-%d-%Y")
    enddate = datetime.datetime.strptime(e, "%m-%d-%Y")
    starting_cash = 100_000.0

    print(f'Start test: start date: {startdate} end date: {enddate} starting cash: {starting_cash}')

    # Get price data and signals from sql server
    price_df = get_data(database=settings.DATABASE, query=get_price_data_query(startdate, enddate), index_col='datetime')
    data = bt.feeds.PandasData(dataname=price_df)
    signals_data = get_data(database=settings.SIGNALS_DATABASE, query=get_signals_query(startdate, enddate), index_col='trade_date')

    # Initialize options
    options_select_filter = SelectFilter(
        symbol='SPXW',
        expiration_dte=FilterRange(high=5),
        strike_offset=FilterRange(low=75, high=75))
    test_manager = OptionTestManager(start_datetime=startdate, end_datetime=enddate,
                                     select_filter=options_select_filter, starting_cash=starting_cash,
                                     extended_option_attributes=['delta', 'gamma'])

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(starting_cash)

    cerebro.addstrategy(SPXSpotGammaExpectedMoveReversionCreditSpread,
                        start_date=startdate,
                        end_date=enddate,
                        test_manager=test_manager,
                        sg_signals=signals_data,
                        delta=0.48)

    cerebro.adddata(data)
    test_results = cerebro.run()

    print(f'Ending cash: {test_manager.portfolio.cash}')
    root_folder = Path(r'C:\_data\backtesting_data\output\sg_signals')
    now = datetime.datetime.now()
    output_file = root_folder.joinpath(f'{now.year}_{now.month}_{now.day}-{now.hour}-{now.minute}.csv')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    trades = test_manager.portfolio.closed_positions

    f = open(output_file, "w")
    f.write(
        "ID,Date,Type,Open Spot Price,Close Spot Price,Open Time,Close Time,Open Price,Close Price,Max Profit,Max Loss,PNL,Range Pct,Range Hi,Range Lo\n")

    for trade_id, trade in trades.items():
        open_dt = trade.get_open_datetime()
        dt = open_dt.date()
        close_dt = trade.get_close_datetime()
        option_type = trade.option_type.name
        max_profit = trade.max_profit
        max_loss = trade.max_loss
        pnl = trade.get_profit_loss()
        trade_price = trade.get_trade_price()
        close_price = trade.price
        open_spot_price = trade.long_option.trade_open_info.spot_price
        close_spot_price = trade.long_option.trade_close_records[-1].spot_price
        open_time = datetime.datetime.strptime(str(open_dt), "%Y-%m-%d %H:%M:%S")
        close_time = datetime.datetime.strptime(str(close_dt), "%Y-%m-%d %H:%M:%S")
        expected_range = trade.user_defined['one_day_move']
        range_hi = trade.user_defined['range_high']
        range_lo = trade.user_defined['range_low']

        line = f'{trade_id},{dt},{option_type},{open_spot_price},{close_spot_price},'
        line += f'{open_time},{close_time},{trade_price},{close_price},{max_profit},{max_loss},{pnl},{expected_range},{range_hi},{range_lo},\n'
        f.write(line)

    f.close()

    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())