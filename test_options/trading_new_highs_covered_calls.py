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
from options_framework.test_manager import OptionTestManager
from options_framework.spreads.single import Single

class PandasData_CalculatedFields(bt.feeds.PandasData):

    lines = ('open', 'high', 'low', 'close', 'volume', 'crsi', 'atr', 'days_since_high')
    params = (('open', -1), ('high', -1), ('low', -1), ('close', -1), ('volume', -1), ('crsi', -1), ('atr', -1),
              ('days_since_high', -1))

    datafields = bt.feeds.PandasData.datafields + (['open', 'high', 'low', 'close', 'volume', 'crsi', 'atr',
                                                    'days_since_high'])
def roundup_100(x):
    return int(math.ceil(x / 100.0)) * 100


def rounddown_100(x):
    return int(math.floor(x / 100.0)) * 100

data_format_file = 'daily_options_db_settings.toml'


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
    query = 'select quote_date, symbol, adjustedopen as [open], adjustedhigh as [high], ' \
            + 'adjustedlow as [low], adjustedclose as [close], volume, crsi, atr, ' \
            + 'days_since_52_wk_high as days_since_high ' \
            + 'from stock_prices sp inner join symbols s on sp.symbol_id = s.id ' \
            + f'where symbol_id={symbol_id} and quote_date >= CONVERT(datetime2, \'{startdate}\') ' \
            + f' and quote_date <= CONVERT(datetime2, \'{enddate}\') order by quote_date'
    return query

def get_symbol_dfs(df, startdate: datetime.date, enddate: datetime.date):
    all_symbols = df['symbol_id'].unique()
    all_symbols.sort()
    dfs = []
    options_db_connection = get_connection(settings.database)
    #syms = [86, 710, 945, 1137, 1993, 6519, 6560, 7016, 7637, 7704, 7772, 8203, 8532, 8567]
    for symbol_id in all_symbols:
        symbol_df = pd.read_sql(get_data_query(symbol_id, startdate, enddate), options_db_connection,
                                parse_dates='quote_date', index_col='quote_date')
        symbol_df['volume'].ffill(axis=0, inplace=True)
        symbol_df.dropna(inplace=True)
        #print(f'loading {symbol_df.iloc[0]['symbol']}')
        if len(symbol_df) > 0:
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
        ('options_manager', None)
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
                'open_trade': False,
                'open_order': None,
                'limit_low': None,
                'target_profit': None,
                'option_expired': False,
            }
            print(f'init {symbol}')
        self.portfolio = self.p.options_manager.portfolio
        self.portfolio.bind(position_expired=self.expired)
        print('init complete')

    def notify_order(self, order):
        ticker = order.daily_option_data.p.name
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        if order.status in [order.Completed]:
            if order.isbuy():

                self.log(
                    f'{ticker},BUY: Price: {order.executed.price :.2f}, Size: {order.executed.size}, Cost: {order.executed.value :.2f}')
                #self.stock_indicators[ticker]["sell_limit"] = order.executed.price * 0.9  # trailing 10% stop

                data_line = f'{datetime.datetime.strftime(self.dt, "%Y-%m-%d")},{ticker},BUY,{order.executed.price :.2f},{order.executed.size},{order.executed.price * order.executed.size :.2f}\n'

            else:
                self.log(
                    f'{ticker}, SELL: Price: {order.executed.price :.2f}, Size: {order.executed.size}, Cost: {order.executed.price * order.executed.size :.2f}')
                data_line = f'{datetime.datetime.strftime(self.dt, "%Y-%m-%d")},{ticker},SELL,{order.executed.price :.2f},{order.executed.size},{order.executed.price * order.executed.size :.2f}\n'

    def notify_cashvalue(self, cash, value):
        if self.dt is not None:
            self.log(f'Cash:, {cash :.2f}, Value:, {value :.2f}')
            data_line = f'{datetime.datetime.strftime(self.dt, "%Y-%m-%d")},{cash :.2f},{value - cash :.2f},{value :.2f}\n'

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'{trade.daily_option_data.p.name}, P/L: GROSS: {trade.pnl :.2f}, Portfolio Value: ${self.broker.get_value():,.2f}')
        data_line = f'{datetime.datetime.strftime(self.dt, "%Y-%m-%d")},{trade.daily_option_data.p.name},{trade.pnl :.2f}\n'

    def expired(self, position):
        symbol = position.symbol
        self.stock_indicators[symbol]['option_expired'] = True
        option_pnl = position.get_profit_loss()
        self.broker.add_cash(position.closed_value)
        d = self.getdatabyname(symbol)
        self.log(f'expired option {symbol} Option PNL: {option_pnl:.2f}, Underlying Price {d.close[0]}')

    def prenext(self):
        # Execute next even if all the stocks do not have data for this time slot
        self.next()

    def next(self):
        self.dt = self.data.datetime.date(0)
        self.portfolio.next(self.dt)
        portfolio_value = self.broker.get_value()
        cash = self.broker.cash
        filtered = list(filter(lambda x: len(x) > 0, self.stocks))

        for stock in filtered:
            symbol = stock.p.name
            close = stock.close[0]
            low = stock.low[0]
            last_high = stock.days_since_high[0]
            crsi = stock.crsi[0]
            atr = stock.atr[0]
            position = self.getposition(data=stock)

            if position.size != 0:
                order = self.stock_indicators[symbol]['open_order']
                if self.stock_indicators[symbol]['option_expired']:
                    self.sell(symbol, size=position.size)
                else:
                    stock_pnl = (close - order.executed.price) * position.size
                    option = [o for i, o in self.portfolio.positions.items() if o.symbol == symbol][0]
                    option_pnl = option.get_unrealized_profit_loss()
                    pos_pnl = stock_pnl + option_pnl

                    #self.log(f'target pnl: {target:.2f}, current pnl: {pos_pnl:.2f} buy price {order.executed.price:.2f} current price: {close:.2f}')
                    if close <= self.stock_indicators[symbol]['limit_low'] or pos_pnl >= self.stock_indicators[symbol]['target_profit']:
                        self.sell(symbol, size=position.size)
                        for k in list(self.portfolio.positions.keys()):
                            pos = self.portfolio.positions[k]
                            if pos.symbol == symbol:
                                self.portfolio.close_position(pos)
                                self.broker.add_cash(pos.closed_value)
                                self.log(f'closed option {symbol} - P/L {pos.get_profit_loss():.2f}')

            else:
                if self.stock_indicators[symbol]['open_trade']:
                    option = None
                    size = roundup_100(math.floor(portfolio_value * self.p.risk_basis / atr))
                    if low > self.stock_indicators[symbol]['limit_low']:
                        # Find call option with price > close and price 2% or higher than stock price
                        option_chain = self.p.options_manager.get_option_chain(symbol=symbol, quote_datetime=self.dt)
                        target_option_price = close * 0.02
                        for exp in option_chain.expirations:
                            if option is not None:
                                break
                            strikes = option_chain.expiration_strikes.get(exp)
                            if strikes:
                                select_strikes = [s for s in strikes if s > close]
                                if len(select_strikes) > 3:
                                    select_strikes = select_strikes[3:]
                                for strike in select_strikes:
                                    try:
                                        option = Single.get_single(option_chain=option_chain, expiration=exp,
                                                                   option_type=OptionType.CALL,
                                                                   option_position_type=OptionPositionType.SHORT,
                                                                   strike=strike)
                                        if option.option.bid >= target_option_price:
                                            quantity = size / 100
                                            # check if there is enough cash to buy underlying stock
                                            cost = close*size
                                            if cash - cost < 0:
                                                option = None
                                                break
                                            self.portfolio.open_position(option, quantity)
                                            self.broker.add_cash(option.current_value*-1) # selling the option, so money is received
                                            self.stock_indicators[symbol]['option_expired'] = False
                                            self.log(f'opened {option}, added {option.current_value*-1} to cash')
                                            break
                                        else:
                                            option = None
                                    except Exception as e:
                                        if not isinstance(e, KeyError):
                                            self.log(e)
                                        option = None

                        if option:
                            order = self.buy(symbol, size=size)
                            cash -= close*size
                            price = option.get_trade_price() # price of option
                            diff = option.strike - close
                            max_profit = (price + diff) * size
                            profit_target = max_profit * 0.8
                            self.stock_indicators[symbol]['open_order'] = order
                            self.stock_indicators[symbol]['target_profit'] = profit_target
                    self.stock_indicators[symbol]['open_trade'] = False

                elif last_high <= 20 and crsi <= 15:
                    #self.log(f'{symbol} {last_high} {crsi}')
                    self.stock_indicators[symbol]['open_trade'] = True
                    self.stock_indicators[symbol]['limit_low'] = close - close * self.p.limit_low_pct


if __name__ == "__main__":
    settings.database = 'options_db'
    settings.data_format_settings = data_format_file
    settings.incur_fees = True
    pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())
    s = sys.argv[1] if len(sys.argv) >= 3 else '01-01-2021'
    e = sys.argv[2] if len(sys.argv) >= 3 else '02-28-2021'
    startdate = datetime.datetime.strptime(s, "%m-%d-%Y")
    enddate = datetime.datetime.strptime(e, "%m-%d-%Y")
    starting_cash = 100_000.0

    fl = Path(__file__)
    print(f'Start test {fl.name}: start date: {startdate} end date: {enddate} starting cash: {starting_cash}')

    cnx = get_connection('signals_db')

    liquid_df = pd.read_sql(get_liquid_options_query(startdate, enddate), cnx, parse_dates='quote_date', index_col=['quote_date'])
    data_dfs = get_symbol_dfs(liquid_df, startdate, enddate)
    options_select_filter = SelectFilter(
        option_type=OptionType.CALL,
        expiration_dte=FilterRange(low=10, high=75),
        strike_offset=FilterRange(low=100, high=100))
    options_test_manager = OptionTestManager(start_datetime=startdate, end_datetime=enddate, select_filter=options_select_filter,
                                     starting_cash=starting_cash)

    cerebro = bt.Cerebro()
    cerebro.broker.set_coc = True
    cerebro.broker.setcash(starting_cash)
    cerebro.addstrategy(TradingNewHighsStrategy,
                        start_date=startdate,
                        end_date=enddate,
                        options_manager=options_test_manager)

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