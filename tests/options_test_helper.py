import datetime
from options_framework.option_types import OptionType
from options_framework.option import Option

test_expiration = datetime.datetime.strptime("07-16-2021", "%m-%d-%Y")
test_quote_date = datetime.datetime.strptime("2021-07-01 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
test_update_quote_date = datetime.datetime.strptime("2021-07-02 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
test_update_quote_date2 = datetime.datetime.strptime("2021-07-02 14:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")
test_update_quote_date3 = datetime.datetime.strptime("2021-07-16 11:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")
at_expiration_quote_date = datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f")
standard_fee = 0.50
ticker = "XYZ"

def get_test_call_option():
    _id, strike, spot_price, bid, ask, price = (1, 100.0, 90.0, 1.0, 2.0, 1.5)
    test_option = Option(id, ticker, strike, test_expiration, OptionType.CALL, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price)
    return test_option

def get_test_call_option_update_values_1():
    quote_date, spot_price, bid, ask, price = (test_update_quote_date, 110.0, 9.50, 10.5, 10.00)  # ITM
    return quote_date, spot_price, bid, ask, price

def get_test_call_option_update_values_2():
    quote_date, spot_price, bid, ask, price = (test_update_quote_date2, 105.0, 4.50, 5.5, 5.00)  # ITM
    return quote_date, spot_price, bid, ask, price

def get_test_call_option_update_values_3():
    quote_date, spot_price, bid, ask, price = (test_update_quote_date3, 90.0, 0, .05, 0.03)  # OTM
    return quote_date, spot_price, bid, ask, price

def get_test_call_option_extended_properties():
    _id = 1
    strike = 100
    spot_price, bid, ask, price = (110.0, 1.0, 2.0, 1.5)
    delta, gamma, theta, vega, open_interest, rho, iv = (0.3459, -0.1234, 0.0485, 0.0935, 100, 0.132, 0.3301)
    test_option = Option(id, ticker, strike, test_expiration, OptionType.CALL, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price,
                         delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho, implied_volatility=iv,
                         open_interest=open_interest)
    return test_option

def get_test_put_option():
    _id, strike, spot_price, bid, ask, price = (1, 100.0, 105.0, 1.0, 2.0, 1.5)
    test_option = Option(id, ticker, strike, test_expiration, OptionType.PUT, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price)
    return test_option

def get_test_put_option_update_values_1():
    quote_date, spot_price, bid, ask, price = (test_update_quote_date, 90.0, 9.50, 10.5, 10.00)  # ITM
    return quote_date, spot_price, bid, ask, price

def get_test_put_option_update_values_2():
    quote_date, spot_price, bid, ask, price = (test_update_quote_date2, 95.0, 4.50, 5.5, 5.00)  # ITM
    return quote_date, spot_price, bid, ask, price

def get_test_put_option_update_values_3():
    quote_date, spot_price, bid, ask, price = (test_update_quote_date3, 110.0, 0, .05, 0.03)  # OTM
    return quote_date, spot_price, bid, ask, price

def get_test_put_option_with_extended_properties():
    _id = 1
    strike = 100
    spot_price, bid, ask, price = (105, 1.0, 2.0, 1.5)
    delta, gamma, theta, vega, open_interest, rho, iv = (-0.4492, -0.1045, 0.0412, 0.1143, 900, 0.0282, 0.3347)
    test_option = Option(id, ticker, strike, test_expiration, OptionType.PUT, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price,
                         delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho, implied_volatility=iv,
                         open_interest=open_interest)
    return test_option
