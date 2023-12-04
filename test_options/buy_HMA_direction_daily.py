import datetime
import warnings
from pprint import pprint as pp

import backtrader as bt
import pandas as pd
import pyodbc
import sqlalchemy as sa
from numpy import isnan

from options_framework.option_types import OptionType
from options_framework.test_manager import OptionTestManager
from options_framework.option_types import OptionType, SelectFilter, FilterRange

warnings.filterwarnings('ignore')

from options_framework.config import settings


def get_connection():
    eng = sa.create_engine("mssql+pyodbc://sa:msdevshow@MYTOWER/options_db?driver=ODBC+Driver+17+for+SQL+Server")
    cnx = eng.connect()
    return cnx


def get_price_data_query(startdate, enddate):
    price_data_query = 'SELECT ' + \
                       'quote_datetime as [datetime]' + \
                       ',[open]' + \
                       ',[high]' + \
                       ',[low]' + \
                       ',[close]' + \
                       ',volume' + \
                       ',0 as openinterest' + \
                       ' FROM spx_prices' + \
                       " where symbol='^SPX'" + \
                       f" and quote_datetime >= CONVERT(datetime2, '{startdate}')" + \
                       f" and quote_datetime < CONVERT(datetime2, '{enddate}') " + \
                       'order by quote_datetime'
    return price_data_query

class HullMADirectionalStrategy(bt.Strategy):
    params = (
        ('startdate', None),
        ('enddate', None),
        ('morning', datetime.time(9, 30)),
        ('mid_day', datetime.time(12, 00)),
        ('afternoon', datetime.time(14, 0)),
        ('hull_period', 14),
        ('option_test_manager', None),
    )

    def log(self, txt, dt=None):
        """ Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt, txt))

    def __init__(self):
        self.hull = bt.indicators.HullMA(self.data1, period=self.p.hull_period)
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')

    def next(self):
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        hull_ma_two_days_ago = self.hull[-2]
        hull_ma_one_day_ago = self.hull[-1]
        if isnan(hull_ma_two_days_ago):
            return

        direction = "up" if hull_ma_two_days_ago < hull_ma_one_day_ago else "down"

        t = self.data.datetime.time(0)

        if t < self.p.mid_day:
            tod = 'morning'
        elif t < self.p.afternoon:
            tod = 'mid day'
        else:
            tod = 'afternoon'

if __name__ == "__main__":
    pp(settings.as_dict())

    server = settings.SERVER
    database = settings.DATABASE
    username = settings.USERNAME
    password = settings.PASSWORD
    ticker = 'SPXW'
    startdate = datetime.datetime(2016, 3, 1)
    enddate = datetime.datetime(2016, 3, 31)
    starting_cash = 100_000.0

    connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database \
                        + ';UID=' + username + ';PWD=' + password
    connection = pyodbc.connect(connection_string)

    query = get_price_data_query(startdate, enddate)
    df = pd.read_sql(query, connection, index_col='datetime', parse_dates=True)
    connection.close()

    options_filter = SelectFilter(symbol='SPXW', option_type=OptionType.CALL, strike_range=FilterRange(2000, 4000))

    option_test_manager = OptionTestManager(start_datetime=startdate, end_datetime=enddate,
                                            select_filter=options_filter, starting_cash=starting_cash)

    ohlc = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'openinterest': 'first',
    }
    df_daily = df.resample('D').apply(ohlc)
    df_daily.dropna(inplace=True) # get daily timeframe for hull ma

    data = bt.feeds.PandasData(dataname=df, name='SPX')
    daily_data = bt.feeds.PandasData(dataname=df_daily, name='SPX')




    cerebro = bt.Cerebro()
    cerebro.addstrategy(HullMADirectionalStrategy, startdate=startdate, enddate=enddate)

    cerebro.adddata(data)
    cerebro.adddata(daily_data)
    cerebro.run()