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

from helpers import PandasData_CalculatedFields

def get_connection(database):
    """

    :type database: SQLAlchemy data
    """
    conn_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER='+settings.SERVER+';DATABASE='+database+';UID='+settings.USERNAME+';PWD='+settings.PASSWORD
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": conn_string})

    engine = create_engine(connection_url)

    return engine

def get_liquid_options_query(startdate: datetime.date, enddate: datetime.date):
    query = f'select stock_prices_id, quote_date, symbol, symbol_id from liquid_options ' \
            + f'where quote_date >= CONVERT(datetime2, \'{startdate}\') ' \
            + f' and quote_date <= CONVERT(datetime2, \'{enddate}\') order by quote_date, symbol'
    return query

def get_data_query(symbol_id, startdate: datetime.date, enddate: datetime.date):
    query = 'select quotedate, symbol, adjustedopen as [open], adjustedhigh as [high], ' \
            + 'adjustedlow as [low], adjustedclose as [close], volume, crsi, atr ' \
            + 'from stock_prices sp inner join symbols s on sp.symbol_id = s.id ' \
            + f'where symbol_id={symbol_id} and quotedate >= CONVERT(datetime2, \'{startdate}\') ' \
            + f' and quotedate <= CONVERT(datetime2, \'{enddate}\') order by quotedate'
    return query

def get_symbol_dfs(df, startdate: datetime.date, enddate: datetime.date):
    all_symbols = df['symbol_id'].unique()
    all_symbols.sort()
    dfs = []
    options_db_connection = get_connection(settings.database)
    for symbol_id in all_symbols:
        symbol_df = pd.read_sql(get_data_query(symbol_id, startdate, enddate), options_db_connection,
                                parse_dates='quotedate', index_col='quotedate')
        symbol_df['volume'].ffill(axis=0, inplace=True)
        symbol_df.dropna(inplace=True)
        if len(symbol_df) >= 252:
            symbol = symbol_df.iloc[0]['symbol']
            print(f'loading {symbol}')
            dfs.append(symbol_df)

    return dfs

class TradingNewHighsStrategy(bt.Strategy):
    params = (
        ('start_date', None),
        ('end_date', None),
        ('last_high_limit', 20),
        ('crsi_limit', 15),
        ('limit_low_pct', 0.05),
        ('risk_basis', 0.002),
        ('crsi_crossover', 70),
    )

    def log(self, txt, dt=None):
        dt = dt if dt is not None else self.dt if self.dt is not None \
            else pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        print('%s, %s' % (dt, txt))

    def __init__(self):
        self.dt = None
        self.stocks = self.datas
        self.stock_indicators = {}
        for data in self.stocks:
            symbol = data.p.name
            self.stock_indicators[symbol] = {
                'last_high_idx': bt.ind.FindLastIndexHighest(data.high, period=252),
                'open_trade': False,
                'limit_low': None,
            }
            print(f'init {symbol}')

        print('init complete')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        ticker = order.data.p.name

        if order.status in [order.Completed]:
            if order.isbuy():

                self.log(
                    f'{ticker},BUY: Price: {order.executed.price :.2f}, Size: {order.executed.size}, Cost: {order.executed.value :.2f}')
                self.stock_indicators[ticker]["sell_limit"] = order.executed.price * 0.9  # trailing 10% stop

                data_line = f'{datetime.datetime.strftime(self.dt, "%Y-%m-%d")},{ticker},BUY,{order.executed.price :.2f},{order.executed.size},{order.executed.price * order.executed.size :.2f}\n'

            else:
                self.log(
                    f'{ticker}, SELL: Price: {order.executed.price :.2f}, Size: {order.executed.size}, Cost: {order.executed.price * order.executed.size :.2f}')
                data_line = f'{datetime.datetime.strftime(self.dt, "%Y-%m-%d")},{ticker},SELL,{order.executed.price :.2f},{order.executed.size},{order.executed.price * order.executed.size :.2f}\n'

    # def notify_cashvalue(self, cash, value):
    #     if self.dt is not None:
    #         self.log(f'Cash:, {cash :.2f}, Value:, {value :.2f}')
    #         data_line = f'{datetime.datetime.strftime(self.dt, "%Y-%m-%d")},{cash :.2f},{value - cash :.2f},{value :.2f}\n'

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'{trade.data.p.name}, P/L: GROSS: {trade.pnl :.2f}, Portfolio Value: ${self.broker.get_value():,.2f}')
        data_line = f'{datetime.datetime.strftime(self.dt, "%Y-%m-%d")},{trade.data.p.name},{trade.pnl :.2f}\n'

    def prenext(self):
        # Execute next even if all the stocks do not have data for this time slot
        self.next()

    def next(self):
        self.dt = self.data.datetime.date(0)
        portfolio_value = self.broker.get_value()

        filtered = list(filter(lambda x: len(x) > 0, self.stocks))

        for stock in filtered:
            symbol = stock.p.name
            close = stock.close[0]
            low = stock.low[0]
            last_high = self.stock_indicators[symbol]['last_high_idx'][0]
            crsi = stock.crsi[0]
            atr = stock.atr[0]
            position = self.getposition(data=stock)

            if position.size != 0:
                if crsi >= self.p.crsi_crossover or close <= self.stock_indicators[symbol]['limit_low']:
                    self.sell(symbol, size=position.size)

            if self.stock_indicators[symbol]['open_trade']:
                if low > self.stock_indicators[symbol]['limit_low']:
                    size = math.floor(portfolio_value * self.p.risk_basis / atr)
                    self.buy(symbol, size=size)

                self.stock_indicators[symbol]['open_trade'] = False

            if last_high <= 20 and crsi <= 15:
                #self.log(f'{symbol} {last_high} {crsi}')
                self.stock_indicators[symbol]['open_trade'] = True
                self.stock_indicators[symbol]['limit_low'] = close - close * self.p.limit_low_pct


if __name__ == "__main__":
    settings.database = 'options_db'
    settings.data_format_settings = 'daily_options_db_settings.toml'
    settings.incur_fees = True
    pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())
    s = sys.argv[1] if len(sys.argv) >= 3 else '01-01-2018'
    e = sys.argv[2] if len(sys.argv) >= 3 else '12-31-2019'
    startdate = datetime.datetime.strptime(s, "%m-%d-%Y")
    enddate = datetime.datetime.strptime(e, "%m-%d-%Y")
    starting_cash = 100_000.0

    fl = Path(__file__)
    print(f'Start test {fl.name}: start date: {startdate} end date: {enddate} starting cash: {starting_cash}')

    cnx = get_connection('signals_db')

    liquid_df = pd.read_sql(get_liquid_options_query(startdate, enddate), cnx, parse_dates='quote_date', index_col=['quote_date'])
    data_dfs = get_symbol_dfs(liquid_df, startdate, enddate)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(starting_cash)
    cerebro.addstrategy(TradingNewHighsStrategy, start_date=startdate, end_date=enddate)

    for data in data_dfs:
        symbol = data.iloc[0]['symbol']
        bt_data = PandasData_CalculatedFields(dataname=data, name=symbol)
        cerebro.adddata(bt_data)

    print('data retrived')
    cerebro.run()

    print(f'Ending value: ${cerebro.broker.get_value():,.2f}')

    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())