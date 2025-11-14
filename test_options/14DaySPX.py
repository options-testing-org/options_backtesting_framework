"""
Open a 14-day to exp put credit spread at around 2:00 PM
on Monday, Wednesday, and Friday
5-day sma > 10-day sma
short strike 50 delta or less
5 wide spread
close @ 30% profit

"""

import datetime
import math
import sys
import time

import backtrader as bt
import pandas as pd
from pathlib import Path

from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from pprint import pprint as pp
from options_framework.config import settings
from options_framework.option_types import OptionType, SelectFilter, FilterRange, OptionPositionType
from options_framework.spreads.vertical import Vertical
from options_framework.test_manager import OptionTestManager

settings.standard_fee = 1.03
settings.incur_fees = True

def get_data(database, query, index_col):
    """

    :type database: SQLAlchemy data
    """
    conn_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER='+settings.SERVER+';DATABASE='+database+';UID='+settings.USERNAME+';PWD='+settings.PASSWORD
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": conn_string})

    engine = create_engine(connection_url)
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, index_col=index_col, parse_dates=index_col)

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

class SPX14DayPutCredit(bt.Strategy):
    params = (
        ('start_date', None),
        ('end_date', None),
        ('test_manager', None),
        ('max_risk', 0.05),
        ('sma_short', 5),
        ('sma_long', 10),
        ('delta', 0.50),
        ('spread_width', 5),
        ('profit_target', 0.30),
        ('trade_dow', [0,2,4])
    )

    def log(self, txt, dt=None):
        dt = dt if dt is not None else self.dt if self.dt is not None \
            else pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        print('%s, %s' % (dt, txt))

    def expired(self, position):
        pnl = position.get_profit_loss()
        trade_val = position.trade_value
        message = f'expired ({position.position_id}) opened value: {trade_val:.2f} expired value: {pnl:.2f} pct gain/loss: {pnl/trade_val*-1:.2f}%'
        self.log(message)

    def __init__(self):
        self.data = self.datas[0]
        self.dt = None
        self.sma_short = bt.indicators.SMA(self.data1, period=self.p.sma_short)
        self.sma_long = bt.indicators.SMA(self.data1, period=self.p.sma_long)
        self.current_date = None
        self.current_time = None
        self.day_of_week = None
        self.trade_today = None
        self.portfolio = self.p.test_manager.portfolio
        self.portfolio.bind(position_expired=self.expired)
        self.option_chain = self.p.test_manager.option_chain
        print('init complete')

    def next(self):
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        self.portfolio.next(self.dt)
        price = self.data.close[0]
        #self.log('next')

        # Once per day
        if self.data.datetime.date(0) != self.current_date:
            self.current_date = self.data.datetime.date(0)
            self.day_of_week = self.dt.weekday()
            positions_value = sum(p.get_profit_loss() for p in self.portfolio.positions.values())
            portfolio_value = positions_value + self.portfolio.cash
            if len(self.portfolio.positions) > 0:
                self.trade_today = False
            else:
                self.trade_today = True
            self.log(f'{portfolio_value:.2f}')

        # Check profit/loss of open contracts
        if len(self.portfolio.positions) > 0:
            positions = list(self.portfolio.positions.values())
            for pos in positions:
                pnl = pos.get_unrealized_profit_loss()
                to_close = False
                if pnl >= pos.user_defined['target_pnl']:
                    to_close = True
                if price < pos.short_option.strike:
                    to_close = True
                if to_close:
                    self.portfolio.close_position(pos)
                    self.trade_today = True

        # Check day of week
        # if self.day_of_week not in self.p.trade_dow:
        #     return

        if not self.trade_today:
            return

        # Check time of day
        current_time = self.data.datetime.time(0)
        if current_time.hour == 14 and current_time.minute == 0:

            # Look for trade
            if self.sma_short[0] < self.sma_long[0]:
                return

            self.p.test_manager.get_current_option_chain(self.dt.to_pydatetime())

            target_expiration = self.current_date + datetime.timedelta(days=14)

            credit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=self.option_chain,
                                                                            expiration=target_expiration,
                                                                            option_position_type=OptionPositionType.SHORT,
                                                                            option_type=OptionType.PUT,
                                                                            delta=self.p.delta,
                                                                            spread_width=self.p.spread_width)
            risk_amount = self.portfolio.portfolio_value * self.p.max_risk
            if credit_spread.max_loss > 0:
                qty = int(risk_amount / credit_spread.max_loss)
                qty = 1 if qty == 0 else qty
                credit_spread.update_quantity(qty)
                self.portfolio.open_position(credit_spread, quantity=qty)
                target_pnl = credit_spread.max_profit * self.p.profit_target
                credit_spread.user_defined['target_pnl'] = target_pnl
                self.log(f'Open PCS {credit_spread.short_option.strike}/{credit_spread.long_option.strike} expiring {target_expiration} for {credit_spread.current_value} target pnl: {target_pnl:.2f}')

    def stop(self):
        if len(self.portfolio.positions) == 0:
            return
        positions = list(self.portfolio.positions.values())
        for p in positions:
            self.portfolio.close_position(p)
        self.log(f'ending cash: {self.portfolio.cash:.2f}')


if __name__ == "__main__":
    settings.incur_fees = True
    settings.standard_fee = 1.03
    #pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())
    s = sys.argv[1] if len(sys.argv) >= 3 else '03-01-2016'
    e = sys.argv[2] if len(sys.argv) >= 3 else '04-30-2016'
    startdate = datetime.datetime.strptime(s, "%m-%d-%Y")
    enddate = datetime.datetime.strptime(e, "%m-%d-%Y")
    starting_cash = 100_000.0

    print(f'Start test {Path(__file__).name}: start date: {startdate} end date: {enddate} starting cash: {starting_cash}')

    # Set up options for testing
    options_select_filter = SelectFilter(
        symbol='SPXW',
        option_type=OptionType.PUT,
        expiration_dte=FilterRange(low=10, high=20),
        strike_offset=FilterRange(low=200, high=200))
    test_manager = OptionTestManager(start_datetime=startdate + datetime.timedelta(days=10), end_datetime=enddate,
                                     select_filter=options_select_filter, starting_cash=starting_cash,
                                     extended_option_attributes=['delta'])
    # Get price data and signals from sql server
    price_df = get_data(database=settings.DATABASE, query=get_price_data_query(startdate, enddate), index_col='datetime')
    data = bt.feeds.PandasData(dataname=price_df, name='SPX')

    ohlc = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'openinterest': 'first',
    }
    df_daily = price_df.resample('D').apply(ohlc)
    df_daily.dropna(inplace=True) # get daily timeframe for moving average

    daily_data = bt.feeds.PandasData(dataname=df_daily, name='SPX')

    cerebro = bt.Cerebro()
    cerebro.addstrategy(SPX14DayPutCredit,
                        start_date=startdate,
                        end_date=enddate,
                        test_manager=test_manager)

    cerebro.adddata(data)
    cerebro.adddata(daily_data)
    results = cerebro.run()

    print(f'Ending cash: {test_manager.portfolio.cash}')
    root_folder = Path(r'C:\_data\backtesting_data\output')
    root_folder = root_folder.joinpath(Path(__file__).stem)
    now = datetime.datetime.now()
    output_file = root_folder.joinpath(f'{now.year}_{now.month}_{now.day}-{now.hour}-{now.minute}.csv')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    trades = test_manager.portfolio.closed_positions

    f = open(output_file, "w")
    f.write(
        "ID,Date,Type,Expiration,Quantity,Open Spot Price,Close Spot Price,Open Time,Close Time,Open Price,Close Price,Short Strike,SS Price,Long Strike,LS Price,Width,Trade Val,Close Val,Max Profit,Max Loss,PNL,Fees,W/L\n")

    for trade_id, trade in trades.items():
        open_dt = trade.get_open_datetime()
        expiration = f'{trade.expiration.month}-{trade.expiration.day}-{trade.expiration.year}'
        dt = open_dt.date()
        close_dt = trade.get_close_datetime()
        option_type = trade.option_type.name
        max_profit = trade.max_profit
        max_loss = trade.max_loss
        qty = trade.long_option.trade_open_info.quantity
        pnl = trade.get_profit_loss()
        fees = trade.get_fees()
        win_loss = 'Win' if pnl > 0 else 'Lose'
        trade_price = trade.get_trade_price()
        close_price = trade.price
        short_strike = trade.short_option.strike
        ss_price = trade.short_option.trade_price
        long_strike = trade.long_option.strike
        ls_price = trade.long_option.trade_price
        spread_width = abs(short_strike - long_strike)
        trade_value = trade.trade_value
        close_value = sum(o.get_profit_loss() for o in trade.options)
        open_spot_price = trade.long_option.trade_open_info.spot_price
        close_spot_price = trade.long_option.trade_close_records[-1].spot_price
        open_time = datetime.datetime.strptime(str(open_dt), "%Y-%m-%d %H:%M:%S")
        close_time = datetime.datetime.strptime(str(close_dt), "%Y-%m-%d %H:%M:%S")

        line = f'{trade_id},{dt},{option_type},{expiration},{qty},{open_spot_price},{close_spot_price},'
        line += f'{open_time},{close_time},{trade_price},{close_price},{short_strike},{ss_price},{long_strike},{ls_price},'
        line += f'{spread_width},{trade_value:.2f},{close_value:2f},{max_profit},{max_loss},{pnl},{fees},{win_loss}\n'
        f.write(line)

    f.close()

    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())