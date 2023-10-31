import datetime
from options_framework.option_types import OptionType
from options_framework.option import Option

ticker = "XYZ"
test_expiration = datetime.datetime.strptime("07-16-2021", "%m-%d-%Y")
test_quote_date = datetime.datetime.strptime("2021-07-01 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
test_update_quote_date = datetime.datetime.strptime("2021-07-02 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
test_update_quote_date2 = datetime.datetime.strptime("2021-07-02 14:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")
standard_fee = 0.50