import datetime
import math
import sys
import time
import csv
import numpy as np

import backtrader as bt
import pandas as pd
from pathlib import Path

def roundup_100(x):
    return int(math.ceil(x / 100.0)) * 100

from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from pprint import pprint as pp
from options_framework.config import settings
from options_framework.option_types import OptionType, SelectFilter, FilterRange, OptionPositionType, OptionStatus
from options_framework.test_manager import OptionTestManager
from options_framework.spreads.vertical import Vertical

data_format_file = 'daily_options_db_settings.toml'
ddates = []
sym_vals = {}

def get_connection(database):
    """

    :type database: SQLAlchemy data
    """
    conn_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER='+settings.SERVER+';DATABASE='+database+';UID='+settings.USERNAME+';PWD='+settings.PASSWORD
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": conn_string})

    engine = create_engine(connection_url)

    return engine

def get_datetime_list(startdate: datetime.date, enddate: datetime.date):
    query = 'select distinct quote_date, quote_date as qd from stock_prices ' \
            + f'where quote_date >= CONVERT(datetime2, \'{startdate}\') ' \
            + f' and quote_date <= CONVERT(datetime2, \'{enddate}\') ' \
            + 'order by quote_date'

    return query

def get_liquid_options_query(startdate: datetime.date, enddate: datetime.date):
    query = f'select stock_prices_id, quote_date, symbol, symbol_id, avg_volume, open_interest from liquid_options ' \
            + f'where quote_date >= CONVERT(datetime2, \'{startdate}\') ' \
            + f' and quote_date <= CONVERT(datetime2, \'{enddate}\') ' \
            + 'order by quote_date, symbol'  #+ 'and symbol_id in (1328, 9552, 309, 11709, 1882, 7283, 10762, 9132) ' \
    return query

def get_data_query(symbol_id, startdate: datetime.date, enddate: datetime.date):
    query = 'select quote_date, symbol, adjustedopen as [open], adjustedhigh as [high], ' \
            + 'adjustedlow as [low], adjustedclose as [close], volume, crsi, atr, ' \
            + 'days_since_52_wk_high as days_since_high ' \
            + 'from stock_prices sp inner join symbols s on sp.symbol_id = s.id ' \
            + f'where symbol_id={symbol_id} and quote_date >= CONVERT(datetime2, \'{startdate}\') ' \
            + f' and quote_date <= CONVERT(datetime2, \'{enddate}\') and [close] > 5 order by quote_date'
    return query

def get_symbol_dfs(dates_df, liquid_stocks_df, startdate: datetime.date, enddate: datetime.date):
    all_symbols = liquid_stocks_df['symbol_id'].unique()
    all_symbols.sort()
    dfs = []
    options_db_connection = get_connection(settings.database)

    for symbol_id in all_symbols:
        data = pd.read_sql(get_data_query(symbol_id, startdate, enddate), options_db_connection,
                                parse_dates='quote_date', index_col='quote_date')

        if len(data) == 0:
            continue

        symbol = data.iloc[0]['symbol']
        #print(f'getting data for {symbol}')

        # fill missing values with the previous value
        data['crsi'] = data['crsi'].astype(float).ffill()
        data['days_since_high'] = data['days_since_high'].astype(float).ffill()

        # Use the mean to replace zeros in the volume colums
        data['volume'].replace(0, data['volume'].mean(), inplace=True)
        data.dropna(inplace=True)

        if len(data) == 0:
            continue

        liq_df = liquid_stocks_df[liquid_stocks_df['symbol_id'] == symbol_id][['avg_volume', 'open_interest']]
        liq_df = liq_df[liq_df.index >= data.iloc[0].name] # get liq date from first date of stock data
        data = data.join(liq_df, how='outer')
        data['avg_volume'].fillna(value=data['avg_volume'].mean(), inplace=True)
        data['open_interest'].fillna(value=data['open_interest'].mean(), inplace=True)

        na_count = data.isna().sum()
        if na_count.sum() > 0:
            # print(f'{symbol} ({symbol_id}) has null data rows')
            data.dropna(inplace=True)

        if len(data) == 0:
            continue

        data_start = data.iloc[0].name
        data_end = data.iloc[-1].name

        # fill in any missing dates in the range
        data_dates = dates_df[(dates_df['qd'] >= data_start) & (dates_df['qd'] <= data_end)]
        data = data.join(data_dates, how='outer')
        data.drop(['qd'], axis=1, inplace=True)

        # if any rows were added in the last step, fill with data from previous rows
        data.loc[data['open'].isna(), 'symbol'] = symbol
        data['open'] = data['open'].astype(float).ffill()
        data['high'] = data['high'].astype(float).ffill()
        data['low'] = data['low'].astype(float).ffill()
        data['close'] = data['close'].astype(float).ffill()
        data['volume'] = data['volume'].astype(float).ffill()
        data['crsi'] = data['crsi'].astype(float).ffill()
        data['atr'] = data['atr'].astype(float).ffill()
        data['days_since_high'] = data['days_since_high'].astype(float).ffill()
        data['avg_volume'] = data['avg_volume'].astype(float).ffill()
        data['open_interest'] = data['open_interest'].astype(float).ffill()

        ddate = {'symbol_id': symbol_id, 'symbol': symbol, 'start_date': data.iloc[0].name, 'end_date': data.iloc[-1].name}
        ddates.append(ddate)
        dfs.append(data)

    return dfs

class MyBacktest:

    def expired(self, position):
        pnl = position.get_profit_loss()
        print(f'expired: {position.quote_datetime} {position.symbol} pnl: ${pnl:,.2f}')

    def run_backtest(self, datetimes_df, liquid_stocks_df, datas, test_manager):
        self.portfolio = test_manager.portfolio

        for _, qd in datetimes_df.iterrows():
            dt = qd['qd']
            self.portfolio.next(dt.to_pydatetime().date())
            print(f'{dt} Cash: ${self.portfolio.cash:,.2f}, Value: ${self.portfolio.portfolio_value:,.2f}')
            dt_datas = [d for d in datas if pd.to_datetime(dt) in d.index]
            for d in dt_datas:
                symbol = d.iloc[0]['symbol']
                crsi = d.loc[dt]['crsi']
                atr = d.loc[dt]['atr']
                close = d.loc[dt]['close']
                low = d.loc[dt]['low']
                days_since_high = d.loc[dt]['days_since_high']
                open_interest = d.loc[dt]['open_interest']
                avg_volume = d.loc[dt]['avg_volume']
                loc = d.index.get_loc(dt)

                # check to see if we need to close any open positions

                if any(p for p in list(self.portfolio.positions.values()) if p.symbol == symbol):
                    p = [p for p in list(self.portfolio.positions.values()) if p.symbol == symbol][0]
                    pnl = p.get_unrealized_profit_loss()
                    to_close = False
                    reason = ''
                    if pnl >= p.max_profit * 0.75:
                        reason = 'profit'
                        to_close = True
                    elif close <= p.short_option.strike:
                        reason = 'price < short strike'
                        to_close = True
                    elif (dt.to_pydatetime().date() - p.expiration).days == -1:
                        reason = 'expiration in 1 day'
                        to_close = True
                    if to_close:
                        self.portfolio.close_position(p)
                        print(f'close: {dt}, {symbol}, {reason}, pnl: ${pnl:.2f}')

                elif sym_vals[symbol]['open_trade'] and low <= sym_vals[symbol]['price_limit']:

                    test_manager.get_option_chain(symbol=symbol, quote_datetime=dt)
                    option_chain = test_manager.option_chains[symbol]

                    for exp in option_chain.expirations:
                        # try:
                        # find short strike
                        vertical = None
                        if exp not in option_chain.expiration_strikes.keys():
                            continue
                        exp_strikes = option_chain.expiration_strikes[exp]
                        exp_strikes.sort(reverse=True)
                        target_strike = close - close*0.05
                        strike = next(iter([s for s in exp_strikes if s < target_strike]), None)
                        if strike is None:
                            continue
                        min_price = close * 0.02
                        short_option = next(
                            o for o in option_chain.option_chain if o.expiration == exp and o.strike == strike)
                        if short_option.price < min_price:
                            continue

                        short_option.quantity = -1

                        options = [o for o in option_chain.option_chain if o.expiration == exp and o.strike
                                   < strike and o.delta >= -.10 and o.delta <= 0.0].copy()
                        if not options:
                            continue
                        options.sort(key=lambda x: x.strike, reverse=True)
                        long_option = next(iter([o for o in options if o.delta >= -0.10 or o.price <= min_price/2]), None)
                        if long_option is None:
                            continue
                        long_option.quantity = 1

                        try:
                            vertical = Vertical([long_option, short_option],
                                                option_position_type=OptionPositionType.SHORT,
                                                quantity=-1)

                            if vertical.max_profit >= 50.0:
                                max_risk = self.portfolio.portfolio_value * 0.10
                                qty = math.ceil(max_risk/vertical.max_loss)
                                if qty > 0:
                                    self.portfolio.open_position(vertical, quantity=qty)
                                    print(f'open: {dt} {vertical} max profit: ${vertical.max_profit:,.2f}')
                                break
                        except Exception as e:
                            if not 'No matching expiration' in str(e) or 'Insufficient margin' in str(e):
                                print(dt, symbol, e)

                    #print(f'{i} {symbol}, {crsi:.2f}, {days_since_high}, {open_interest:.2f}, {avg_volume:,}')

                elif crsi <= 15 and days_since_high <= 20 and open_interest >= 4_000 and avg_volume >= 1_000_000:
                    #print(f'{i} {symbol}, {crsi:.2f}, {days_since_high}, {open_interest}, {avg_volume}')
                    sym_vals[symbol]['open_trade'] = True
                    sym_vals[symbol]['price_limit'] = close - (close*0.05)
                    pass

        if any(p for p in list(self.portfolio.positions.values())):

            for p in list(self.portfolio.positions.values()):
                self.portfolio.close_position(p)
                pnl = p.get_profit_loss()
                print(f'close: {p.quote_datetime} test ending: {p.symbol} expiration: {p.expiration} pnl: ${pnl:.2f}')


if __name__ == "__main__":
    settings.database = 'options_db'
    settings.data_format_settings = data_format_file
    settings.incur_fees = True
    pp(settings.as_dict())
    t1 = time.time()
    print(time.ctime())
    s = sys.argv[1] if len(sys.argv) >= 3 else '01-01-2024'
    e = sys.argv[2] if len(sys.argv) >= 3 else '03-31-2024'
    startdate = datetime.datetime.strptime(s, "%m-%d-%Y")
    enddate = datetime.datetime.strptime(e, "%m-%d-%Y")
    starting_cash = 100_000.0

    fl = Path(__file__)
    print(f'Start test {fl.name}: start date: {startdate} end date: {enddate} starting cash: {starting_cash}')

    root_folder = Path(r'L:\_data\backtesting_data\output')
    root_folder = root_folder.joinpath(fl.stem)
    now = datetime.datetime.now()
    output_folder = root_folder.joinpath(f'{now.year}_{now.month}_{now.day}__{now.hour}-{now.minute}')
    output_folder.mkdir(parents=True, exist_ok=True)


    cnx = get_connection(settings.database)
    datetimes_df = pd.read_sql(get_datetime_list(startdate, enddate), cnx, parse_dates='quote_date', index_col=['quote_date'])

    cnx = get_connection('signals_db')
    liquid_df = pd.read_sql(get_liquid_options_query(startdate, enddate), cnx, parse_dates='quote_date', index_col=['quote_date'])
    symbols_list = liquid_df['symbol'].unique()
    for s in symbols_list:
        sym_vals[s] = {}
        sym_vals[s]['open_trade'] = False
        sym_vals[s]['price_limit'] = 0

    data_dfs = get_symbol_dfs(datetimes_df, liquid_df, startdate, enddate)
    options_select_filter = SelectFilter(
        option_type=OptionType.PUT,
        expiration_dte=FilterRange(high=35))
    options_test_manager = OptionTestManager(start_datetime=startdate, end_datetime=enddate, select_filter=options_select_filter,
                                    starting_cash=starting_cash, extended_option_attributes=['delta'])

    backtester = MyBacktest()
    options_test_manager.portfolio.bind(position_expired=backtester.expired)
    backtester.run_backtest(datetimes_df, liquid_df, data_dfs, options_test_manager)

    print(f'Cash at end of run: ${options_test_manager.portfolio.cash:,.2f}')

    # create running total file
    rt = options_test_manager.portfolio.close_values
    output_file = output_folder.joinpath(f'running_total_{now.year}{now.month}{now.day}{now.hour}{now.minute}.csv')
    rt_df = pd.DataFrame([[v] for (d, v) in rt], index=[d for (d, v) in rt], columns=['Value'])
    rt_df.to_csv(output_file)

    output_file = output_folder.joinpath(f'trades_{now.year}{now.month}{now.day}{now.hour}{now.minute}.csv')
    close_values = options_test_manager.portfolio.close_values

    trades = options_test_manager.portfolio.closed_positions
    trade_infos = []

    for trade_id, trade in trades.items():
        pnl = trade.get_profit_loss()
        short_strike = trade.short_option.strike
        long_strike = trade.long_option.strike

        trade_info = {
            "symbol": trade.symbol,
            "id": trade_id,
            "trade_date": trade.get_open_datetime().date(),
            "option_type": trade.option_type.name,
            "max_profit": trade.max_profit,
            "max_loss": trade.max_loss,
            "expiration": f'{trade.expiration.month}-{trade.expiration.day}-{trade.expiration.year}',
            "quantity": trade.long_option.trade_open_info.quantity,
            "open_spot_price": trade.long_option.trade_open_info.spot_price,
            "close_spot_price": trade.long_option.trade_close_records[-1].spot_price,
            "open_dt": trade.get_open_datetime(),
            "close_dt": trade.get_close_datetime(),
            "open_price": trade.get_trade_price(),
            "close_price": trade.price,
            "short_id": trade.short_option.option_id,
            "long_id": trade.long_option.option_id,
            "short_strike": short_strike,
            "long_strike": long_strike,
            "short_delta": trade.short_option.delta,
            "long_delta": trade.long_option.delta,
            "spread_width": abs(short_strike - long_strike),
            "open_value": trade.trade_value,
            "close_value": trade.closed_value,
            "fees": trade.get_fees(),
            "pnl": pnl,
            "win_loss": 'Win' if pnl > 0 else 'Lose'
        }

        trade_infos.append(trade_info)

    field_names = list(trade_info.keys())
    with open(output_file, 'w', newline='') as f:
        data_writer = csv.DictWriter(f, fieldnames=field_names)
        data_writer.writeheader()
        data_writer.writerows(trade_infos)


    t2 = time.time()
    time_diff = t2 - t1
    hours = math.floor(time_diff / 3600)
    minutes = math.floor((time_diff - (hours * 3600)) / 60)
    seconds = math.floor(time_diff - hours * 3600 - minutes * 60)
    print(f'Total run time: {hours} hours, {minutes} minutes, {seconds} seconds ')
    print(datetime.datetime.now())
