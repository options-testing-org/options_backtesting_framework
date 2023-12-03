import datetime

from options_framework.test_manager import OptionTestManager
from options_framework.data.data_loader import DataLoader
from options_framework.option_chain import OptionChain

def test_get_sql_data_loader_test_manager():
    start_date = datetime.datetime(2016, 3, 1, 9, 31)
    end_date = datetime.datetime(2016, 5, 30, 16,15)
    symbol = 'SPXW'
    tm = OptionTestManager(start_datetime=start_date, end_datetime=end_date, symbol=symbol)




