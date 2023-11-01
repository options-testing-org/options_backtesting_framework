import datetime
from options_framework.option_types import OptionType
from options_framework.option import Option

test_expiration = datetime.datetime.strptime("07-16-2021", "%m-%d-%Y")
test_quote_date = datetime.datetime.strptime("2021-07-01 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
test_update_quote_date = datetime.datetime.strptime("2021-07-02 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
test_update_quote_date2 = datetime.datetime.strptime("2021-07-02 14:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")
test_update_quote_date3 = datetime.datetime.strptime("2021-07-16 11:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")
standard_fee = 0.50
ticker = "XYZ"

def get_test_call_option():
    _id = 1
    strike = 100
    spot_price, bid, ask, price = (90, 1.0, 2.0, 1.5)
    test_option = Option(id, ticker, strike, test_expiration, OptionType.CALL, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price)
    return test_option

def get_test_call_option_update_values_1():
    quote_date, spot_price, bid, ask, price = (test_update_quote_date, 110, 9.50, 10.5, 10.00)
    return quote_date, spot_price, bid, ask, price

def get_test_call_option_update_values_2():
    quote_date, spot_price, bid, ask, price = (test_update_quote_date2, 105, 4.50, 5.5, 5.00)
    return quote_date, spot_price, bid, ask, price

def test_call_option_update_3(test_option):
    quote_date, spot_price, bid, ask, price = (test_update_quote_date3, 95, 0, .05, 0.03)
    test_option.update(quote_date, spot_price, bid, ask, price)

def get_test_call_option_extended_properties():
    _id = 1
    strike = 100
    spot_price, bid, ask, price = (110, 1.0, 2.0, 1.5)
    delta, gamma, theta, vega, open_interest, rho, iv = (0.3459, -0.1234, 0.0485, 0.0935, 100, 0.132, 0.3301)
    test_option = Option(id, ticker, strike, test_expiration, OptionType.CALL, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price,
                         delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho, implied_volatility=iv,
                         open_interest=open_interest)
    return test_option

def get_test_put_option():
    _id = 1
    strike = 100
    spot_price, bid, ask, price = (105, 1.0, 2.0, 1.5)
    test_option = Option(id, ticker, strike, test_expiration, OptionType.PUT, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price)
    return test_option

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

def get_4210_put_option():
    _id = 1
    strike = 4210
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4308, 13.8, 14.1, 13.95, -0.2047, 0.0024, -1.1116, 2.5014, 329)
    option = Option(_id, ticker, strike, test_expiration, OptionType.PUT, quote_date=test_quote_date,
                    spot_price=spot_price,
                    bid=bid, ask=ask, price=price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                    open_interest=open_interest, fee=standard_fee)  # trade price = 13.95
    return option


def update_4210_put_option(option):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4330.27, 8.8, 9.1, 8.95, -0.1471, 0.002, -0.9392, 1.9709, 349)  # 8.95
    option.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta,
                  gamma=gamma, theta=theta, vega=vega, open_interest=open_interest)


def get_4220_put_option():
    _id = 2
    strike = 4220
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4308, 14.8, 15.2, 15.00, -0.2224, 0.0026, -1.1275, 2.625, 815)
    option = Option(_id, ticker, strike, test_expiration, OptionType.PUT,
                    quote_date=test_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price,
                    open_interest=open_interest, delta=delta, gamma=gamma, theta=theta,
                    vega=vega, fee=standard_fee)  # trade price = 15.0
    return option


def update_4220_put_option(option):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4330.27, 9.5, 9.8, 9.65, -0.1606, 0.0022, -0.9628, 2.0883, 878)
    option.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                  open_interest=open_interest)  # 9.65

def update_4220_put_option_2(option):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4349.73, 8.30, 8.50, 8.4, -0.1362, 0.0018, -0.9335, 1.8654, 878)
    option.update(test_update_quote_date2, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                  open_interest=open_interest)  # 9.65

def get_4100_put_option():
    _id = 3
    strike = 4100
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4308.00, 6.6, 6.9, 6.75, -0.0899, 0.0010, -0.8469, 1.4294, 1243)
    option = Option(_id, ticker, strike, test_expiration, option_type=OptionType.PUT, quote_date=test_quote_date,
                    spot_price=spot_price, bid=bid, ask=ask, price=price,
                    open_interest=open_interest, delta=delta, gamma=gamma, theta=theta,
                    vega=vega, fee=standard_fee)  # trade price 6.75
    return option

def get_long_4100_put_option():
    put = get_4100_put_option()
    put.open_trade(1)
    return put

def get_short_4100_put_option():
    put = get_4100_put_option()
    put.open_trade(-1)
    return put

def update_4100_put_option(option):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4330.27, 4.1, 4.3, 4.20, -0.0619, 0.0008, -0.6607, 1.0448, 1805)
    option.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                  open_interest=open_interest)  # 4.20


def get_4075_put_option():
    _id = 4
    strike = 4075
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4308.00, 5.7, 6, 5.85, -0.0762, 0.0009, -0.7887, 1.2627, 1825)
    option = Option(_id, ticker, strike, test_expiration, OptionType.PUT, quote_date=test_quote_date,
                    spot_price=spot_price, bid=bid, ask=ask, price=price,
                    open_interest=open_interest, delta=delta, gamma=gamma, theta=theta,
                    vega=vega)  # trade price 5.85
    return option


def update_4075_put_option(option):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4330.27, 3.5, 3.7, 3.60, -0.0519, 0.0007, -0.6052, 0.9094, 1837)
    option.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                  open_interest=open_interest)  # 3.60


def get_4380_call_option():
    _id = 5
    strike = 4380
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4308, 5.4, 5.7, 5.55, 0.1519, 0.0033, -0.545, 2.0717, 391)
    option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, quote_date=test_quote_date,
                    spot_price=spot_price, bid=bid, ask=ask, price=price,
                    open_interest=open_interest, delta=delta, gamma=gamma, theta=theta, vega=vega,
                    fee=standard_fee)  # trade price 5.55
    return option


def update_4380_call_option(option):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4330.27, 8, 8.2, 8.10, 0.2194, 0.0046, -0.6714, 2.5316, 372)
    option.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                  open_interest=open_interest)  # 8.1

def update_4380_call_option_2(option):
    # 2021-07-02 14:31:00.0000000	14.30	14.60	0.0800	0.3260	0.0053	-0.8739	3.0781	54.1393	372	4349.73	14.450000
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4349.73, 14.30, 14.60, 14.45, 0.3260, 0.0053, -0.8739, 3.0781, 372)
    option.update(test_update_quote_date2, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                  open_interest=open_interest)  # 14.45

def get_4390_call_option():
    _id = 6
    strike = 4390
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4308.00, 4.1, 4.3, 4.20, 0.1213, 0.0028, -0.4664, 1.7755, 584)
    option = Option(_id, ticker, strike, test_expiration, option_type=OptionType.CALL,
                    quote_date=test_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price,
                    open_interest=open_interest, delta=delta, gamma=gamma, theta=theta, vega=vega)  # trade price 4.2
    return option


def update_4390_call_option(option):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4330.27, 6, 6.2, 6.10, 0.1762, 0.004, -0.5858, 2.217, 606)
    option.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                  open_interest=open_interest)  # 6.1


def get_4310_call_option():
    _id = 7
    strike = 4310
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4308, 30.6, 31.1, 30.85, 0.4842, 0.0048, -1.073, 3.5121, 508)
    option = Option(_id, ticker, strike, test_expiration, option_type=OptionType.CALL, quote_date=test_quote_date,
                    spot_price=spot_price, bid=bid, ask=ask, price=price,
                    open_interest=open_interest, delta=delta, gamma=gamma, theta=theta, vega=vega)  # trade price 30.85
    return option


def update_4310_call_option(option):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4330.27, 41.5, 41.9, 41.70, 0.5992, 0.0049, -1.0637, 3.3099, 514)
    option.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                  open_interest=open_interest)  # 41.70


def get_4320_call_option():
    _id = 8
    strike = 4320
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4308, 25.1, 25.5, 25.30, 0.4338, 0.0049, -1.0255, 3.4663, 946)
    option = Option(_id, ticker, strike, test_expiration, option_type=OptionType.CALL, quote_date=test_quote_date,
                    spot_price=spot_price, bid=bid, ask=ask, price=price,
                    open_interest=open_interest, delta=delta, gamma=gamma, theta=theta, vega=vega)  # trade price 25.30
    return option


def update_4320_call_option(option):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = (
        4330.27, 34.5, 34.9, 34.70, 0.5511, 0.0053, -1.0423, 3.3881, 917)
    option.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                  open_interest=open_interest)  # 34.70


def get_4300_put_option():
    # spot price = 4352.74
    _id = 9
    strike = 4300
    option_expiration = datetime.datetime.strptime("07-19-2021", "%m-%d-%Y")
    quote_datetime, bid, ask, price, delta, spot_price, implied_volatility, delta, gamma, \
        theta, vega, open_interest = (datetime.datetime.strptime('07/15/2021 14:30:00', '%m/%d/%Y %H:%M:%S'),
                                      6, 6.3, 6.15, -0.1863, 4352.74, 0.1302,
                                      -0.1863, 0.0045, -1.9671, 1.2341, 3870)
    option = Option(_id, ticker, strike, option_expiration, option_type=OptionType.PUT, quote_date=quote_datetime,
                    spot_price=spot_price, bid=bid, ask=ask, price=price,
                    open_interest=open_interest, delta=delta, gamma=gamma, theta=theta, vega=vega,
                    implied_volatility=implied_volatility)  # trade price 3.50
    return option, quote_datetime


def update_4300_put_option_spot_price_up(option):
    # spot price = 4366.44
    bid, ask, price, quote_datetime, underlying_price, delta, gamma, theta, vega, open_interest = \
        (1.9, 2, 1.95, datetime.datetime.strptime('07/16/2021 09:45:00', '%m/%d/%Y %H:%M:%S'),
         4366.44, -0.0865, 0.0032, -1.1723, 0.6524, 4031)
    option.update(quote_datetime, underlying_price, bid, ask, price, delta=delta, gamma=gamma,
                  theta=theta, vega=vega, open_interest=open_interest)


def update_4300_put_option_spot_price_down(option):
    # spot price = 4277.42
    bid, ask, price, quote_datetime, underlying_price, delta, gamma, theta, vega, open_interest = \
        (25.9, 26.4, 26.15, datetime.datetime.strptime('07/19/2021 09:45:00', '%m/%d/%Y %H:%M:%S'),
         4277.42, -0.7511, 0.0101, -17.7459, 0.3764, 5762)
    option.update(quote_datetime, underlying_price, bid, ask, price,
                  delta=delta, gamma=gamma, theta=theta, vega=vega, open_interest=open_interest)


def update_4300_put_option_expiration(option):
    bid, ask, price, quote_datetime, underlying_price, delta, gamma, theta, vega, open_interest = \
        (37, 46.2, 41.6, datetime.datetime.strptime('07/19/2021 16:15:00', '%m/%d/%Y %H:%M:%S'),
         4258.5, -0.9689, 0.0031, -37.7203, 0.0228, 5762)
    option.update(quote_datetime, underlying_price, bid, ask, price, delta=delta,
                  gamma=gamma, theta=theta, vega=vega, open_interest=open_interest)
