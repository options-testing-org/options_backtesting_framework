import datetime

import pandas as pd
import pyodbc

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option_types import OptionType

class SQLServerDataLoader(DataLoader):

    def __init__(self, settings_file: str, *args, **kwargs):
        super().__init__(settings_file, *args, **kwargs)
        self.quote_datetime = None
        server = settings.SERVER
        database = settings.DATABASE
        username = settings.USERNAME
        password = settings.PASSWORD
        self.connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database \
                                 + ';UID=' + username + ';PWD=' + password
        self.options_query = 'select distinct o.id as option_id, symbol, expiration, strike, option_type ' \
                             + 'from options o inner join option_values ov on o.id = ov.option_id ' \
                             + 'where quote_datetime >= CONVERT(datetime2, \'{start_date}\') ' \
                             + 'and quote_datetime <= CONVERT(datetime2, \'{end_date}\')'

        self.connection = pyodbc.connect(self.connection_string)

    def load_data(self, quote_datetime: datetime.datetime, option_type_filter: OptionType = None,
                  range_filters: dict = None, *args, **kwargs):
        self.quote_datetime = quote_datetime
        query = self.options_query.replace('{start_date}', str(quote_datetime)).replace('{end_date}', str(quote_datetime))

        df = pd.read_sql(query, self.connection, index_col='datetime', parse_dates=True)
        pass
