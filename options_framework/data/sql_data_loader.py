import datetime

import pandas as pd
import pyodbc

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType


class SQLServerDataLoader(DataLoader):

    def __init__(self, settings_file: str, select_fields: list = None, *args, **kwargs):
        super().__init__(settings_file=settings_file, select_fields=select_fields, *args, **kwargs)
        self.quote_datetime = None
        server = settings.SERVER
        database = settings.DATABASE
        username = settings.USERNAME
        password = settings.PASSWORD
        self.connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database \
                                 + ';UID=' + username + ';PWD=' + password

    def load_data(self, quote_datetime: datetime.datetime, symbol: str, option_type_filter: OptionType = None,
                  range_filters: dict = None, *args, **kwargs):
        connection = pyodbc.connect(self.connection_string)
        self.quote_datetime = quote_datetime
        # query = (self.options_query.replace('{symbol}', symbol)
        #          .replace('{start_date}', str(quote_datetime))
        #          .replace('{end_date}', str(quote_datetime)))
        query = self._build_query(symbol=symbol, start_date=quote_datetime, end_date=quote_datetime,
                                  option_type_filter=option_type_filter, range_filters=range_filters)
        if 'quote_datetime' in self.select_fields:
            df = pd.read_sql(query, connection, index_col='quote_datetime', parse_dates=True)
        else:
            df = pd.read_sql(query, connection)

        connection.close()

        options = [Option(
            option_id=row['option_id'],
            symbol=row['symbol'],
            expiration=row['expiration'].date(),
            strike=row['strike'],
            option_type=OptionType.CALL if row['option_type'] == 1 else OptionType.PUT,
            quote_datetime=i if 'quote_datetime' in self.select_fields else None,
            spot_price=row['spot_price'] if 'spot_price' in self.select_fields else None,
            bid=row['bid'] if 'bid' in self.select_fields else None,
            ask=row['ask'] if 'ask' in self.select_fields else None,
            price=row['price'] if 'price' in self.select_fields else None,
            delta=row['delta'] if 'delta' in self.select_fields else None,
            gamma=row['gamma'] if 'gamma' in self.select_fields else None,
            theta=row['theta'] if 'theta' in self.select_fields else None,
            vega=row['vega'] if 'vega' in self.select_fields else None,
            rho=row['rho'] if 'rho' in self.select_fields else None,
            open_interest=row['open_interest'] if 'open_interest' in self.select_fields else None,
            implied_volatility=row['implied_volatility'] if 'implied_volatility' in self.select_fields else None
            ) for i, row in df.iterrows()]

        super().on_data_loaded(quote_datetime=quote_datetime, option_chain=options)

    def _build_query(self, symbol: str, start_date: datetime.datetime, end_date: datetime.datetime,
                     option_type_filter: OptionType = None, range_filters: dict = None):
        fields = ['option_id'] + self.select_fields
        field_mapping = ','.join([db_field for option_field, db_field in settings.FIELD_MAPPING.items() \
                                  if option_field in fields])
        query = settings.SELECT_OPTIONS_QUERY['select']
        query += field_mapping
        query += settings.SELECT_OPTIONS_QUERY['from']
        query += (settings.SELECT_OPTIONS_QUERY['where']
                  .replace('{symbol}', symbol)
                  .replace('{start_date}', str(start_date))
                  .replace('{end_date}', str(end_date)))
        if option_type_filter:
            query += f' and option_type = {option_type_filter.value} '
        if range_filters and 'expiration' in range_filters.keys():
            low_exp, high_exp = range_filters['expiration']['low'], range_filters['expiration']['high']
            query += f' and expiration between CONVERT(datetime2, \'{low_exp}\') and CONVERT(datetime2, \'{high_exp}\')'
        if range_filters and 'strike' in range_filters.keys():
            low_strike, high_strike = range_filters['strike']['low'], range_filters['strike']['high']
            query += f' and strike between {low_strike} and {high_strike}'
        if range_filters and 'delta' in range_filters.keys():
            low_delta, high_delta = range_filters['delta']['low'], range_filters['delta']['high']
            query += f' and delta between {low_delta} and {high_delta}'
        if range_filters and 'gamma' in range_filters.keys():
            low_gamma, high_gamma = range_filters['gamma']['low'], range_filters['gamma']['high']
            query += f' and gamma between {low_gamma} and {high_gamma}'
        if range_filters and 'theta' in range_filters.keys():
            low_theta, high_theta = range_filters['theta']['low'], range_filters['theta']['high']
            query += f' and theta between {low_theta} and {high_theta}'
        if range_filters and 'vega' in range_filters.keys():
            low_vega, high_vega = range_filters['vega']['low'], range_filters['vega']['high']
            query += f' and vega between {low_vega} and {high_vega}'
        if range_filters and 'rho' in range_filters.keys():
            low_rho, high_rho = range_filters['rho']['low'], range_filters['rho']['high']
            query += f' and rho between {low_rho} and {high_rho}'
        if range_filters and 'open_interest' in range_filters.keys():
            low_open_interest, high_open_interest = range_filters['open_interest']['low'], range_filters['open_interest']['high']
            query += f' and open_interest between {low_open_interest} and {high_open_interest}'
        if range_filters and 'implied_volatility' in range_filters.keys():
            low_iv, high_iv = range_filters['implied_volatility']['low'], range_filters['implied_volatility']['high']
            query += f' and implied_volatility between {low_iv} and {high_iv}'

        query += settings.SELECT_OPTIONS_QUERY['order_by']
        query += ','.join(self.order_by_fields)

        return query
