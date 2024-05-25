import dataclasses
import datetime

import pandas as pd
#import pyodbc
from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.sql import text

from multiprocessing import Pool

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter

def create_option(quote_datetime, row, fields_list):
    option = Option(
        option_id=row['option_id'],
        symbol=row['symbol'],
        expiration=row['expiration'].date(),
        strike=row['strike'],
        option_type=OptionType.CALL if row['option_type'] == 1 else OptionType.PUT,
        quote_datetime=quote_datetime,
        spot_price=row['spot_price'],
        bid=row['bid'],
        ask=row['ask'],
        price=row['price'],
        delta=row['delta'] if 'delta' in fields_list else None,
        gamma=row['gamma'] if 'gamma' in fields_list else None,
        theta=row['theta'] if 'theta' in fields_list else None,
        vega=row['vega'] if 'vega' in fields_list else None,
        rho=row['rho'] if 'rho' in fields_list else None,
        open_interest=row['open_interest'] if 'open_interest' in fields_list else None,
        implied_volatility=row['implied_volatility'] if 'implied_volatility' in fields_list else None)
    return option


class SQLServerDataLoader(DataLoader):

    def __init__(self, *, start: datetime.datetime, end: datetime.datetime, select_filter: SelectFilter,
                 extended_option_attributes: list[str] = None):
        super().__init__(start=start, end=end, select_filter=select_filter, extended_option_attributes=extended_option_attributes)
        server = settings.SERVER
        database = settings.DATABASE
        username = settings.USERNAME
        password = settings.PASSWORD
        connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database \
                                 + ';UID=' + username + ';PWD=' + password
        connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": connection_string})

        self.sql_alchemy_engine = create_engine(connection_url)
        self.last_loaded_date = start - datetime.timedelta(days=1)
        self.start_load_date = start
        self.datetimes_list = self._get_datetimes_list()
        expirations = self._get_expirations_list()
        self.expirations = [x.to_pydatetime().date() for x in list(expirations['expiration'])]

    def load_cache(self, start: datetime.datetime):
        self.start_load_date = start
        start_loc = self.datetimes_list.index.get_loc(str(start))
        end_loc = start_loc + settings.SQL_DATA_LOADER_SETTINGS.buffer_size
        end_loc = end_loc if end_loc < len(self.datetimes_list) else len(self.datetimes_list)-1
        query_end_date = self.datetimes_list.iloc[end_loc].name.to_pydatetime()
        query = self._build_query(start, query_end_date)
        with self.sql_alchemy_engine.connect() as conn:
            df = pd.read_sql(query, conn, index_col="quote_datetime", parse_dates=True)

        df.index = pd.to_datetime(df.index)
        self.data_cache = df
        self.last_loaded_date = df.iloc[-1].name.to_pydatetime() # set to end of data loaded

    def get_option_chain(self, quote_datetime):

        df = self.data_cache.loc[str(quote_datetime)]
        #count = len(df)
        # rows = [(i, row, self.fields_list) for i, row in df.iterrows()]
        # pool = Pool(processes=10)
        # options = pool.starmap_async(create_option, rows).get()
        # pool.close()
        # pool.join()


        options = [Option(
            option_id=row['option_id'],
            symbol=row['symbol'],
            expiration=row['expiration'].date(),
            strike=row['strike'],
            option_type=OptionType.CALL if row['option_type'] == 1 else OptionType.PUT,
            quote_datetime=i,
            spot_price=row['spot_price'],
            bid=row['bid'],
            ask=row['ask'],
            price=row['price'],
            delta=row['delta'] if 'delta' in self.extended_option_attributes else None,
            gamma=row['gamma'] if 'gamma' in self.extended_option_attributes else None,
            theta=row['theta'] if 'theta' in self.extended_option_attributes else None,
            vega=row['vega'] if 'vega' in self.extended_option_attributes else None,
            rho=row['rho'] if 'rho' in self.extended_option_attributes else None,
            open_interest=row['open_interest'] if 'open_interest' in self.extended_option_attributes else None,
            implied_volatility=row['implied_volatility'] if 'implied_volatility' in self.extended_option_attributes else None
            ) for i, row in df.iterrows()]

        super().on_option_chain_loaded(quote_datetime=quote_datetime, option_chain=options)

    def on_options_opened(self, portfolio, options: list[Option]) -> None:
        option_ids = [str(o.option_id) for o in options]
        open_date = options[0].trade_open_info.date
        #print(f"options {','.join(option_ids)} were opened on {open_date}")
        fields = ['option_id', 'symbol', 'expiration', 'strike', 'option_type', 'quote_datetime', 'spot_price',
                  'bid', 'ask', 'price'] + self.extended_option_attributes
        field_mapping = ','.join([db_field for option_field, db_field in settings.FIELD_MAPPING.items() \
                                  if option_field in fields])
        query = "select " + field_mapping
        query += settings.SELECT_OPTIONS_QUERY['from']
        query += f' where option_id in ({",".join(option_ids)})'
        query += f' and {settings.SELECT_OPTIONS_QUERY.quote_datetime_field} >= CONVERT(datetime2, \'{open_date}\')'
        query += f' order by {settings.SELECT_OPTIONS_QUERY.quote_datetime_field}'
        with self.sql_alchemy_engine.connect() as conn:
            df = pd.read_sql(query, conn, index_col="quote_datetime", parse_dates=True)
        df.index = pd.to_datetime(df.index)

        for option in options:
            cache = df.loc[df['option_id'] == option.option_id]
            option.update_cache = cache

    def get_expirations(self):
        return self.expirations

    def _build_query(self, start_date: datetime.datetime, end_date: datetime.datetime):
        fields = ['option_id', 'symbol', 'expiration', 'strike', 'option_type', 'quote_datetime', 'spot_price',
                       'bid', 'ask', 'price'] + self.extended_option_attributes
        field_mapping = ','.join([db_field for option_field, db_field in settings.FIELD_MAPPING.items() \
                                  if option_field in fields])
        filter_dict = dataclasses.asdict(self.select_filter)
        query = settings.SELECT_OPTIONS_QUERY['select']
        query += field_mapping
        query += settings.SELECT_OPTIONS_QUERY['from']
        query += (settings.SELECT_OPTIONS_QUERY['where']
                  .replace('{symbol}', self.select_filter.symbol)
                  .replace('{start_date}', str(start_date))
                  .replace('{end_date}', str(end_date)))
        if self.select_filter.option_type:
            query += f' and option_type = {self.select_filter.option_type.value}'

        if self.select_filter.expiration_dte:
            low_val, high_val = self.select_filter.expiration_dte.low, self.select_filter.expiration_dte.high
            if low_val and low_val > 0:
                query += f' and expiration >= DATEADD(day, {low_val}, quote_datetime)'
            if high_val:
                query += f' and expiration <= DATEADD(day, {high_val}, quote_datetime)'

        if self.select_filter.strike_offset:
            low_val, high_val = self.select_filter.strike_offset.low, self.select_filter.strike_offset.high
            if low_val:
                query += f' and strike >= {settings.SELECT_OPTIONS_QUERY.spot_price_field}-{low_val}'
            if high_val:
                query += f' and strike <= {settings.SELECT_OPTIONS_QUERY.spot_price_field}+{high_val}'

        for fltr in [f for f in filter_dict.keys() if 'range' in f]:
            name, low_val, high_val = fltr[:-6], filter_dict[fltr]['low'], filter_dict[fltr]['high']
            for val in [low_val, high_val]:
                if val is not None:# and high_val is not None:
                    operator = ">=" if val is low_val else "<="
                    query += f' and {name} {operator} {val}'

        query += ' order by quote_datetime, expiration, strike'

        return query

    def _get_datetimes_list(self):
        symbol = self.select_filter.symbol
        start_date = self.start_datetime
        end_date = self.end_datetime
        query = settings.SELECT_OPTIONS_QUERY.quote_datetime_list_query.replace('{symbol}', symbol).replace('{start_date}', str(start_date)).replace('{end_date}', str(end_date))
        with self.sql_alchemy_engine.connect() as conn:
            df = pd.read_sql(query, conn, parse_dates=True, index_col=[settings.SELECT_OPTIONS_QUERY.quote_datetime_field])
        df.index = pd.to_datetime(df.index)
        return df

    def _get_expirations_list(self):
        symbol = self.select_filter.symbol
        start_date = self.start_datetime
        end_date = self.end_datetime
        query = "select distinct expiration "
        query += settings.SELECT_OPTIONS_QUERY['from']
        query += (settings.SELECT_OPTIONS_QUERY['where']
                  .replace('{symbol}', self.select_filter.symbol)
                  .replace('{start_date}', str(start_date))
                  .replace('{end_date}', str(end_date)))
        query += " order by expiration"
        with self.sql_alchemy_engine.connect() as conn:
            df = pd.read_sql(query, conn, parse_dates=True)
        return df
