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

    def load_option_chain(self, *, quote_datetime: datetime.datetime, symbol: str, filters: dict = None, **kwargs):
        if filters is None:
            filters = {}
        connection = pyodbc.connect(self.connection_string)
        self.quote_datetime = quote_datetime

        query = self._build_query(symbol=symbol, start_date=quote_datetime, end_date=quote_datetime,
                                  filters=filters)
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

        super().on_option_chain_loaded_loaded(quote_datetime=quote_datetime, option_chain=options)

    def _build_query(self, symbol: str, start_date: datetime.datetime, end_date: datetime.datetime,
                     filters: dict = None):
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
        for fltr in filters:
            if fltr == 'option_type':
                query += f' and {fltr} = {filters[fltr].value} '
            elif fltr == 'expiration':
                low_val, high_val = filters[fltr]['low'], filters[fltr]['high']
                query += f' and {fltr} between CONVERT(datetime2, \'{low_val}\') and CONVERT(datetime2, \'{high_val}\')'
            else:
                low_val, high_val = filters[fltr]['low'], filters[fltr]['high']
                query += f' and {fltr} between {low_val} and {high_val}'

        query += settings.SELECT_OPTIONS_QUERY['order_by']
        query += ','.join(self.order_by_fields)

        return query
