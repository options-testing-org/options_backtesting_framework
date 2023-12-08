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


class Zone(StrEnum):
    ZONE_1 = auto()
    ZONE_2 = auto()
    ZONE_3 = auto()


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

        # self.p.options_manager.get_current_option_chain(self.dt.to_pydatetime())
        self.portfolio = self.p.options_manager.portfolio
        self.option_chain = self.p.options_manager.option_chain
        self.dt = pd.to_datetime(f'{self.data.datetime.date(1)} {self.data.datetime.time(1)}')
        self.log('init complete', self.dt)

    def next(self):
        dt = self.data.datetime.date(0)
        t = self.data.datetime.time(0)
        if t.minute % 5 != 0:
            return
        self.dt = pd.to_datetime(f'{dt} {t}')
        #self.log('next', self.dt)
        close = self.data[0]
        hull_ma_two_days_ago = self.hull[-2]
        hull_ma_one_day_ago = self.hull[-1]
        if isnan(hull_ma_two_days_ago):
            return

        if dt not in self.p.options_manager.expirations:
            return

        hull_direction_option_type = OptionType.CALL if hull_ma_two_days_ago < hull_ma_one_day_ago else OptionType.PUT

        current_position = None if not self.portfolio.positions else self.portfolio.positions[
            next(iter(self.portfolio.positions))]

        morning = t < self.p.start_mid
        midday = self.p.start_mid <= t <= self.p.start_afternoon
        afternoon = self.p.start_afternoon <= t < self.p.end_afternoon
        #return
        if morning and not current_position:
            self.p.options_manager.get_current_option_chain(self.dt.to_pydatetime())

            vix = self.vix[0]

            if vix < 12:
                wing_width = 5
            elif 12 <= vix < 14:
                wing_width = 10
            elif 14 <= vix < 17:
                wing_width = 20
            elif 17 <= vix < 22:
                wing_width = 25
            elif 22 <= vix < 25:
                wing_width = 30
            elif 25 <= vix < 32:
                wing_width = 35
            elif 32 <= vix < 35:
                wing_width = 40
            elif vix >= 35:
                wing_width = 50

            strikes = self.option_chain.expiration_strikes[dt]
            strikes.sort(reverse=hull_direction_option_type == OptionType.PUT)

            # start at strike closest to close value
            start_strike = min(strikes, key=lambda x: abs(x - close))
            start_idx = strikes.index(start_strike)
            for idx in range(start_idx, len(strikes)):
                center_strike = strikes[idx]

                butterfly = Butterfly.get_position(options=self.option_chain.option_chain,
                                                   expiration=dt, option_type=hull_direction_option_type,
                                                   center_strike=center_strike, wing_width=wing_width, quantity=1)
                actual_r2r = butterfly.risk_to_reward
                if actual_r2r >= self.p.target_risk_to_reward:
                    self.portfolio.open_position(option_position=butterfly, quantity=1)
                    butterfly.user_defined["highest_profit"] = {"profit": 0.0, "time": t}
                    butterfly.user_defined["vix"] = vix
                    butterfly.user_defined["open_time"] = self.dt
                    butterfly.user_defined["hull_direction"] = "Up" if hull_direction_option_type == OptionType.CALL else "Down"
                    print(f'open new position {butterfly.position_id} @ {t} {butterfly.current_value}')
                    break

        if current_position:
            self.portfolio.next(self.dt)
            current_profit = current_position.current_value - current_position.max_loss
            highest_profit = current_position.user_defined["highest_profit"]["profit"]
            highest_time = current_position.user_defined["highest_profit"]["time"]

            if current_profit > highest_profit:
                highest_profit = current_profit
                current_position.user_defined["highest_profit"] = {"profit": highest_profit, "time": t}

            below = close < current_position.lower_breakeven
            above = close > current_position.upper_breakeven
            inside = current_position.lower_breakeven >= close >= current_position.upper_breakeven
            zone1 = current_profit < 0 and (below or above)
            zone2 = current_profit > 0 and (below or above)
            zone3 = inside

            cost = current_position.max_loss

            percent_of_high = current_profit / highest_profit if highest_profit > 0 else 0
            pl = current_position.current_value / cost
            close_position = False

            if morning and zone1:
                close_position = False
            elif morning and zone2 and current_profit >= cost / 2 and percent_of_high <= 0.25:
                close_position = True
            elif morning and zone3 and current_profit >= cost and percent_of_high <= 0.50:
                close_position = True
            elif midday and zone1 and pl <= 0.4:
                close_position = True
            elif midday and zone2 and current_profit >= cost / 2 and percent_of_high <= 0.30:
                close_position = True
            elif midday and zone3 and current_profit >= cost and percent_of_high <= 0.40:
                close_position = True
            elif afternoon and zone1 and pl < 0.5:
                close_position = True
            elif afternoon and zone2 and current_profit >= cost / 2 and percent_of_high <= 0.5:
                close_position = True
            elif afternoon and zone3 and current_profit >= cost and percent_of_high <= 0.75:
                close_position = True

            if close_position:
                self.log(
                    f'close position {current_position.position_id} p/l: {current_profit} {percent_of_high:.2f} @ {highest_time} ',
                    self.dt)
                self.portfolio.close_position(current_position, quantity=current_position.quantity)
                current_position.user_defined["close_time"] = self.dt
                current_position = None

        if t == self.p.end_afternoon:
            if current_position:
                self.log(
                    f'close position {current_position.position_id} p/l: {current_profit} {percent_of_high:.2f} @ {highest_time} ',
                    self.dt)
                self.portfolio.close_position(current_position, quantity=current_position.quantity)
                current_position.user_defined["close_time"] = self.dt
            self.log(f'portfolio value: {self.portfolio.portfolio_value:.2f}  cash: {self.portfolio.cash:.2f}', self.dt)

    def stop(self):
        current_position = None if not self.portfolio.positions else self.portfolio.positions[
            next(iter(self.portfolio.positions))]
        if current_position:
            self.portfolio.close_position(current_position, quantity=current_position.quantity)


if __name__ == "__main__":
    # pp(settings.as_dict())
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
    df_five_min = df.resample('5Min').apply(ohlc)
    df_daily = df.resample('D').apply(ohlc)
    #re_df_daily = df_daily.resample('5Min').apply(ohlc)

    df_daily.dropna(inplace=True)  # get daily timeframe for hull ma
    vix_df = pd.read_csv("C:\\_data\\backtesting_data\\deltaneutral\VIX_.csv", parse_dates=True, index_col=0)
    df.index = pd.to_datetime(df.index, unit='ms')
    df_vix = vix_df.loc[str(startdate.date()):str(enddate.date())]
    #re_vix = vix_df.resample('5min').apply(ohlc)


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

    portfolio = option_test_manager.portfolio
    trades = portfolio.closed_positions

    f = open(r"C:\_data\backtesting_data\output\otm_butterfly\test_results.csv", "w")
    f.write("Type,Low,Center,Upper,Open Time,Close Time,Open Price,Close Price,PNL,Max Loss,R2R,Highest Level,Time Highest,VIX,Hull Direction\n")

    for trade_id, trade in trades.items():
        open_dt = trade.get_open_datetime()
        close_dt = trade.get_close_datetime()
        option_type = trade.option_type.name
        r2r = trade.risk_to_reward
        cost = trade.max_loss
        pnl = trade.get_profit_loss()
        trade_price = trade.get_trade_price()
        close_price = trade.price
        open_time = datetime.datetime.strptime(str(open_dt), "%Y-%m-%d %H:%M:%S")
        close_time = datetime.datetime.strptime(str(close_dt), "%Y-%m-%d %H:%M:%S")
        highest_level = trade.user_defined["highest_profit"]["profit"]
        time_highest = trade.user_defined["highest_profit"]["time"]
        vix = trade.user_defined["vix"]
        lower = trade.lower_option.strike
        center = trade.center_option.strike
        upper = trade.upper_option.strike
        hull = trade.user_defined["hull_direction"]
        line = f'{option_type},{lower},{center},{upper},{open_time},{close_time},{trade_price},{close_price},{pnl},{cost},'
        line += f'{r2r},{highest_level},{str(time_highest)},{vix},{hull}\n'
        f.write(line)

    f.close()

    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())
