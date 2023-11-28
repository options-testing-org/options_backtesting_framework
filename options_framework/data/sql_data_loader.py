import datetime

import pandas as pd
import pyodbc

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType

class SQLServerDataLoader(DataLoader):

    def __init__(self, settings_file: str, fields: list = None, *args, **kwargs):
        super().__init__(settings_file=settings_file, fields=fields, *args, **kwargs)
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
        df = pd.read_sql(query, connection, index_col='quote_datetime', parse_dates=True)
        connection.close()
        options = [Option(option_id=row['option_id'], symbol=row['symbol'], expiration=row['expiration'],
                          strike=row['strike'], option_type=row['option_type'], quote_datetime=i,
                          spot_price=row['spot_price'], bid=row['bid'], ask=row['ask'],
                          price=row['price']) for i, row in df.iterrows()]

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
        if range_filters:
            pass # TODO: Add range filter to where clause
        query += settings.SELECT_OPTIONS_QUERY['order_by']

        return query
