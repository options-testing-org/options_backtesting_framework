import datetime
import pytest
from options_framework.option_types import OptionType
from options_framework.option import Option


@pytest.fixture
def test_expiration():
    return datetime.datetime.strptime("07-16-2021", "%m-%d-%Y")


@pytest.fixture
def test_quote_date():
    return datetime.datetime.strptime("2021-07-01 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")


@pytest.fixture
def test_update_quote_date():
    return datetime.datetime.strptime("2021-07-02 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")


@pytest.fixture
def test_update_quote_date2():
    return datetime.datetime.strptime("2021-07-02 14:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")


@pytest.fixture
def test_update_quote_date3():
    return datetime.datetime.strptime("2021-07-16 11:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")


@pytest.fixture
def at_expiration_quote_date():
    return datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f")


@pytest.fixture
def standard_fee():
    return 0.50


@pytest.fixture
def ticker():
    return "XYZ"


@pytest.fixture
def strike():
    return 100


@pytest.fixture
def option_id():
    return '1'


@pytest.fixture
def get_test_call_option(option_id, test_expiration, test_quote_date, ticker):
    strike, spot_price, bid, ask, price = (100.0, 90.0, 1.0, 2.0, 1.5)
    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.CALL, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price)
    return test_option


@pytest.fixture
def get_test_call_option_update_values_1(test_update_quote_date):
    quote_date, spot_price, bid, ask, price = (test_update_quote_date, 110.0, 9.50, 10.5, 10.00)  # ITM
    return quote_date, spot_price, bid, ask, price


@pytest.fixture
def get_test_call_option_update_values_2(test_update_quote_date2):
    quote_date, spot_price, bid, ask, price = (test_update_quote_date2, 105.0, 4.50, 5.5, 5.00)  # ITM
    return quote_date, spot_price, bid, ask, price


@pytest.fixture
def get_test_call_option_update_values_3(test_update_quote_date3):
    quote_date, spot_price, bid, ask, price = (test_update_quote_date3, 90.0, 0, .05, 0.03)  # OTM
    return quote_date, spot_price, bid, ask, price


@pytest.fixture
def get_test_call_option_extended_properties(option_id, test_expiration, test_quote_date, ticker):
    strike = 100
    spot_price, bid, ask, price = (110.0, 1.0, 2.0, 1.5)
    delta, gamma, theta, vega, open_interest, rho, iv = (0.3459, -0.1234, 0.0485, 0.0935, 100, 0.132, 0.3301)
    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.CALL, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price,
                         delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho, implied_volatility=iv,
                         open_interest=open_interest)
    return test_option


@pytest.fixture
def get_test_put_option(option_id, test_expiration, test_quote_date, ticker):
    strike, spot_price, bid, ask, price = (100.0, 105.0, 1.0, 2.0, 1.5)
    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.PUT, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price)
    return test_option


@pytest.fixture
def get_test_put_option_update_values_1(test_update_quote_date):
    quote_date, spot_price, bid, ask, price = (test_update_quote_date, 90.0, 9.50, 10.5, 10.00)  # ITM
    return quote_date, spot_price, bid, ask, price


@pytest.fixture
def get_test_put_option_update_values_2(test_update_quote_date2):
    quote_date, spot_price, bid, ask, price = (test_update_quote_date2, 95.0, 4.50, 5.5, 5.00)  # ITM
    return quote_date, spot_price, bid, ask, price


@pytest.fixture
def get_test_put_option_update_values_3(test_update_quote_date3):
    quote_date, spot_price, bid, ask, price = (test_update_quote_date3, 110.0, 0, .05, 0.03)  # OTM
    return quote_date, spot_price, bid, ask, price


@pytest.fixture
def get_test_put_option_with_extended_properties(option_id, test_expiration, test_quote_date, ticker):
    strike = 100
    spot_price, bid, ask, price = (105, 1.0, 2.0, 1.5)
    delta, gamma, theta, vega, open_interest, rho, iv = (-0.4492, -0.1045, 0.0412, 0.1143, 900, 0.0282, 0.3347)
    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.PUT, quote_date=test_quote_date,
                         spot_price=spot_price, bid=bid, ask=ask, price=price,
                         delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho, implied_volatility=iv,
                         open_interest=open_interest)
    return test_option


@pytest.fixture
def datafile_settings_file_name():
    return "custom_settings.toml"

@pytest.fixture
def datafile_file_name():
    return "L2_options_20230301.csv"

@pytest.fixture
def database_settings_file_name():
    return ".secrets.toml"
