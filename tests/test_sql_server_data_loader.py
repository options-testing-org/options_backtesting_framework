import datetime

from options_framework.config import settings
from options_framework.data.sql_data_loader import SQLServerDataLoader


def test_database_connection(database_settings_file_name):
    start_date = datetime.datetime.strptime("2016-03-01 09:31:00", "%Y-%m-%d %H:%M:%S")
    end_date = datetime.datetime.strptime("2016-03-31 16:15:00", "%Y-%m-%d %H:%M:%S")
    sql_loader = SQLServerDataLoader(database_settings_file_name, start_date, end_date)
    sql_loader.load_data(quote_datetime=start_date)
    pass