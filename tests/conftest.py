import datetime
import pytest
import pandas as pd
from pandas import DataFrame
import os

os.environ["OPTIONS_FRAMEWORK_CONFIG_FOLDER"] = r'C:\_code\options_backtesting_framework\tests\config'
from mocks import *
from test_data.test_option_daily import daily_test_options, daily_test_df
from pprint import pprint as pp
from test_helpers import get_option_chain_items
from options_framework.config import settings, load_settings


@pytest.fixture
def incur_fees_true():
    original_setting = settings['incur_fees']
    settings['incur_fees'] = True
    yield
    settings['incur_fees'] = original_setting


@pytest.fixture
def incur_fees_false():
    original_setting = settings['incur_fees']
    settings['incur_fees'] = False
    yield
    settings['incur_fees'] = original_setting

@pytest.fixture
def parquet_daily_loader_settings():
    original_settings = settings['data_format_settings']
    data_settings = load_settings("parquet_daily_settings.toml")
    settings['data_settings'] = data_settings
    yield
    data_settings = load_settings(original_settings)
    settings['data_settings'] = data_settings


@pytest.fixture
def parquet_cboe_loader_settings():
    original_settings = settings['data_format_settings']
    data_settings = load_settings("cboe_settings.toml")
    settings['data_settings'] = data_settings
    yield
    data_settings = load_settings(original_settings)
    settings['data_settings'] = data_settings
    pass


@pytest.fixture
def allow_slippage():
    settings.apply_slippage_entry=True
    settings.apply_slippage_exit=True
    yield
    settings.apply_slippage_entry = False
    settings.apply_slippage_exit = False


@pytest.fixture
def option_chain_daily():
    def get_option_chain_daily_for_date(quote_date):
        option_chain = MockOptionChain(symbol='AAPL',
                                   quote_datetime=quote_date)
        options, expirations, expiration_strikes = get_option_chain_items(quote_date, daily_test_df, daily_test_options)
        option_chain.option_chain = options
        option_chain.expirations = expirations
        option_chain.expiration_strikes = expiration_strikes
        return option_chain
    return get_option_chain_daily_for_date



# @pytest.fixture
# def test_expiration():
#     return datetime.date(2021, 7, 16)
#
# @pytest.fixture
# def test_quote_date():
#     return datetime.datetime(2021, 7, 1, 9, 45)
#
# @pytest.fixture
# def test_update_quote_date():
#     return datetime.datetime(2021, 7, 2, 9, 45)
#
# @pytest.fixture
# def test_update_quote_date2():
#     return datetime.datetime(2021, 7, 2, 14, 31)
#
#
# @pytest.fixture
# def test_update_quote_date3():
#     return datetime.datetime(2021, 7, 16, 11, 31)
#
#
# @pytest.fixture
# def at_expiration_quote_date():
#     return datetime.datetime(2021, 7, 16, 16, 15)
#
# @pytest.fixture
# def past_expiration_quote_date():
#     return datetime.datetime(2021, 7, 17, 9, 45)
#
#
# @pytest.fixture
# def standard_fee():
#     return 0.50
#
#
# @pytest.fixture
# def ticker():
#     return "XYZ"
#
#
# @pytest.fixture
# def strike():
#     return 100
#
#
# @pytest.fixture
# def option_id():
#     return '1'
#
#
# @pytest.fixture
# def get_test_call_option(option_id, test_expiration, test_quote_date, ticker):
#     strike, spot_price, bid, ask, price = (100.0, 90.0, 1.0, 2.0, 1.5)
#     test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
#                          option_type=OptionType.CALL, quote_datetime=test_quote_date,
#                          spot_price=spot_price, bid=bid, ask=ask, price=price)
#     return test_option
#
#
# @pytest.fixture
# def get_test_call_option_update_values_1(test_update_quote_date):
#     quote_date, spot_price, bid, ask, price = (test_update_quote_date, 110.0, 9.50, 10.5, 10.00)  # ITM
#     return quote_date, spot_price, bid, ask, price
#
#
# @pytest.fixture
# def get_test_call_option_update_values_2(test_update_quote_date2):
#     quote_date, spot_price, bid, ask, price = (test_update_quote_date2, 105.0, 4.50, 5.5, 5.00)  # ITM
#     return quote_date, spot_price, bid, ask, price
#
#
# @pytest.fixture
# def get_test_call_option_update_values_3(test_update_quote_date3):
#     quote_date, spot_price, bid, ask, price = (test_update_quote_date3, 90.0, 0, .05, 0.03)  # OTM
#     return quote_date, spot_price, bid, ask, price
#
#
# @pytest.fixture
# def get_test_call_option_extended_properties(option_id, test_expiration, test_quote_date, ticker):
#     strike = 100
#     spot_price, bid, ask, price = (110.0, 1.0, 2.0, 1.5)
#     delta, gamma, theta, vega, open_interest, rho, iv = (0.3459, -0.1234, 0.0485, 0.0935, 100, 0.132, 0.3301)
#     test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
#                          option_type=OptionType.CALL, quote_datetime=test_quote_date,
#                          spot_price=spot_price, bid=bid, ask=ask, price=price,
#                          delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho, implied_volatility=iv,
#                          open_interest=open_interest)
#     return test_option
#
#
# @pytest.fixture
# def get_test_put_option(option_id, test_expiration, test_quote_date, ticker):
#     strike, spot_price, bid, ask, price = (100.0, 105.0, 1.0, 2.0, 1.5)
#     test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
#                          option_type=OptionType.PUT, quote_datetime=test_quote_date,
#                          spot_price=spot_price, bid=bid, ask=ask, price=price)
#     return test_option
#
#
# @pytest.fixture
# def get_test_put_option_update_values_1(test_update_quote_date):
#     quote_date, spot_price, bid, ask, price = (test_update_quote_date, 90.0, 9.50, 10.5, 10.00)  # ITM
#     return quote_date, spot_price, bid, ask, price
#
#
# @pytest.fixture
# def get_test_put_option_update_values_2(test_update_quote_date2):
#     quote_date, spot_price, bid, ask, price = (test_update_quote_date2, 95.0, 4.50, 5.5, 5.00)  # ITM
#     return quote_date, spot_price, bid, ask, price
#
#
# @pytest.fixture
# def get_test_put_option_update_values_3(test_update_quote_date3):
#     quote_date, spot_price, bid, ask, price = (test_update_quote_date3, 110.0, 0, .05, 0.03)  # OTM
#     return quote_date, spot_price, bid, ask, price
#
#
# @pytest.fixture
# def get_test_put_option_with_extended_properties(option_id, test_expiration, test_quote_date, ticker):
#     strike = 100
#     spot_price, bid, ask, price = (105, 1.0, 2.0, 1.5)
#     delta, gamma, theta, vega, open_interest, rho, iv = (-0.4492, -0.1045, 0.0412, 0.1143, 900, 0.0282, 0.3347)
#     test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
#                          option_type=OptionType.PUT, quote_datetime=test_quote_date,
#                          spot_price=spot_price, bid=bid, ask=ask, price=price,
#                          delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho, implied_volatility=iv,
#                          open_interest=open_interest)
#     return test_option
#
#
# @pytest.fixture
# def datafile_file_name():
#     return "L2_options_20230301.csv"

def dump(o):
    #datetime.date(2016, 3, 2)
    op_inst = f'Option(option_id={o.option_id}, symbol=\'{o.symbol}\', '
    op_inst += f'expiration=datetime.date({o.expiration.year}, {o.expiration.month}, {o.expiration.day}), strike={o.strike},'
    op_inst += f'option_type={o.option_type}, quote_datetime=datetime.datetime({o.quote_datetime.year}, '
    op_inst += f'{o.quote_datetime.month}, {o.quote_datetime.day}, {o.quote_datetime.hour}, {o.quote_datetime.minute}),'
    op_inst += f'spot_price={o.spot_price},'
    op_inst += f'bid={o.bid}, ask={o.ask}, price={o.price}, delta={o.delta}, gamma={o.gamma}, theta={o.theta},'
    op_inst += f'vega={o.vega}, rho={o.rho}, open_interest={o.open_interest}, implied_volatility={o.implied_volatility}),'
    print('    ', op_inst)

#@pytest.fixture()
# def spx_option_chain():
#     from options_framework.config import settings
#     original_value_1 = settings.DATA_LOADER_TYPE
#     settings.DATA_LOADER_TYPE = "SQL_DATA_LOADER"
#     settings.DATA_FORMAT_SETTINGS = 'sql_server_cboe_settings.toml'
#     start_date = datetime.datetime(2016, 3, 1, 9, 31)
#     end_date = datetime.datetime(2016, 3, 2, 16, 15)
#     select_filter = SelectFilter(symbol="SPXW",
#                                  expiration_dte=FilterRange(high=3),
#                                  strike_offset=FilterRange(low=50, high=50))
#     data_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter,
#                                       extended_option_attributes=['delta','gamma','theta','vega','rho','open_interest','implied_volatility'])
#     data_loader.load_cache(start_date)
#     option_chain = OptionChain()
#     data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
#     quote_datetime = datetime.datetime(2016, 3, 1, 9, 31)
#     data_loader.get_option_chain(quote_datetime=quote_datetime)
#     yield option_chain, data_loader
#     settings.DATA_LOADER_TYPE = original_value_1

#
#
# @pytest.fixture()
# def spx_option_chain_puts():
#     from options_framework.config import settings
#     original_value_1 = settings.DATA_LOADER_TYPE
#     settings.DATA_LOADER_TYPE = "SQL_DATA_LOADER"
#     settings.DATA_FORMAT_SETTINGS = 'sql_server_cboe_settings.toml'
#     start_date = datetime.datetime(2016, 3, 1, 9, 31)
#     end_date = datetime.datetime(2016, 3, 1, 9, 32)
#     select_filter = SelectFilter(symbol="SPXW", option_type=OptionType.PUT,
#                                  expiration_dte=FilterRange(0, 31),
#                                  strike_offset=FilterRange(low=100, high=100))
#     data_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
#     data_loader.load_cache(start_date)
#     option_chain = OptionChain()
#     data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
#     quote_datetime = datetime.datetime(2016, 3, 1, 9, 31)
#     data_loader.get_option_chain(quote_datetime=quote_datetime)
#     yield option_chain, data_loader
#     settings.DATA_LOADER_TYPE = original_value_1
#
# @pytest.fixture()
# def spx_option_chain_calls():
#     from options_framework.config import settings
#     original_value_1 = settings.DATA_LOADER_TYPE
#     settings.DATA_LOADER_TYPE = "SQL_DATA_LOADER"
#     settings.DATA_FORMAT_SETTINGS = 'sql_server_cboe_settings.toml'
#     start_date = datetime.datetime(2016, 3, 1, 9, 31)
#     end_date = datetime.datetime(2016, 3, 1, 9, 35)
#     select_filter = SelectFilter(symbol="SPXW", option_type=OptionType.CALL,
#                                  expiration_dte=FilterRange(0, 31),
#                                  strike_offset=FilterRange(low=100, high=100))
#     data_loader = SQLServerDataLoader(start=start_date, end=end_date, select_filter=select_filter)
#     data_loader.load_cache(start_date)
#     option_chain = OptionChain()
#     data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
#     quote_datetime = datetime.datetime(2016, 3, 1, 9, 31)
#     data_loader.get_option_chain(quote_datetime=quote_datetime)
#     yield option_chain, data_loader
#     settings.DATA_LOADER_TYPE = original_value_1

def create_update_cache(update_values: list): # quote_date, spot_price, bid, ask, price
    updates = []
    for item in update_values:
        val_dict = {'quote_datetime': item[0], 'spot_price': item[1], 'bid': item[2], 'ask': item[3], 'price': item[4]}
        updates.append(val_dict)

    df = DataFrame(updates)
    df['quote_datetime'] = pd.to_datetime(df['quote_datetime'])
    df.set_index("quote_datetime", inplace=True)
    return df
