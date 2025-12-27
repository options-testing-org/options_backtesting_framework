"""
Iron condor rules:
long delta = 15, short delta = 5
DTE 10
risk per trade = 5%
stop loss = 200%
no profit taking
Close 1 day before expiration
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
from options_framework.option_types import OptionType, SelectFilter, FilterRange, OptionSpreadType, \
    OptionPositionType
from options_framework.spreads.iron_condor import IronCondor
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
        df = pd.read_sql(text(query), conn, index_col=index_col, parse_dates=True)

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

def get_signals_query(startdate, enddate):
    query = 'select trade_date, vol_trigger from spotgamma_report ' \
            + f" where trade_date >= CONVERT(datetime2, '{startdate}')" \
            + f" and trade_date <= CONVERT(datetime2, '{enddate}') " \
            + 'order by trade_date'

    return query

class SPX0DTE(bt.Strategy):
    params = (
        ('start_date', None),
        ('end_date', None),
        ('test_manager', None),
        ('max_risk', 0.10),
        ('sg_signals', None),
        ('long_delta', 0.06),
        ('short_delta', 0.10),
        ('stop_loss_pct', 2.0),
        ('profit_stop_pct', 0.5),
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
        self.current_date = None
        self.vol_trigger = None
        self.trade_today = True
        self.portfolio = self.p.test_manager.portfolio
        self.portfolio.bind(position_expired=self.expired)
        self.option_chain = self.p.test_manager.options
        print('init complete')

    def next(self):
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        self.portfolio.next(self.dt)

        current_date = self.data.datetime.date(0)

        # Once per day
        if current_date != self.current_date:
            self.current_date = current_date
            self.vol_trigger = self.p.sg_signals['vol_trigger'].loc[current_date]
            positions_value = sum(p.current_value for p in self.portfolio.positions.values())
            self.log(f'{positions_value + self.portfolio.cash:.2f}')
            self.trade_today = True

            open_price = self.data.open[0]
            if open_price < self.vol_trigger:
                self.trade_today = False

            # determine if today is an expiration day
            if self.current_date not in self.p.test_manager.expirations:
                self.trade_today = False

            #self.log(f'trade today {self.trade_today}')

        # Check profit/loss of open positions
        if len(self.portfolio.positions) > 0:
            positions = list(self.portfolio.positions.values())
            for pos in positions:
                to_close = False
                pnl = pos.get_unrealized_profit_loss()
                if pnl <= pos.user_defined['stop_loss']:
                    to_close = True
                # if pnl > pos.user_defined['profit_stop']:
                #     to_close = True
                if to_close:
                    self.portfolio.close_position(pos)
                    close_pnl = pos.get_profit_loss()
                    self.log(f'closed ({pos.position_id}) {pos.trade_value} for {close_pnl:.2f} Pct: {close_pnl/pos.trade_value*-1:.2f}%')

        if self.trade_today:
            price = self.data.close[0]
            if price < self.vol_trigger:
                return

            self.p.test_manager.get_current_option_chain(self.dt.to_pydatetime())

            expiration = current_date
            try:
                iron_condor = IronCondor.get_iron_condor_by_delta(option_chain=self.option_chain, expiration=expiration,
                                                              long_delta=self.p.long_delta,
                                                              short_delta=self.p.short_delta)
                risk_amount = self.portfolio.cash * self.p.max_risk
                if iron_condor.max_loss > 0:
                    qty = int(risk_amount / iron_condor.max_loss)
                    qty = 1 if qty == 0 else qty
                    iron_condor.update_quantity(quantity=qty)
                    profit_stop = iron_condor.current_value*-1*self.p.profit_stop_pct
                    stop_loss = iron_condor.current_value * self.p.stop_loss_pct
                    self.portfolio.open_position(iron_condor, quantity=qty, profit_stop=profit_stop, stop_loss=stop_loss)
                    message = f'opened iron condor ({iron_condor.position_id}) for {iron_condor.current_value:.2f}'
                    self.log(message)

                    self.trade_today = False
            except Exception as ex:
                self.log(ex)


    # def notify_cashvalue(self, cash, value):
    #     if self.dt is None: return
    #     if self.dt.time() == datetime.time(16, 15):
    #         self.log(f'what {self.portfolio.cash}')

    def stop(self):
        if len(self.portfolio.positions) == 0:
            return
        for p in list(self.portfolio.positions.values()):
            self.portfolio.close_position(p)
        self.log(f'ending cash: {self.portfolio.cash:.2f}')


if __name__ == "__main__":
    # settings.INCUR_FEES = True
    # settings.STANDARD_FEE = 1.03
    pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())
    s = sys.argv[1] if len(sys.argv) >= 3 else '08-03-2020'
    e = sys.argv[2] if len(sys.argv) >= 3 else '08-10-2020'
    startdate = datetime.datetime.strptime(s, "%m-%d-%Y")
    enddate = datetime.datetime.strptime(e, "%m-%d-%Y")
    starting_cash = 100_000.0

    print(
        f'Start test {Path(__file__).name}: start date: {startdate} end date: {enddate} starting cash: {starting_cash}')

    # Set up options for testing
    options_select_filter = SelectFilter(
        symbol='SPXW',
        expiration_dte=FilterRange(high=5),
        strike_offset=FilterRange(low=500, high=500))
    test_manager = OptionTestManager(start_datetime=startdate, end_datetime=enddate,
                                     select_filter=options_select_filter, starting_cash=starting_cash,
                                     extended_option_attributes=['delta'])

    # Get price data and signals from sql server
    price_df = get_data(database=settings.DATABASE, query=get_price_data_query(startdate, enddate),
                        index_col='datetime')
    data = bt.feeds.PandasData(dataname=price_df, name='SPX')
    signals_data = get_data(database=settings.SIGNALS_DATABASE, query=get_signals_query(startdate, enddate),
                            index_col='trade_date')

    cerebro = bt.Cerebro()
    cerebro.addstrategy(SPX0DTE,
                        start_date=startdate,
                        end_date=enddate,
                        test_manager=test_manager,
                        sg_signals=signals_data)
    cerebro.adddata(data)
    results = cerebro.run()

    print(f'Ending cash: {test_manager.portfolio.cash}')
    root_folder = Path(r'C:\_data\backtesting_data\output')
    root_folder = root_folder.joinpath(Path(__file__).stem)
    now = datetime.datetime.now()
    output_file = root_folder.joinpath(f'{now.year}_{now.month}_{now.day}-{now.hour}-{now.minute}.csv')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    trades = test_manager.portfolio.closed_positions

    f = open(output_file, "w")
    header = "ID,Date,Quantity,Open Spot Price,Close Spot Price,Open Time,Close Time,Open Price,Close Price," \
             + "Call Short Strike,Call Long Strike,Call Spread,Put Short Strike,Put Long Strike,Put Spread," \
             + "Trade Val,Close Val,Max Profit,Max Loss,PNL,Fees,W/L\n"
    f.write(header)

    for trade_id, trade in trades.items():
        open_dt = trade.get_open_datetime()
        dt = open_dt.date()
        close_dt = trade.get_close_datetime()
        max_profit = trade.max_profit
        max_loss = trade.max_loss
        qty = trade.long_call_option.quantity
        pnl = trade.get_profit_loss()
        win_lose = 'Win' if pnl > 0 else 'Lose'
        trade_price = trade.get_trade_price()
        close_price = trade.price
        call_long_strike = trade.long_call_option.strike
        call_short_strike = trade.short_call_option.strike
        put_long_strike = trade.long_put_option.strike
        put_short_strike = trade.short_put_option.strike
        trade_value = trade.trade_value
        close_value = sum(o.trade_close_info.profit_loss for o in trade.options)
        fees = sum(o.get_fees() for o in trade.options)
        open_spot_price = trade.long_call_option.trade_open_info.spot_price
        close_spot_price = trade.long_call_option.trade_close_records[-1].spot_price
        open_time = datetime.datetime.strptime(str(open_dt), "%Y-%m-%d %H:%M:%S")
        close_time = datetime.datetime.strptime(str(close_dt), "%Y-%m-%d %H:%M:%S")

        line = f'{trade_id},{dt},{qty},{open_spot_price},{close_spot_price},'
        line += f'{open_time},{close_time},{trade_price},{close_price},{call_long_strike},{call_short_strike},'
        line += f'{abs(call_long_strike-call_short_strike)},{put_long_strike},{put_short_strike},'
        line += f'{abs(put_long_strike-put_short_strike)},'
        line += f'{trade_value:.2f},{close_value:2f},{max_profit},{max_loss},{pnl},{fees},{win_lose}\n'
        f.write(line)

    f.close()

    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())
