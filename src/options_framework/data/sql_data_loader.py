import dataclasses
import datetime

import pandas as pd
from pandas import DataFrame
#import pyodbc
from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.sql import text

from multiprocessing import Pool

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter, FilterRange

class SQLServerDataLoader(DataLoader):

    def __init__(self, *, start: datetime.datetime, end: datetime.datetime, select_filter: SelectFilter,
                 extended_option_attributes: list[str] = None):
        super().__init__(start=start, end=end, select_filter=select_filter, extended_option_attributes=extended_option_attributes)
        server = settings['server']
        database = settings['database']
        username = settings['username']
        password = settings['password']
        connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database \
                                 + ';UID=' + username + ';PWD=' + password
        connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": connection_string})

        self.sql_alchemy_engine = create_engine(connection_url)
        self.datetimes_list = self._get_datetimes_list()

    def load_option_chain_data(self, symbol: str, start: datetime.datetime) -> None:
        start = self.start_datetime
        end = start + datetime.timedelta(days=1)
        start = pd.to_datetime(start)
        end = pd.to_datetime(end)
        last_test_date = self.datetimes_list.iloc[-1].name
        if end > last_test_date:
            end = last_test_date

        query = self._build_query(symbol, start, end)
        with self.sql_alchemy_engine.connect() as conn:
            df = pd.read_sql(query, conn, index_col='quote_datetime', parse_dates='quote_datetime')

        super().on_option_chain_loaded(symbol=symbol, quote_datetime=start, options_data=df)

    def on_options_opened(self, options: list[Option]) -> None:
        option_ids = [str(o.option_id) for o in options]
        open_date = options[0].trade_open_info.date
        #print(f"options {','.join(option_ids)} were opened on {open_date}")
        fields = ['option_id', 'symbol', 'expiration', 'strike', 'option_type', 'quote_datetime', 'spot_price',
                  'bid', 'ask', 'price'] + self.extended_option_attributes
        field_mapping = ','.join([db_field for option_field, db_field in settings['field_mapping'].items() \
                                  if option_field in fields])
        query = "select " + field_mapping
        query += settings['select_options_query']['from']
        query += f' where option_id in ({",".join(option_ids)})'
        query += f' and {settings['select_options_query'].quote_datetime_field} >= CONVERT(datetime2, \'{open_date}\')'
        query += f' and {settings['select_options_query'].quote_datetime_field} <= CONVERT(datetime2, \'{self.end_datetime}\')'
        query += f' order by {settings['select_options_query'].quote_datetime_field}'
        with self.sql_alchemy_engine.connect() as conn:
            df = pd.read_sql(query, conn, index_col='quote_datetime', parse_dates='quote_datetime')
        df.index = pd.to_datetime(df.index)

        for option in options:
            cache = df.loc[df['option_id'] == option.option_id]
            option.update_cache = cache

    def get_expirations(self, symbol: str) -> list:
        expirations = self._get_expirations_df(symbol)
        expirations = [x.to_pydatetime().date() for x in list(expirations['expiration'])]
        return expirations

    def _build_query(self, symbol: str, start_date: datetime.datetime, end_date: datetime.datetime):
        fields = ['option_id', 'symbol', 'expiration', 'strike', 'option_type', 'quote_datetime', 'spot_price',
                       'bid', 'ask', 'price'] + self.extended_option_attributes
        field_mapping = ','.join([db_field for option_field, db_field in settings['field_mapping'].items() \
                                  if option_field in fields])
        filter_dict = dataclasses.asdict(self.select_filter)
        query = settings['select_options_query']['select']
        query += field_mapping
        query += settings['select_options_query']['from']
        query += (settings['select_options_query']['where']
                  .replace('{symbol}', symbol)
                  .replace('{start_date}', str(start_date))
                  .replace('{end_date}', str(end_date)))
        if self.select_filter.option_type:
            query += f' and option_type = {self.select_filter.option_type.value}'

        if self.select_filter.expiration_dte:
            low_val, high_val = self.select_filter.expiration_dte.low, self.select_filter.expiration_dte.high
            if low_val and low_val > 0:
                query += f' and expiration >= DATEADD(day, {low_val}, {settings['select_options_query'].quote_datetime_field})'
            else:
                query += f' and expiration >= {settings['select_options_query'].quote_datetime_field}'
            if high_val:
                query += f' and expiration <= DATEADD(day, {high_val}, {settings['select_options_query'].quote_datetime_field})'

        if self.select_filter.strike_offset:
            low_val, high_val = self.select_filter.strike_offset.low, self.select_filter.strike_offset.high
            if low_val:
                query += f' and strike > {settings['select_options_query'].spot_price_field}-{low_val}'
            if high_val:
                query += f' and strike < {settings['select_options_query'].spot_price_field}+{high_val}'

        for fltr in [f for f in filter_dict.keys() if 'range' in f]:
            name, low_val, high_val = fltr[:-6], filter_dict[fltr]['low'], filter_dict[fltr]['high']
            for val in [low_val, high_val]:
                if val is not None:# and high_val is not None:
                    operator = ">=" if val is low_val else "<="
                    query += f' and {name} {operator} {val}'

        query += f' order by quote_datetime, expiration, strike'

        return query

    def _get_datetimes_list(self):
        start_date = self.start_datetime
        end_date = self.end_datetime
        query = settings['select_options_query'].datetime_list_query.replace('{start_date}', str(start_date)).replace('{end_date}', str(end_date))
        with self.sql_alchemy_engine.connect() as conn:
            df = pd.read_sql(query, conn, parse_dates=settings['select_options_query'].quote_datetime_field, index_col=[settings['select_options_query'].quote_datetime_field])
        df.index = pd.to_datetime(df.index)
        return df

    def _get_expirations_df(self, symbol: str):
        start_date = self.start_datetime
        end_date = self.end_datetime
        exp_start = self.select_filter.expiration_dte.low
        exp_end = self.select_filter.expiration_dte.high
        if exp_start:
            start_date += datetime.timedelta(days=exp_start)
        if exp_end:
            end_date += datetime.timedelta(days=exp_end)
        else:
            end_date = datetime.date.max
        query = settings.SELECT_OPTIONS_QUERY['select_expirations_list_query'] \
                .replace('{symbol}', symbol) \
                .replace('{start_date}', str(start_date)) \
                .replace('{end_date}', str(end_date))
        with self.sql_alchemy_engine.connect() as conn:
            df = pd.read_sql(query, conn, parse_dates=settings['select_options_query'].quote_datetime_field)
        return df
