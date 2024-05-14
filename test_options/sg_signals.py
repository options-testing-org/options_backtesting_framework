import datetime
import math
import sys
import time
import tomllib

import backtrader as bt
import pandas as pd
from pathlib import Path

import pyodbc
from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.sql import text
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

# def get_pyodbc_connection(database):
#     connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + db_settings['server'] + ';DATABASE=' + \
#                         database + ';UID=' + db_settings['username'] + ';PWD=' + db_settings[
#                             'password']
#     cnxn = pyodbc.connect(connection_string)
#     return cnxn

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
                self.log(f'one day move: {self.one_day_move:.4f}  high: {self.sg_high:.2f}  low: {self.sg_low:.2f}')
            except KeyError:
                print(f'missing signals for {current_date}')
                return

        #self.log('next')

    def notify_cashvalue(self, cash, value):
        if self.dt is None: return
        if self.dt.time() == datetime.time(16, 15):
            self.log(cash)


if __name__ == "__main__":
    t1 = time.time()
    print(time.ctime())
    startdate = datetime.datetime.strptime(sys.argv[1], "%m-%d-%Y")
    enddate = datetime.datetime.strptime(sys.argv[2], "%m-%d-%Y")
    starting_cash = 100_000.0

    # Get price data and signals from sql server
    price_df = get_data(database=db_settings['spx_database'], query=get_price_data_query(startdate, enddate), index_col='datetime')
    data = bt.feeds.PandasData(dataname=price_df)
    signals_data = get_data(database=db_settings['signals_database'], query=get_signals_query(startdate, enddate), index_col='trade_date')

    # Initialize options
    filter = SelectFilter(
        symbol='SPXW',
        expiration_dte=FilterRange(high=5),
        strike_offset=FilterRange(low=120, high=120))
    test_manager = OptionTestManager(start_datetime=startdate, end_datetime=enddate, select_filter=filter, starting_cash=starting_cash)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(starting_cash)

    cerebro.addstrategy(SPXSpotGammaExpectedMoveReversionCreditSpread,
                        start_date=startdate,
                        end_date=enddate,
                        test_manager=test_manager,
                        sg_signals=signals_data)

    cerebro.adddata(data)
    test_results = cerebro.run()

    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())