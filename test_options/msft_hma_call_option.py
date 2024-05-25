"""
Test MSFT: Buy 30-day call, one strike OTM when 20-day Hull MA is up for the last two days.
Sell call and buy put one strike OTM when 20-day Hull MA is down for the last two days
"""

import datetime
from pathlib import Path
import datetime
import warnings
from pprint import pprint as pp
import tomllib

import backtrader as bt
import pandas as pd

from numpy import isnan

from options_framework.option_types import OptionType, FilterRange
from options_framework.test_manager import OptionTestManager, SelectFilter
from options_framework.spreads.single import Single

warnings.filterwarnings('ignore')

from options_framework.config import settings as options_settings

with open("config\\backtest_settings.toml", 'rb') as f:
    backtest_settings = tomllib.load(f)

class HullMAOptionStrategy(bt.Strategy):
    params = (
        ('startdate', None),
        ('enddate', None),
        ('hull_period', 20),
        ('options_manager', None),)

    def log(self, txt, dt=None):
        """ Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt, txt))

    def __init__(self):
        self.hull = bt.indicators.HullMA(self.data, period=self.p.hull_period)
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')
        self.portfolio = self.p.options_manager.portfolio
        self.option_chain = self.p.options_manager.spx_option_chain_puts

    def next(self):
        self.dt = pd.to_datetime(f'{self.data.datetime.date(0)} {self.data.datetime.time(0)}')

        hull_ma_two_days_ago = self.hull[-2]
        hull_ma_one_day_ago = self.hull[-1]
        if isnan(hull_ma_two_days_ago):
            return


        option_type = OptionType.CALL if hull_ma_two_days_ago < hull_ma_one_day_ago else OptionType.PUT
        current_position = None if not self.portfolio.positions else self.portfolio.positions[next(iter(self.portfolio.positions))]

        if not current_position or option_type != current_position.option_type:
            # if an option is open, close it first
            if current_position:
                self.portfolio.close_position(current_position, 1)
            self.p.options_manager.get_current_option_chain(self.dt.to_pydatetime())
            dt_compare = self.data.datetime.date(0) + datetime.timedelta(days=30)
            exp = [e for e in self.option_chain.expirations if e > dt_compare][0]
            strikes = self.option_chain.expiration_strikes[exp]
            strike = 0
            if option_type == OptionType.CALL:
                strike = [s for s in strikes if s > self.data.close[0]][0]
            if option_type == OptionType.PUT:
                strikes.sort(reverse=True)
                strike = [s for s in strikes if s < self.data.close[0]][0]

            option = Single.get_single_position(option_chain=self.option_chain.spx_option_chain_puts, expiration=exp,
                                                option_type=option_type, strike=strike)

            self.portfolio.open_position(option_position=option, quantity=1)

        self.log(f'portfolio value: {self.portfolio.portfolio_value:.2f}  cash: {self.portfolio.cash:.2f}',  self.dt)

    def stop(self):
        position_ids = list(self.portfolio.positions.keys())
        for pos_id in position_ids:
            position = self.portfolio.positions[pos_id]
            self.portfolio.close_position(position, position.quantity)
        self.log(
            f'portfolio value: {self.portfolio.portfolio_value:.2f}  cash: {self.portfolio.cash:.2f}',
            self.dt)

if __name__ == "__main__":
    pp(options_settings.as_dict())
    pp(backtest_settings)
    startdate = datetime.datetime(2023, 1, 1)
    enddate = datetime.datetime(2023, 3, 31)
    ticker = "MSFT"
    starting_cash = 100_000.0

    path_to_stock_data = Path(backtest_settings['stock_data_dir'], "MSFT_.csv")
    stock_price_df = pd.read_csv(path_to_stock_data, parse_dates=True, index_col=0)
    after_start_date = stock_price_df.index >= startdate
    before_end_date = stock_price_df.index <= enddate
    between_two_dates = after_start_date & before_end_date
    df = stock_price_df.loc[between_two_dates]

    msft_data = bt.feeds.PandasData(dataname=df, name=ticker)
    options_filter = SelectFilter(symbol=ticker,
                                  expiration_range=FilterRange(None, datetime.date(2023, 9, 10)),
                                  strike_offset=FilterRange(200, 400))
    options_manager = OptionTestManager(startdate, enddate, options_filter, starting_cash)
    portfolio = options_manager.portfolio

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(starting_cash)
    cerebro.adddata(msft_data)
    cerebro.addstrategy(HullMAOptionStrategy, startdate=startdate, enddate=enddate, options_manager=options_manager)
    cerebro.run()
