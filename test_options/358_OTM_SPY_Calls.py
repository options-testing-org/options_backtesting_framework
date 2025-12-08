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
import csv

import backtrader as bt
import pandas as pd
from pathlib import Path

from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from pprint import pprint as pp
from options_framework.config import settings
from options_framework.option_types import OptionType, SelectFilter, FilterRange, OptionPositionType
from options_framework.spreads.single import Single
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

class SPX_358_OTM_Calls(bt.Strategy):
    params = (
        ('start_date', None),
        ('end_date', None),
        ('test_manager', None),
        ('max_risk', 0.05),
        ('ema_short', 3),
        ('ema_medium', 5),
        ('ema_long', 8),
        ('delta', 0.40),
        ('profit_target', 0.50),
        ('max_days_in_trade', 14),
        ('target_dte', 30),
    )

    def log(self, txt, dt=None):
        dt = dt if dt is not None else self.dt if self.dt is not None \
            else pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        print('%s, %s' % (dt, txt))

    def __init__(self):
        self.data = self.datas[0]
        self.dt = None
        self.ema_short = bt.indicators.EMA(self.data1, period=self.p.ema_short)
        self.ema_medium = bt.indicators.EMA(self.data1, period=self.p.ema_medium)
        self.ema_long = bt.indicators.EMA(self.data1, period=self.p.ema_long)
        self.current_date = None
        self.trade_today = None
        self.portfolio = self.p.test_manager.portfolio
        self.option_chain = self.p.test_manager.options
        print('init complete')

    def next(self):
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        self.portfolio.next(self.dt)
        # self.log('next')

        # Once per day
        if self.data.datetime.date(0) != self.current_date:
            self.current_date = self.data.datetime.date(0)
            self.log(f'{self.portfolio.current_value:.2f}')
            if len(self.portfolio.positions) > 0:
                self.trade_today = False
            else:
                self.trade_today = True

        # Check profit/loss of open contracts
        # don't open new positions if already in a position
        if len(self.portfolio.positions) > 0:
            positions = list(self.portfolio.positions.values())
            to_close = False
            for pos in positions:
                pnl = pos.get_unrealized_profit_loss()
                reason = ""
                if pnl >= pos.user_defined['target_pnl']:
                    to_close = True
                    reason = "profit"
                if self.current_date == pos.user_defined['max_date']:
                    to_close = True
                    reason = "past max date"
                if to_close:
                    self.portfolio.close_position(pos)
                    self.trade_today = True
                    message = f'Closed ({pos.position_id}) credit: {pos.trade_value:.2f} expired value: {pnl:.2f} pct gain/loss: {pnl / pos.trade_value * -1:.2f}% reason: {reason}'
                    self.log(message)

        if len(self.portfolio.positions) > 0 or not self.trade_today:
            return

        # Look for trade
        short_ema = self.ema_short[0]
        medium_ema = self.ema_medium[0]
        long_ema = self.ema_long[0]
        if short_ema > medium_ema > long_ema:
            price = self.data.close[0]
            self.p.test_manager.get_current_option_chain(self.dt.to_pydatetime())
            target_expiration = self.current_date + datetime.timedelta(days=self.p.target_dte)
            try:
                call_option = Single.get_single_by_delta(option_chain=self.option_chain, expiration=target_expiration,
                                                         option_position_type=OptionPositionType.LONG,
                                                         option_type=OptionType.CALL, delta=self.p.delta)

                risk_amount = self.portfolio.current_value * self.p.max_risk
                qty = int(risk_amount / (price * 100))
                qty = 1 if qty == 0 else qty
                target_pnl = call_option.trade_value * self.p.profit_target
                max_date = self.current_date + datetime.timedelta(days=self.p.max_days_in_trade)

                self.portfolio.open_position(call_option, quantity=qty, target_pnl=target_pnl, max_date=max_date)

                self.log(
                    f'Open Call Option {call_option.strike} expiring {target_expiration} for {call_option.current_value} target pnl: {target_pnl:.2f}')
            except Exception as e:
                self.log(e)

    def stop(self):
        if len(self.portfolio.positions) == 0:
            return
        positions = list(self.portfolio.positions.values())
        for p in positions:
            self.portfolio.close_position(p)
        self.log(f'ending cash: {self.portfolio.cash:.2f}')


if __name__ == "__main__":
    settings.database = 'spx_options_data_5'
    settings.incur_fees = True
    settings.standard_fee = 1.03
    pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())
    s = sys.argv[1] if len(sys.argv) >= 3 else '03-01-2016'
    e = sys.argv[2] if len(sys.argv) >= 3 else '04-30-2016'
    startdate = datetime.datetime.strptime(s, "%m-%d-%Y")
    enddate = datetime.datetime.strptime(e, "%m-%d-%Y")
    starting_cash = 100_000.0

    fl = Path(__file__)
    print(f'Start test {fl.name}: start date: {startdate} end date: {enddate} starting cash: {starting_cash}')

    # Get price data
    price_df = get_data(database=settings.DATABASE, query=get_price_data_query(startdate, enddate), index_col='datetime')
    data = bt.feeds.PandasData(dataname=price_df, name='SPX')

    # Set up options for testing
    options_select_filter = SelectFilter(
        symbol='SPXW',
        option_type=OptionType.CALL,
        expiration_dte=FilterRange(low=25, high=45),
        strike_offset=FilterRange(low=200, high=200))
    test_manager = OptionTestManager(start_datetime=startdate, end_datetime=enddate,
                                     select_filter=options_select_filter, starting_cash=starting_cash,
                                     extended_option_attributes=['delta'])

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
    cerebro.addstrategy(SPX_358_OTM_Calls,
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
    output_folder = root_folder.joinpath(f'{now.year}_{now.month}_{now.day}__{now.hour}-{now.minute}')
    output_folder.mkdir(parents=True, exist_ok=True)
    output_file = output_folder.joinpath(f'{fl.stem}_{now.year}{now.month}{now.day}{now.hour}{now.minute}.csv')

    close_values = test_manager.portfolio.close_values

    trades = test_manager.portfolio.closed_positions
    trade_infos = []

    for trade_id, trade in trades.items():
        pnl = trade.get_profit_loss()
        strike = trade.option.strike

        fees = trade.get_fees()
        close_value = sum(o.get_profit_loss() for o in trade.options)

        trade_info = {
            "id": trade_id,
            "trade_date": trade.get_open_datetime().date(),
            "option_type": trade.option_type.name,
            "expiration": f'{trade.expiration.month}-{trade.expiration.day}-{trade.expiration.year}',
            "quantity": trade.option.trade_open_info.quantity,
            "open_spot_price": trade.option.trade_open_info.spot_price,
            "close_spot_price": trade.option.trade_close_records[-1].spot_price,
            "open_dt": trade.get_open_datetime(),
            "close_dt": trade.get_close_datetime(),
            "open_price": trade.get_trade_price(),
            "close_price": trade.price,
            "option_id": trade.option.option_id,
            "strike": strike,
            "delta": trade.option.delta,
            "open_value": trade.trade_value,
            "close_value": close_value,
            "fees": fees,
            "pnl": pnl,
            "win_loss": 'Win' if pnl > 0 else 'Lose'
        }

        trade_infos.append(trade_info)

    field_names = list(trade_info.keys())
    with open(output_file, 'w', newline='') as f:
        data_writer = csv.DictWriter(f, fieldnames=field_names)
        data_writer.writeheader()
        data_writer.writerows(trade_infos)

    count = len(trades)
    wins = sum(1 for t in trade_infos if t['win_loss'] == 'Win')
    losses = sum(1 for t in trade_infos if t['win_loss'] == 'Lose')
    running_portfolio_value = test_manager.portfolio.close_values
    running_value_file = output_folder.joinpath(
        f'{fl.stem}_running_{now.year}{now.month}{now.day}{now.hour}{now.minute}.csv')

    running_total_fields = {
        'Value': 'last'
    }
    df_running_total = pd.DataFrame(running_portfolio_value,
                                    columns=['Date', 'Value'])
    df_running_total['Date'] = pd.to_datetime(df_running_total['Date'])
    df_running_total.set_index(['Date'], inplace=True)
    rt = df_running_total.resample('D').apply(running_total_fields)
    rt.dropna(inplace=True)
    rt.to_csv(running_value_file.absolute())

    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())