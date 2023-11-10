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

# Delta Neutral options file headers
dn_headers = ['AKA', 'UnderlyingSymbol', 'UnderlyingPrice', 'Exchange', 'OptionSymbol', 'OptionExt', 'Type',
              'Expiration', 'DataDate', 'Strike', 'Last', 'Bid', 'Ask', 'Volume', 'OpenInterest', 'IV', 'Delta',
              'Gamma', 'Theta', 'Vega']
# symbol strike, expiration, option_type quote_date, spot_price, bid, ask ' \
#     + 'delta gamma theta vega rho open_interest implied_volatility
# dn_column_map = DataColumnMap(symbol='UnderlyingSymbol', strike='Strike', expiration='Expiration', option_type='Type',
#                               quote_date='DataDate', spot_price='UnderlyingPrice', bid='Bid', ask='Ask', delta='Delta',
#                               gamma='Gamma', theta='Theta', vega='Vega', open_interest='OpenInterest',
#                               implied_volatility='implied_volatility')

# get column indices
# delta_neutral_col_map = DataColumnMap(
#     i_id=dn_headers.index('AKA'),
#     i_symbol=dn_headers.index('UnderlyingSymbol'),
#     i_strike=dn_headers.index('Strike'),
#     i_expiration=dn_headers.index('Expiration'),
#     i_option_type=dn_headers.index('Type'),
#     i_quote_date=dn_headers.index('DataDate'),
#     i_spot_price=dn_headers.index('UnderlyingPrice'),
#     i_bid=dn_headers.index('Bid'),
#     i_ask=dn_headers.index('Ask'),
#     i_delta=dn_headers.index('Delta'),
#     i_gamma=dn_headers.index('Gamma'),
#     i_theta=dn_headers.index('Theta'),
#     i_vega=dn_headers.index('Vega'),
#     i_open_interest=dn_headers.index('OpenInterest'),
#     i_implied_volatility=dn_headers.index('IV'))
# delta_neutral_call_value = 'call'
# delta_negative_put_value = 'put'

# CBOE options file headers
cboe_headers = ['underlying_symbol', 'quote_datetime', 'root', 'expiration', 'strike', 'option_type', 'open', 'high',
                'low', 'close', 'trade_volume', 'bid_size', 'bid', 'ask_size', 'ask', 'underlying_bid',
                'underlying_ask', 'implied_underlying_price', 'active_underlying_price', 'implied_volatility',
                'delta', 'gamma', 'theta', 'vega', 'rho', 'open_interest']

# cboe_column_map = DataColumnMap(symbol='underlying_symbol', strike='strike', expiration='expiration',
#                                 option_type='option_type', quote_date='quote_datetime',
#                                 spot_price='active_underlying_price', bid='bid', ask='ask', delta='delta',
#                                 gamma='gamma', theta='theta', vega='vega', open_interest='open_interest',
#                                 implied_volatility='implied_volatility')
# cboe_col_positions = DataColumnIndexPositions(
#     i_symbol=cboe_headers.index('root'),
#     i_strike=cboe_headers.index('strike'),
#     i_expiration=cboe_headers.index('expiration'),
#     i_option_type=cboe_headers.index('option_type'),
#     i_quote_date=cboe_headers.index('quote_datetime'),
#     i_spot_price=cboe_headers.index('active_underlying_price'),
#     i_bid=cboe_headers.index('bid'),
#     i_ask=cboe_headers.index('ask'),
#     i_delta=cboe_headers.index('delta'),
#     i_gamma=cboe_headers.index('gamma'),
#     i_theta=cboe_headers.index('theta'),
#     i_vega=cboe_headers.index('vega'),
#     i_open_interest=cboe_headers.index('open_interest'),
#     i_implied_volatility=cboe_headers.index('implied_volatility'))
#
# cboe_call_value = 'C'
# cboe_put_value = 'P'


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
