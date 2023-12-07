import datetime
import math
import time
import warnings

import backtrader as bt
import pandas as pd
import pyodbc
import sqlalchemy as sa
from numpy import isnan

from enum import StrEnum, auto

from options_framework.option_types import OptionType, SelectFilter, FilterRange
from options_framework.spreads.butterfly import Butterfly
from options_framework.test_manager import OptionTestManager

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

class TimeSlot(StrEnum):
    MORNING = auto()
    MIDDLE = auto()
    AFTERNOON = auto()
    EOD = auto()

class Zone(StrEnum):
    ZONE_1 = auto()
    ZONE_2 = auto()
    ZONE_3 = auto()
    UNDEFINED = auto()


class OTMButterflyStrategy(bt.Strategy):
    params = (
        ('startdate', None),
        ('enddate', None),
        ('market_open', datetime.time(9, 31)),
        ('start_mid', datetime.time(12, 00)),
        ('start_afternoon', datetime.time(14, 30)),
        ('end_afternoon', datetime.time(16, 0)),
        ('eod', datetime.time(16, 15)),
        ('hull_period', 14),
        ('target_risk_to_reward', 9.0),
        ('options_manager', None),)


    def log(self, txt, dt=None):
        """ Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt, txt))

    def __init__(self):
        self.hull = bt.indicators.HullMA(self.data1, period=self.p.hull_period)
        self.vix = self.datas[2]
        self.dt = pd.to_datetime(f'{self.data.datetime.date(1)} {self.data.datetime.time(1)}')
        self.p.options_manager.get_current_option_chain(self.dt.to_pydatetime())
        self.portfolio = self.p.options_manager.portfolio
        self.option_chain = self.p.options_manager.option_chain
        self.log('init complete', self.dt)

    #def next(self):
    #    pass

    def next(self):
        dt = self.data.datetime.date(0)
        t = self.data.datetime.time(0)
        self.dt = pd.to_datetime(f'{dt} {t}')
        close = self.data[0]
        hull_ma_two_days_ago = self.hull[-2]
        hull_ma_one_day_ago = self.hull[-1]
        if isnan(hull_ma_two_days_ago):
            return

        if not self.dt.date() in self.p.options_manager.expirations:
            return

        self.p.options_manager.next(self.dt.to_pydatetime())
        hull_direction_option_type = OptionType.CALL if hull_ma_two_days_ago < hull_ma_one_day_ago else OptionType.PUT

        if self.p.market_open < t < self.p.start_mid:
            t_slot = TimeSlot.MORNING
        elif self.p.start_mid < t < self.p.start_afternoon:
            t_slot = TimeSlot.MIDDLE
        elif self.p.start_afternoon < t < self.p.end_afternoon:
            t_slot = TimeSlot.AFTERNOON
        else:
            t_slot = TimeSlot.EOD

        current_position = None if not self.portfolio.positions else self.portfolio.positions[next(iter(self.portfolio.positions))]
        if t == self.p.market_open:
            #self.log(t_slot, self.dt)
            # if current_position:
            #     self.portfolio.close_position(current_position, current_position.quantity)
            self.p.options_manager.get_current_option_chain(self.dt.to_pydatetime())

            vix = self.vix[0]

            if vix < 16:
                wing_width = 10
            elif 16 < vix < 20:
                wing_width = 20
            elif 20 < vix < 22:
                wing_width = 30
            else:
                wing_width = 40

            strikes = self.option_chain.expiration_strikes[expiration]
            strikes.sort(reverse=hull_direction_option_type == OptionType.PUT)

            # start at strike closest to close value
            start_strike = min(strikes, key=lambda x: abs(x-close))
            start_idx = strikes.index(start_strike)
            for idx in range(start_idx, len(strikes)):
                center_strike = strikes[idx]

                butterfly = Butterfly.get_position(options=self.option_chain.option_chain,
                                      expiration=expiration, option_type=hull_direction_option_type,
                                      center_strike=center_strike, wing_width=wing_width, quantity=1)
                actual_r2r = butterfly.risk_to_reward
                if actual_r2r >= self.p.target_risk_to_reward:
                    self.portfolio.open_position(option_position=butterfly, quantity=1)
                    butterfly.user_defined["highest_profit"] = {"profit": 0.0, "time": t}
                    print(f'open new position {butterfly.position_id} @ {t}')
                    break

        if current_position:
            current_profit = current_position.current_value - current_position.max_loss
            highest_profit = current_position.user_defined["highest_profit"]["profit"]

            if current_profit > highest_profit:
                highest_profit = current_profit
                current_position.user_defined["highest_profit"] = {"profit":highest_profit, "time": t}

            if current_profit > 0 and (close < current_position.lower_breakeven or close > current_position.upper_breakeven):
                zone = Zone.ZONE_2
            elif current_profit > 0 and (current_position.lower_breakeven < close < current_position.upper_breakeven):
                zone = Zone.ZONE_3
            elif current_profit < 0 and (close > current_position.upper_breakeven or close < current_position.lower_breakeven):
                zone = Zone.ZONE_1
            else:
                zone = Zone.UNDEFINED
            cost = current_position.max_profit
            percent_of_high = current_profit/highest_profit if highest_profit > 0 else 0
            pl = current_position.current_value / cost
            close_position = False

            if t_slot == TimeSlot.MORNING:
                if zone == Zone.ZONE_1:
                    close_position = False
                if zone == Zone.ZONE_2 and percent_of_high <= 0.25:
                    if current_profit > cost*0.50:
                        close_position = True
                if zone == Zone.ZONE_3 and percent_of_high <= 0.50:
                    if current_profit > cost * 0.75:
                        close_position = True
            if t_slot == TimeSlot.MIDDLE:
                if zone == Zone.ZONE_1 and pl <= 0.4:
                    close_position = False
                if zone == Zone.ZONE_2 and percent_of_high <= 0.50:
                    if current_profit > cost * 0.50:
                        close_position = True
                if zone == Zone.ZONE_3 and percent_of_high <= 0.60:
                    if current_profit > cost * 0.75:
                        close_position = True
            if t_slot == TimeSlot.AFTERNOON:
                if zone == Zone.ZONE_1 and pl <= 0.50:
                    close_position = False
                if zone == Zone.ZONE_2 and percent_of_high <= 0.75:
                    if current_profit > cost * 0.50:
                        close_position = True
                if zone == Zone.ZONE_3 and percent_of_high <= 0.90:
                    if current_profit > cost * 0.75:
                        close_position = True

            if close_position:
                self.log(f'close position {current_position.position_id} max loss: {current_position.max_loss}  close_reason {t_slot.name} {zone.name} {percent_of_high:.2f} @ {t} {current_position.current_value - current_position.max_loss}', self.dt)
                self.portfolio.close_position(current_position, quantity=current_position.quantity)
                current_position = None

        if t == self.p.end_afternoon:
            if current_position:
                self.log(f'close position {current_position.position_id} max loss: {current_position.max_loss} close_reason {t_slot.name} {zone.name} {percent_of_high:.2f} @ {t} {current_position.current_value - current_position.max_loss}', self.dt)
                self.portfolio.close_position(current_position, quantity=current_position.quantity)
            self.log(f'portfolio value: {self.portfolio.portfolio_value:.2f}  cash: {self.portfolio.cash:.2f}', self.dt)
        # if t == self.p.eod:
        #     self.log(
        #         f'portfolio value: {self.portfolio.portfolio_value:.2f}  cash: {self.portfolio.cash:.2f}',
        #         self.dt)


if __name__ == "__main__":
    #pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())

    server = settings.SERVER
    database = settings.DATABASE
    username = settings.USERNAME
    password = settings.PASSWORD
    ticker = 'SPXW'
    startdate = datetime.datetime(2016, 3, 1)
    enddate = datetime.datetime(2016, 4, 30)
    starting_cash = 100_000.0

    connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database \
                        + ';UID=' + username + ';PWD=' + password
    connection = pyodbc.connect(connection_string)

    query = get_price_data_query(startdate, enddate)
    df = pd.read_sql(query, connection, index_col='datetime', parse_dates=True)
    connection.close()

    options_filter = SelectFilter(symbol='SPXW',
                                  expiration_dte=FilterRange(high=6),
                                  strike_offset=FilterRange(100, 100))

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
    vix_df = pd.read_csv("C:\\_data\\backtesting_data\\deltaneutral\VIX_.csv", parse_dates=True, index_col=0)
    df.index = pd.to_datetime(df.index, unit='ms')
    df_vix = vix_df.loc['2016-03-01':'2016-05-01']

    data = bt.feeds.PandasData(dataname=df, name='SPX')
    daily_data = bt.feeds.PandasData(dataname=df_daily, name='SPX')
    vix_data = bt.feeds.PandasData(dataname=df_vix, name='VIX')

    cerebro = bt.Cerebro()
    cerebro.addstrategy(OTMButterflyStrategy, startdate=startdate, enddate=enddate,
                        options_manager=option_test_manager)

    cerebro.adddata(data)
    cerebro.adddata(daily_data)
    cerebro.adddata(vix_data)
    cerebro.run()

    t2 = time.time()
    time_diff = t2-t1
    hours = math.floor(time_diff/3600)
    minutes = math.floor((time_diff - (hours*3600))/60)
    seconds = math.floor(time_diff - hours*3600 - minutes*60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())
