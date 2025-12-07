import datetime
import json
import math
import time
import warnings
import logging

import backtrader as bt
import pandas as pd
import pyodbc
import sqlalchemy as sa
from numpy import isnan

from enum import StrEnum, auto
from pathlib import Path
from pprint import pprint as pp

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
    UNDEFINED = auto()


class Zone(StrEnum):
    ZONE_1 = auto()
    ZONE_2 = auto()
    ZONE_3 = auto()
    UNDEFINED = auto()

def get_time_slot(t: datetime.time) -> TimeSlot:
    t_slot = None
    if datetime.time(9, 30) <= t < datetime.time(12, 00):
        t_slot = TimeSlot.MORNING
    elif datetime.time(12, 0) <= t < datetime.time(14, 30):
        t_slot = TimeSlot.MIDDLE
    elif datetime.time(14, 30) <= t < datetime.time(16, 00):
        t_slot = TimeSlot.AFTERNOON
    elif t >= datetime.time(16, 00):
        t_slot = TimeSlot.EOD
    else:
        t_slot = TimeSlot.UNDEFINED

    return t_slot


def get_zone(spot_price: float, lower_be: float, upper_be: float, in_profit: bool) -> Zone | None:
    zone = None
    if lower_be < spot_price < upper_be:
        zone = Zone.ZONE_3
    elif spot_price < lower_be or spot_price > upper_be and in_profit:
        zone = Zone.ZONE_2
    elif spot_price < lower_be or spot_price > upper_be and not in_profit:
        zone = Zone.ZONE_1
    else:
        zone = Zone.UNDEFINED

    return zone


class OTMButterflyStrategy(bt.Strategy):
    params = (
        ('startdate', None),
        ('enddate', None),
        ('starting_cash', 100_000.0),
        ('end_afternoon', datetime.time(15, 50)),
        ('hull_period', 14),
        ('target_risk_to_reward', 9.0),
        ('options_manager', None),
        ('log_file_name', None),
        ('log_level', logging.DEBUG))

    def log(self, txt, dt=None):
        """ Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt, txt))

    def on_close_position(self, position):
        time_slot = get_time_slot(self.data.datetime.time(0))
        profit = sum(x.trade_close_info.profit_loss for x in position.options)
        zone = get_zone(self.data[0], position.lower_breakeven, position.upper_breakeven, profit > 0)
        highest_profit = position.user_defined["highest_profit"]["profit"]
        percent_of_high = profit / highest_profit if highest_profit > 0 else 0
        position.user_defined["time_slot"] = time_slot.name
        position.user_defined["zone"] = zone.name
        self.log(
            f'close position {position.position_id} p/l: {profit} {percent_of_high:.2f} @ {position.user_defined["highest_profit"]["time"]} ',
            self.dt)
        logging.info(f'{datetime.datetime.now()} Close position({position.position_id}) @ {self.dt} pnl: {profit}')

    def __init__(self):
        self.hull = bt.indicators.HullMA(self.data1, period=self.p.hull_period)
        self.vix = self.datas[2]

        # self.p.options_manager.get_current_option_chain(self.dt.to_pydatetime())
        self.portfolio = self.p.options_manager.portfolio
        self.option_chain = self.p.options_manager.option_chain
        self.dt = pd.to_datetime(f'{self.data.datetime.date(1)} {self.data.datetime.time(1)}')
        self.log(f'init complete - Starting cash: {self.p.starting_cash:.2f}', self.dt)
        self.portfolio.bind(position_closed=self.on_close_position)
        logging.basicConfig(filename=self.p.log_file_name, encoding='utf-8', level=self.p.log_level)
        s = settings.as_dict()
        pp(s)
        logging.debug(json.dumps(s, indent=4))
        logging.debug(f'{datetime.datetime.now()} init complete {self.dt}')
        logging.info(f'start date:{startdate},  end date:{enddate} Min R2R: {self.p.target_risk_to_reward}')
        logging.info(f'HullMA 14-day direction entry @ 9:35 each morning.')
        logging.info(f'Starting cash: {self.p.starting_cash:.2f}')

    def next(self):
        dt = self.data.datetime.date(0)
        t = self.data.datetime.time(0)
        if t.minute % 5 != 0 and t < self.p.end_afternoon:
            return
        self.dt = pd.to_datetime(f'{dt} {t}')

        close = self.data[0]
        hull_ma_two_days_ago = self.hull[-2]
        hull_ma_one_day_ago = self.hull[-1]
        if isnan(hull_ma_two_days_ago):
            return

        if dt not in self.p.options_manager.expirations:
            return

        if t > self.p.end_afternoon:
            pass

        #self.log('next', self.dt)
        hull_direction_option_type = OptionType.CALL if hull_ma_two_days_ago < hull_ma_one_day_ago else OptionType.PUT

        current_position = None if not self.portfolio.positions else self.portfolio.positions[
            next(iter(self.portfolio.positions))]

        time_slot = get_time_slot(t)
        self.portfolio.next(self.dt)

        if time_slot == TimeSlot.MORNING and not current_position:
            self.p.options_manager.get_current_option_chain(self.dt.to_pydatetime())

            vix = self.vix[0]

            match vix:
                # case _ if vix < 12:
                #     wing_width = 5
                # case _ if 12 <= vix < 14:
                #     wing_width = 15
                # case _ if 14 <= vix < 17:
                case _ if vix < 17:
                    wing_width = 20
                case _ if 17 <= vix < 22:
                    wing_width = 25
                case _ if 22 <= vix < 25:
                    wing_width = 30
                case _ if 25 <= vix < 32:
                    wing_width = 35
                case _ if 32 <= vix < 35:
                    wing_width = 40
                case _ if vix >= 35:
                    wing_width = 50

            strikes = self.option_chain.expiration_strikes[dt]
            strikes.sort(reverse=hull_direction_option_type == OptionType.PUT)

            # start at strike closest to close value
            start_strike = min(strikes, key=lambda x: abs(x - close))
            start_idx = strikes.index(start_strike)
            for idx in range(start_idx, len(strikes)):
                center_strike = strikes[idx]

                try:
                    butterfly = Butterfly.get_balanced_butterfly(option_chain=self.option_chain.spx_option_chain_puts,
                                                                 expiration=dt, option_type=hull_direction_option_type,
                                                                 center_strike=center_strike, wing_width=wing_width)
                    actual_r2r = butterfly.risk_to_reward if butterfly.max_loss > 0 else 0
                    if actual_r2r >= self.p.target_risk_to_reward:
                        self.portfolio.open_position(option_position=butterfly, quantity=1)
                        butterfly.user_defined["highest_profit"] = {"profit": 0.0, "time": t}
                        butterfly.user_defined["vix"] = vix
                        butterfly.user_defined["open_time"] = self.dt
                        butterfly.user_defined["hull_direction"] = "Up" if hull_direction_option_type == OptionType.CALL else "Down"
                        butterfly.user_defined["time_slot"] = TimeSlot.UNDEFINED
                        butterfly.user_defined["zone"] = Zone.UNDEFINED
                        self.log(f'open new position {butterfly.position_id} @ {t} {butterfly.current_value}')
                        logging.info(f'{datetime.datetime.now()} Open new position({butterfly.position_id}): date: {self.dt} debit: {butterfly.max_loss:.2f} {butterfly}')
                        return
                except ValueError as ve:
                    self.log("ValueError", ve.strerror)
                    logging.error(f'{datetime.datetime.now()} {ve.strerror} @ {self.dt} center strike: {center_strike}, wing width: {wing_width}')
            pass

        if current_position:

            current_profit = current_position.current_value - current_position.max_loss
            highest_profit = current_position.user_defined["highest_profit"]["profit"]

            if current_profit > highest_profit:
                highest_profit = current_profit
                current_position.user_defined["highest_profit"] = {"profit": highest_profit, "time": t}

            zone = get_zone(close, current_position.lower_breakeven, current_position.upper_breakeven, current_profit > 0)

            cost = current_position.max_loss

            percent_of_high = current_profit / highest_profit if highest_profit > 0 else 0
            pl = current_position.current_value / cost
            close_position = False

            match time_slot:
                case TimeSlot.MORNING:
                    match zone:
                        case Zone.ZONE_2:
                            close_position = current_profit >= cost / 2 and percent_of_high <= 0.25
                        case Zone.ZONE_3:
                            close_position = current_profit >= cost and percent_of_high <= 0.50
                case TimeSlot.MIDDLE:
                    match zone:
                        case Zone.ZONE_1:
                            close_position = pl <= 0.4
                        case Zone.ZONE_2:
                            close_position = current_profit >= cost / 2 and percent_of_high <= 0.30
                        case Zone.ZONE_3:
                            close_position = current_profit >= cost and percent_of_high <= 0.40
                case TimeSlot.AFTERNOON:
                    match zone:
                        case Zone.ZONE_1:
                            close_position = pl < 0.5
                        case Zone.ZONE_2:
                            close_position = current_profit >= cost / 2 and percent_of_high <= 0.5
                        case Zone.ZONE_3:
                            close_position = current_profit >= cost and percent_of_high <= 0.75
                # case TimeSlot.EOD:
                #     close_position = True

            if close_position:
                self.portfolio.close_position(current_position, quantity=current_position.quantity)

        if t == self.p.end_afternoon:
            self.log(f'portfolio value: {self.portfolio.current_value:.2f}  cash: {self.portfolio.cash:.2f}', self.dt)
            if current_position:
                self.log('current_positions')

    def stop(self):
        current_position = None if not self.portfolio.positions else self.portfolio.positions[
            next(iter(self.portfolio.positions))]
        if current_position:
            self.portfolio.close_position(current_position, quantity=current_position.quantity)
        logging.info(f'ending cash: {self.portfolio.cash:.2f}')


if __name__ == "__main__":

    t1 = time.time()
    print(time.ctime())
    now = datetime.datetime.today()

    root_folder = r'C:\_data\backtesting_data\output\otm_butterfly'
    output_folder = f'{now.year}_{now.month}_{now.day}-{now.hour}-{now.minute}'
    log_file = Path(root_folder, output_folder, f"otm_butterfly.log_{output_folder}")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    server = settings.SERVER
    database = settings.DATABASE
    username = settings.USERNAME
    password = settings.PASSWORD
    ticker = 'SPXW'
    startdate = datetime.datetime(2016, 3, 1)
    #startdate = datetime.datetime(2020, 2, 1)
    #enddate = datetime.datetime(2016, 4, 29)
    enddate = datetime.datetime(2022, 6, 15)
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
    df_daily.dropna(inplace=True)  # get daily timeframe for hull ma
    vix_df = pd.read_csv("C:\\_data\\backtesting_data\\deltaneutral\\VIX_.csv", parse_dates=True, index_col=0)
    df.index = pd.to_datetime(df.index, unit='ms')
    df_vix = vix_df.loc[str(startdate.date()):str(enddate.date())]

    data = bt.feeds.PandasData(dataname=df, name='SPX')
    daily_data = bt.feeds.PandasData(dataname=df_daily, name='SPX')
    vix_data = bt.feeds.PandasData(dataname=df_vix, name='VIX')

    cerebro = bt.Cerebro()
    cerebro.addstrategy(OTMButterflyStrategy, startdate=startdate, enddate=enddate,
                        options_manager=option_test_manager, log_file_name=log_file)

    cerebro.adddata(data)
    cerebro.adddata(daily_data)
    cerebro.adddata(vix_data)
    cerebro.run()

    portfolio = option_test_manager.portfolio
    trades = portfolio.closed_positions

    results_file = Path(root_folder, output_folder, f"test_results{output_folder}.csv")
    f = open(results_file, "w")
    f.write("ID,Type,Open Spot Price,Close Spot Price,Low,Center,Upper,Open Time,Close Time,Open Price,Close Price,PNL,Max Loss,R2R,Highest Level,Time Highest,VIX,Hull Direction,Close Time Slot,Close Zone\n")

    for trade_id, trade in trades.items():
        open_dt = trade.get_open_datetime()
        close_dt = trade.get_close_datetime()
        option_type = trade.option_type.name
        r2r = trade.risk_to_reward
        cost = trade.max_loss
        pnl = trade.get_profit_loss()
        trade_price = trade.get_trade_price()
        close_price = trade.price
        open_spot_price = trade.center_option.trade_open_info.spot_price
        close_spot_price = trade.center_option.trade_close_records[-1].spot_price
        open_time = datetime.datetime.strptime(str(open_dt), "%Y-%m-%d %H:%M:%S")
        close_time = datetime.datetime.strptime(str(close_dt), "%Y-%m-%d %H:%M:%S")
        highest_level = trade.user_defined["highest_profit"]["profit"]
        time_highest = trade.user_defined["highest_profit"]["time"]
        vix = trade.user_defined["vix"]
        lower = trade.lower_option.strike
        center = trade.center_option.strike
        upper = trade.upper_option.strike
        hull = trade.user_defined["hull_direction"]
        time_slot = trade.user_defined["time_slot"]
        zone = trade.user_defined["zone"]
        line = f'{trade_id},{option_type},{open_spot_price},{close_spot_price},{lower},{center},{upper},{open_time},'
        line += f'{close_time},{trade_price},{close_price},{pnl},{cost},{r2r},{highest_level},{str(time_highest)},'
        line += f'{vix},{hull},{time_slot},{zone}\n'
        f.write(line)

    f.close()

    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())
    logging.info(f'Total run time: {hours} hours, {minutes} minutes')
