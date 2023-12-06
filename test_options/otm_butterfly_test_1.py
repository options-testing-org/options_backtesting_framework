import datetime
import sqlalchemy as sa
import backtrader as bt
import pandas as pd
from numpy import isnan

from options_framework.option_types import OptionType


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


class OTMButterfly(bt.Strategy):
    params = (
        ('startdate', None),
        ('enddate', None),
        ('opening', datetime.time(9, 30)),
        ('mid_day', datetime.time(12, 00)),
        ('afternoon', datetime.time(14, 0)),
        ('closing', datetime.time(15, 50)),
        ('eod', datetime.time(16, 15)),
        ('hull_period', 14),
        ('options_manager', None),)

    def log(self, txt, dt=None):
        """ Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt, txt))

    def __init__(self):
        self.hull = bt.indicators.HullMA(self.data1, period=self.p.hull_period)
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        self.portfolio = self.p.options_manager.portfolio
        self.option_chain = self.p.options_manager.option_chain

        def next(self):
            self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
            hull_ma_two_days_ago = self.hull[-2]
            hull_ma_one_day_ago = self.hull[-1]
            if isnan(hull_ma_two_days_ago):
                return
            self.p.options_manager.next(self.dt.to_pydatetime())
            option_type = OptionType.CALL if hull_ma_two_days_ago < hull_ma_one_day_ago else OptionType.PUT

            t = self.data.datetime.time(0)
            current_position = None if not self.portfolio.positions else self.portfolio.positions[
                next(iter(self.portfolio.positions))]

            tod = 'before open'
            if self.p.opening <= t < self.p.mid_day:
                tod = 'morning'
            elif self.p.mid_day < t < self.p.afternoon:
                tod = 'mid-day'
            elif self.p.afternoon < t < self.p.closing:
                tod = 'afternoon'
            elif t == self.p.closing:
                tod = 'closing'
            elif t == self.p.eod:
                tod = 'eod'

            if t == self.p.opening:
                self.log(tod, self.dt)
            if t == self.p.closing:
                self.log(tod, self.dt)

            if tod == 'eod':
                self.log(
                    f'portfolio value: {self.portfolio.portfolio_value:.2f}  cash: {self.portfolio.cash:.2f}',
                    self.dt)
