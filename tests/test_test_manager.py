import datetime
from dataclasses import fields
import dataclasses
from options_framework.test_manager import OptionTestManager
from options_framework.option_types import OptionType, SelectFilter, FilterRange

def test_instantiate_test_manager():
    my_filter = SelectFilter(symbol='SPXW', option_type=OptionType.CALL, strike_range=FilterRange(1000, 2000))
    start_date = datetime.datetime(2016, 3, 1, 9, 31)
    end_date = datetime.datetime(2016, 6, 30, 16, 15)

    test_manager = OptionTestManager(start_date, end_date, my_filter)

    pass