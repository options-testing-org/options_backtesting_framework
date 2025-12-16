"""
Open a 7-day to exp put credit spread at around 2:00 PM
any day
3-day ema > 8-day ema
spot price > 20-day ema
short strike 45 delta or less
5 wide spread
close @ 25% profit
Only 1 position open at a time
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
from options_framework.option_types import OptionType, SelectFilter, FilterRange
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

import pandas as pd
import backtrader as bt
import datetime
from options_framework.option_types import OptionType, OptionPositionType
from options_framework.spreads.vertical import Vertical

class SPX_7_Day_Put_Credit(bt.Strategy):
    params = (
        ('start_date', None),
        ('end_date', None),
        ('test_manager', None),
        ('max_risk', 0.10),
        ('sma_short', 3),
        ('sma_medium', 8),
        ('sma_long', 20),
        ('delta', 0.45),
        ('spread_width', 10),
        ('trade_dow', [2]),
        ('trade_hour', 15),
        ('trade_minute', 0),
        ('dte', 7),
        ('profit_target', 0.50),
        ('stop_loss_pct', 1.0),
        ('save_properties', []),
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
        self.sma_medium = bt.indicators.SMA(self.data1, period=self.p.sma_medium)
        self.sma_long = bt.indicators.SMA(self.data1, period=self.p.sma_long)
        self.current_date = None
        self.current_time = None
        self.day_of_week = None
        self.trade_today = None
        self.portfolio = self.p.test_manager.portfolio
        self.portfolio.bind(position_expired=self.expired)
        self.option_chain = self.p.test_manager.options
        print('init complete')

    def next(self):
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        #self.log('next')
        price = self.data.close[0]
        sma_20 = self.sma_long[0]
        sma_3 = self.sma_short[0]
        sma_8 = self.sma_medium[0]
        self.portfolio.next(self.dt, price, sma_20, sma_3, sma_8)

        # Once per day
        if self.data.datetime.date(0) != self.current_date:
            self.current_date = self.data.datetime.date(0)
            self.day_of_week = self.dt.weekday()
            positions_value = sum(p.get_profit_loss() for p in self.portfolio.positions.values())
            portfolio_value = positions_value + self.portfolio.cash
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
                # if pnl <= pos.user_defined['stop_loss']:
                #     to_close = True
                if price < pos.user_defined['close_price']:
                    to_close = True
                if to_close:
                    self.portfolio.close_position(pos)
                    self.trade_today = True
                    message = f'Closed ({pos.position_id}) credit: {pos.trade_value:.2f} closed value: {pnl:.2f} pct gain/loss: {pnl / pos.trade_value * -1:.2f}%'
                    self.log(message)

        # Only hold one position at a time
        if not self.trade_today:
            return

        # Chck time of day
        current_time = self.data.datetime.time(0)
        if current_time.hour == self.p.trade_hour and current_time.minute == self.p.trade_minute:

            # Look for trade
            if (price > sma_20) and (sma_3 > sma_8):
                expiration = self.current_date + datetime.timedelta(days=self.p.get_dte)
                self.p.test_manager.get_current_option_chain(self.dt.to_pydatetime())
                try:
                    credit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=self.option_chain,
                                                        expiration=expiration,
                                                        option_position_type=OptionPositionType.SHORT,
                                                        option_type=OptionType.PUT, delta=self.p.delta,
                                                        spread_width=self.p.spread_width)
                    risk_amount = self.portfolio.current_value * self.p.max_risk
                    if credit_spread.max_loss > 0:
                        qty = int(risk_amount / credit_spread.max_loss)
                        qty = 1 if qty == 0 else qty
                        credit_spread.update_quantity(quantity=qty)
                        close_price = credit_spread.short_option.strike - 5
                        target_pnl = credit_spread.max_profit * self.p.profit_target
                        self.portfolio.open_position(credit_spread,
                                                     quantity=qty,
                                                     target_pnl=target_pnl,
                                                     close_price=close_price,
                                                     short_delta=credit_spread.short_option.delta,
                                                     long_delta=credit_spread.long_option.delta)
                        self.log(f'Open PCS {credit_spread.short_option.strike}/{credit_spread.long_option.strike} expiring {expiration} for {credit_spread.current_value} target pnl: {target_pnl:.2f}')

                except Exception as ex:
                    self.log(ex)
                    if ex.args[0].startswith('Insufficient margin'):
                        self.trade_today = False

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
    pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())
    s = sys.argv[1] if len(sys.argv) >= 3 else '04-01-2021'
    e = sys.argv[2] if len(sys.argv) >= 3 else '06-30-2021'
    startdate = datetime.datetime.strptime(s, "%m-%d-%Y")
    enddate = datetime.datetime.strptime(e, "%m-%d-%Y")
    starting_cash = 100_000.0

    fl = Path(__file__)
    print(f'Start test {fl.name}: start date: {startdate} end date: {enddate} starting cash: {starting_cash}')

    # Set up options for testing
    options_select_filter = SelectFilter(
        option_type=OptionType.PUT,
        expiration_dte=FilterRange(low=5, high=15),
        strike_offset=FilterRange(low=100, high=100))
    test_manager = OptionTestManager(start_datetime=startdate + datetime.timedelta(days=20), end_datetime=enddate,
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
    cerebro.addstrategy(SPX_7_Day_Put_Credit,
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

    # Save trades
    trades = test_manager.portfolio.closed_positions
    trade_infos = []

    for trade_id, trade in trades.items():
        pnl = trade.get_profit_loss()
        short_strike = trade.short_option.strike
        long_strike = trade.long_option.strike
        fees = trade.get_fees()
        closed_value = trade.closed_value
        # if closed_value > trade.max_profit:
        #     closed_value = trade.max_profit
        #     pnl = trade.max_profit - fees
        #
        # if closed_value < trade.max_loss * -1:
        #     closed_value = trade.max_loss * -1
        #     pnl = (trade.max_loss * -1) - fees

        trade_info = {
            "id": trade_id,
            "trade_date": trade.get_open_datetime().date(),
            "option_type": trade.option_type.name,
            "max_profit": trade.max_profit,
            "max_loss": trade.max_loss,
            "expiration": f'{trade.expiration.month}-{trade.expiration.day}-{trade.expiration.year}',
            "quantity": trade.long_option.trade_open_info.quantity,
            "open_spot_price": trade.long_option.trade_open_info.spot_price,
            "close_spot_price": trade.long_option.trade_close_records[-1].spot_price,
            "open_dt": trade.get_open_datetime(),
            "close_dt": trade.get_close_datetime(),
            "open_price": trade.get_trade_price(),
            "close_price": trade.price,
            "short_id": trade.short_option.option_id,
            "long_id": trade.long_option.option_id,
            "short_strike": short_strike,
            "long_strike": long_strike,
            "short_delta": trade.user_defined['short_delta'],
            "long_delta": trade.user_defined['long_delta'],
            "spread_width": abs(short_strike - long_strike),
            "open_value": trade.trade_value,
            "close_value": closed_value,
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

    # Calculate trade stats
    count = len(trades)
    wins = sum(1 for t in trade_infos if t['win_loss'] == 'Win')
    losses = sum(1 for t in trade_infos if t['win_loss'] == 'Lose')
    running_portfolio_value = test_manager.portfolio.close_values
    running_value_file = output_folder.joinpath(f'{fl.stem}_running_{now.year}{now.month}{now.day}{now.hour}{now.minute}.csv')

    running_total_fields = {
        'Value': 'last',
        'Price': 'first',
        'SMA_20': 'first',
        'SMA_3': 'first',
        'SMA_8': 'first',
    }
    df_running_total = pd.DataFrame(running_portfolio_value, columns=['Date', 'Value', 'Price', 'SMA_20', 'SMA_3', 'SMA_8'])
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