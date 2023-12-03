import dataclasses
import datetime

import pandas as pd
from pandas import DataFrame, Series
import pyodbc

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter

class SQLServerDataLoader(DataLoader):

    def __init__(self, start: datetime.datetime, end: datetime.datetime, select_filter: SelectFilter,
                 fields_list: list[str], *args, **kwargs):
        super().__init__(start, end, select_filter, fields_list, *args, **kwargs)
        self.data_cache = None
        settings.load_file(settings.SQL_DATA_FORMAT_SETTINGS)
        server = settings.SERVER
        database = settings.DATABASE
        username = settings.USERNAME
        password = settings.PASSWORD
        self.connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database \
                                 + ';UID=' + username + ';PWD=' + password
        self.load_cache(start)

    def load_cache(self, start: datetime.datetime):

        connection = pyodbc.connect(self.connection_string)

        query = self._build_query()
        if 'quote_datetime' in self.fields_list:
            df = pd.read_sql(query, connection, index_col='quote_datetime', parse_dates=True)
        else:
            df = pd.read_sql(query, connection)

        connection.close()

    def load_option_chain(self, *, quote_datetime: datetime.datetime):

        options = [Option(
            option_id=row['option_id'],
            symbol=row['symbol'],
            expiration=row['expiration'].date(),
            strike=row['strike'],
            option_type=OptionType.CALL if row['option_type'] == 1 else OptionType.PUT,
            quote_datetime=i if 'quote_datetime' in self.fields_list else None,
            spot_price=row['spot_price'] if 'spot_price' in self.fields_list else None,
            bid=row['bid'] if 'bid' in self.fields_list else None,
            ask=row['ask'] if 'ask' in self.fields_list else None,
            price=row['price'] if 'price' in self.fields_list else None,
            delta=row['delta'] if 'delta' in self.fields_list else None,
            gamma=row['gamma'] if 'gamma' in self.fields_list else None,
            theta=row['theta'] if 'theta' in self.fields_list else None,
            vega=row['vega'] if 'vega' in self.fields_list else None,
            rho=row['rho'] if 'rho' in self.fields_list else None,
            open_interest=row['open_interest'] if 'open_interest' in self.fields_list else None,
            implied_volatility=row['implied_volatility'] if 'implied_volatility' in self.fields_list else None
            ) for i, row in df.iterrows()]

        super().on_option_chain_loaded_loaded(quote_datetime=quote_datetime, option_chain=options)

    def _build_query(self):
        fields = ['option_id'] + self.fields_list
        field_mapping = ','.join([db_field for option_field, db_field in settings.FIELD_MAPPING.items() \
                                  if option_field in fields])
        ranges = [f for f in dataclasses.fields(self.select_filter) if 'range' in f]
        query = settings.SELECT_OPTIONS_QUERY['select']
        query += field_mapping
        query += settings.SELECT_OPTIONS_QUERY['from']
        query += (settings.SELECT_OPTIONS_QUERY['where']
                  .replace('{symbol}', self.select_filter.symbol)
                  .replace('{start_date}', str(self.start_datetime))
                  .replace('{end_date}', str(self.end_datetime)))
        for fltr in self.select_filter.ranges:
            if fltr == 'option_type':
                query += f' and {fltr} = {self.select_filter.ranges[fltr].value} '
            elif fltr == 'expiration':
                low_val, high_val = self.select_filter.ranges[fltr].low, self.select_filter.ranges[fltr].high
                query += f' and {fltr} between CONVERT(datetime2, \'{low_val}\') and CONVERT(datetime2, \'{high_val}\')'
            else:
                low_val, high_val = self.select_filter.ranges[fltr].low, self.select_filter.ranges[fltr].high
                query += f' and {fltr} between {low_val} and {high_val}'

        query += ' order by \'quote_datetime\', \'expiration\', \'strike\''

        return query

