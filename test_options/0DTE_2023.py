"""
1. At 10am ET, if SPX is trading below its 3sma on the daily chart, sell a call credit spread.

2. At 10am ET, if SPX is trading above its 3sma on the daily chart, do nothing.

3. At 10:30am ET, if SPX is trading above its 3sma on the daily chart, sell a put credit spread.

4. At 10:30am ET, if SPX is trading below its 3sma on the daily chart, do nothing.

"""
import datetime
import math
import sys
import time
import tomllib

import backtrader as bt
import pandas as pd
from pathlib import Path

from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from pprint import pprint as pp
from options_framework.config import settings
from options_framework.option_types import OptionType, SelectFilter, FilterRange, OptionCombinationType, \
    OptionPositionType
from options_framework.spreads.vertical import Vertical
from options_framework.spreads.single import Single
from options_framework.test_manager import OptionTestManager

with open("config\\.secrets.toml", 'rb') as f:
    db_settings = tomllib.load(f)


def get_data(database, query, index_col):
    """

    :type database: SQLAlchemy data
    """
    conn_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + db_settings[
        'server'] + ';DATABASE=' + database + ';UID=' + db_settings['username'] + ';PWD=' + db_settings['password']
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


class SPX0DTE(bt.Strategy):
    params = (
        ('start_date', None),
        ('end_date', None),
        ('test_manager', None),
        ('max_risk', 0.05),
        ('sma_period', 3),
        ('delta', 0.48),
        ('spread_width', 5)
    )

    def log(self, txt, dt=None):
        dt = dt if dt is not None else self.dt if self.dt is not None \
            else pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        print('%s, %s' % (dt, txt))

    def __init__(self):
        self.data = self.datas[0]
        self.dt = None
        self.sma = bt.indicators.SMA(self.data1, period=self.p.sma_period)
        self.current_date = None
        self.current_time = None
        self.portfolio = self.p.test_manager.portfolio
        self.option_chain = self.p.test_manager.option_chain
        print('init complete')

    def next(self):
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        self.portfolio.next(self.dt)

        current_date = self.data.datetime.date(0)
        current_time = self.data.datetime.time(0)

        # Once per day
        if current_date != self.current_date:
            self.current_date = current_date
            positions_value = sum(p.get_profit_loss() for p in self.portfolio.positions.values())
            self.log(f'{positions_value + self.portfolio.cash:.2f}')

        # determine if today is an expiration day
        if self.current_date not in self.p.test_manager.expirations:
            return

        price = self.data.close[0]
        sma_3day = self.sma[0]

        if current_time.hour == 10 and current_time.minute == 0:
            #status = " price < sma " if price < sma_3day else " price > sma "
            if price < sma_3day:
                # self.log(f'calls: price={price:.2f} sma={sma_3day:.2f} {status}')
                # self.log('sell call credit spread')
                self.p.test_manager.get_current_option_chain(self.dt.to_pydatetime())

                short_option = Single.get_single_by_delta(option_chain=self.option_chain,
                                                          expiration=self.current_date,
                                                          option_type=OptionType.CALL,
                                                          option_position_type=OptionPositionType.SHORT,
                                                          delta=self.p.delta)
                long_option = Single.get_single(option_chain=self.option_chain,
                                                expiration=self.current_date,
                                                option_type=OptionType.CALL,
                                                option_position_type=OptionPositionType.LONG,
                                                strike=short_option.strike + self.p.spread_width)
                credit_spread = Vertical(options=[long_option.option, short_option.option],
                                         option_combination_type=OptionCombinationType.VERTICAL,
                                         option_position_type=OptionPositionType.SHORT, quantity=-1)
                risk_amount = self.portfolio.cash * self.p.max_risk
                if credit_spread.max_loss > 0:
                    qty = int(risk_amount / credit_spread.max_loss)
                    qty = 1 if qty == 0 else qty
                    self.portfolio.open_position(credit_spread, quantity=qty)
                    message = f'opened call credit spread {short_option.strike}/{long_option.strike} ' \
                              + f'for {credit_spread.current_value:.2f}'
                    self.log(message)
                pass

        if current_time.hour == 10 and current_time.minute == 30:
            #status = " price < sma " if price < sma_3day else " price > sma "
            if price > sma_3day:
                # self.log(f'puts: price={price:.2f} sma={sma_3day:.2f} {status}')
                # self.log('sell put credit spread')
                self.p.test_manager.get_current_option_chain(self.dt.to_pydatetime())
                put_delta = self.p.delta * -1
                short_option = Single.get_single_by_delta(option_chain=self.option_chain,
                                                          expiration=self.current_date,
                                                          option_type=OptionType.PUT,
                                                          option_position_type=OptionPositionType.SHORT,
                                                          delta=put_delta)
                long_option = Single.get_single(option_chain=self.option_chain,
                                                expiration=self.current_date,
                                                option_type=OptionType.PUT,
                                                option_position_type=OptionPositionType.LONG,
                                                strike=short_option.strike - self.p.spread_width)
                credit_spread = Vertical(options=[long_option.option, short_option.option],
                                         option_combination_type=OptionCombinationType.VERTICAL,
                                         option_position_type=OptionPositionType.SHORT, quantity=-1)

                risk_amount = self.portfolio.cash * self.p.max_risk
                if credit_spread.max_loss > 0:
                    qty = int(risk_amount / credit_spread.max_loss)
                    qty = 1 if qty == 0 else qty
                    self.portfolio.open_position(credit_spread, quantity=qty)
                    message = f'opened put credit spread {short_option.strike}/{long_option.strike} ' \
                              + f'for {credit_spread.current_value:.2f}'
                    self.log(message)
                pass

        pass

    # def notify_cashvalue(self, cash, value):
    #     if self.dt is None: return
    #     if self.dt.time() == datetime.time(16, 15):
    #         self.log(f'what {self.portfolio.cash}')

    def stop(self):
        if len(self.portfolio.positions) == 0:
            return
        for p in self.portfolio.positions.values():
            self.portfolio.close_position(p)
        self.log(f'ending cash: {self.portfolio.cash:.2f}')


if __name__ == "__main__":
    pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())
    s = sys.argv[1] if len(sys.argv) >= 3 else '08-03-2020'
    e = sys.argv[2] if len(sys.argv) >= 3 else '09-30-2020'
    startdate = datetime.datetime.strptime(s, "%m-%d-%Y")
    enddate = datetime.datetime.strptime(e, "%m-%d-%Y")
    starting_cash = 100_000.0

    print(
        f'Start test {Path(__file__).name}: start date: {startdate} end date: {enddate} starting cash: {starting_cash}')

    # Set up options for testing
    options_select_filter = SelectFilter(
        symbol='SPXW',
        expiration_dte=FilterRange(high=1),
        strike_offset=FilterRange(low=35, high=35))
    test_manager = OptionTestManager(start_datetime=startdate, end_datetime=enddate,
                                     select_filter=options_select_filter, starting_cash=starting_cash,
                                     extended_option_attributes=['delta'])
    # Get price data and signals from sql server
    price_df = get_data(database=settings['database'], query=get_price_data_query(startdate, enddate),
                        index_col='datetime')
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
    df_daily.dropna(inplace=True)  # get daily timeframe for moving average

    daily_data = bt.feeds.PandasData(dataname=df_daily, name='SPX')

    cerebro = bt.Cerebro()
    cerebro.addstrategy(SPX0DTE,
                        start_date=startdate,
                        end_date=enddate,
                        test_manager=test_manager,
                        spread_width=5)
    cerebro.adddata(data)
    cerebro.adddata(daily_data)
    results = cerebro.run()

    print(f'Ending cash: {test_manager.portfolio.cash}')
    root_folder = Path(r'C:\_data\backtesting_data\output')
    root_folder = root_folder.joinpath(Path(__file__).stem)
    now = datetime.datetime.now()
    output_file = root_folder.joinpath(f'{now.year}_{now.month}_{now.day}-{now.hour}-{now.minute}.csv')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    trades = test_manager.portfolio.closed_positions

    f = open(output_file, "w")
    f.write(
        "ID,Date,Type,Quantity,Open Spot Price,Close Spot Price,Open Time,Close Time,Open Price,Close Price,Short Strike,SS Price,Long Strike,LS Price,Trade Val,Close Val,Max Profit,Max Loss,PNL\n")

    for trade_id, trade in trades.items():
        open_dt = trade.get_open_datetime()
        dt = open_dt.date()
        close_dt = trade.get_close_datetime()
        option_type = trade.option_type.name
        max_profit = trade.max_profit
        max_loss = trade.max_loss
        qty = trade.long_option.trade_open_info.quantity
        pnl = trade.get_profit_loss()
        trade_price = trade.get_trade_price()
        close_price = trade.price
        short_strike = trade.short_option.strike
        ss_price = trade.short_option.trade_price
        long_strike = trade.long_option.strike
        ls_price = trade.long_option.trade_price
        trade_value = trade.trade_value
        close_value = sum(o.get_profit_loss() for o in trade.options)
        open_spot_price = trade.long_option.trade_open_info.spot_price
        close_spot_price = trade.long_option.trade_close_records[-1].spot_price
        open_time = datetime.datetime.strptime(str(open_dt), "%Y-%m-%d %H:%M:%S")
        close_time = datetime.datetime.strptime(str(close_dt), "%Y-%m-%d %H:%M:%S")

        line = f'{trade_id},{dt},{option_type},{qty},{open_spot_price},{close_spot_price},'
        line += f'{open_time},{close_time},{trade_price},{close_price},{short_strike},{ss_price},{long_strike},{ls_price},'
        line += f'{trade_value:.2f},{close_value:2f},{max_profit},{max_loss},{pnl}\n'
        f.write(line)

    f.close()

    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())
