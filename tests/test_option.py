import pytest

from options_framework.option_types import OptionPositionType
import options_framework.option as option
from options_test_helper import *

# Test initialization
def test_option_init_with_only_option_contract_parameters():
    _id = 1
    strike = 4305
    test_option = Option(_id, ticker, strike, test_expiration, OptionType.CALL)

    option_contract = test_option.option_contract
    option_quote = test_option.option_quote
    greeks = test_option.greeks

    assert option_contract.option_id == _id
    assert option_contract.symbol == ticker
    assert option_contract.strike == strike
    assert option_contract.expiration == test_expiration

    assert option_quote is None
    assert test_option.extended_properties is None
    assert greeks is None
    assert test_option.quantity == 0


def test_option_init_with_quote_data():
    _id = 1
    strike = 4305
    bid, ask, price, spot_price = (32.7, 33.2, 32.95, 4308)
    test_option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, test_quote_date, spot_price, bid, ask, price)

    option_quote = test_option.option_quote

    assert option_quote.bid == bid
    assert option_quote.ask == ask
    assert option_quote.price == price
    assert option_quote.quote_date == test_quote_date


def test_option_init_with_extended_properties():
    bid, ask, price, delta, spot_price, iv, gamma, theta, vega, open_interest, rho = (32.7, 33.2, 32.95,
                                                                                      -0.4916, 4308, 0.0951, 0.0048,
                                                                                      -1.0935, 3.5141, 24, -90.0008)
    _id = 1
    strike = 4305
    fee = 0.5

    test_option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, test_quote_date, spot_price, bid, ask, price,
                       open_interest=open_interest, implied_volatility=iv, delta=delta, gamma=gamma,
                       theta=theta, vega=vega, rho=rho, fee=fee)

    option_contract = test_option.option_contract
    option_quote = test_option.option_quote
    greeks = test_option.greeks
    extended_properties = test_option.extended_properties

    assert option_contract.option_id == _id
    assert option_contract.symbol == ticker
    assert option_contract.strike == strike
    assert option_contract.expiration == test_expiration
    assert option_quote.bid == bid
    assert option_quote.ask == ask
    assert option_quote.price == price
    assert option_quote.quote_date == test_quote_date

    assert greeks.delta == delta
    assert greeks.gamma == gamma
    assert greeks.theta == theta
    assert greeks.vega == vega
    assert greeks.rho == rho

    assert extended_properties.implied_volatility == iv
    assert extended_properties.open_interest == open_interest

    assert test_option._fee == fee

def test_option_init_with_user_defined_attributes():
    _id = 1
    strike = 4305
    test_value = 'test value'

    bid, ask, price, delta, spot_price, iv, gamma, theta, vega, open_interest, rho = (32.7, 33.2, 32.95,
                                                                                      -0.4916, 4308, 0.0951, 0.0048,
                                                                                      -1.0935, 3.5141, 24, -90.0008)

    test_option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, test_quote_date, spot_price, bid, ask, price,
                    open_interest=open_interest, iv=iv, delta=delta, gamma=gamma,
                    theta=theta, vega=vega, rho=rho, user_defined=test_value)

    assert test_option.user_defined == test_value

def test_option_init_raises_exception_if_missing_required_fields():
    # missing id
    _id = None
    with pytest.raises(ValueError, match="option_id is required"):
        Option(option_id=_id, symbol="XYZ", strike=4305, expiration=test_expiration, option_type=OptionType.CALL)

    # missing ticker symbol
    _id = 1
    symbol = None
    with pytest.raises(ValueError, match="symbol is required"):
        Option(option_id=_id, symbol=symbol, strike=4305, expiration=test_expiration, option_type=OptionType.CALL)

    # missing strike
    strike = None
    with pytest.raises(ValueError, match="strike is required"):
        Option(option_id=_id, symbol="XYZ", strike=strike, expiration=test_expiration, option_type=OptionType.CALL)

    # missing expiration
    expiration = None
    with pytest.raises(ValueError, match="expiration is required"):
        Option(option_id=_id, symbol="XYZ", strike=4305, expiration=expiration, option_type=OptionType.CALL)

    # missing option type
    option_type = None
    with pytest.raises(ValueError, match="option_type is required"):
        Option(option_id=_id, symbol="XYZ", strike=4305, expiration=test_expiration, option_type=option_type)


def test_option_init_raises_exception_if_quote_date_is_greater_than_expiration():
    bad_open_date = datetime.datetime.strptime("2021-07-17 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    strike = 4380
    spot_price, bid, ask, price = (4308, 5.4, 5.7, 5.55)
    with pytest.raises(Exception, match="Cannot create an option with a quote date past its expiration date"):
        Option(id, ticker, strike, test_expiration, OptionType.CALL, quote_date=bad_open_date,
               spot_price=spot_price, bid=bid, ask=ask, price=price)

# repr tests
def test_call_option_string_representation():
    call = get_4380_call_option()
    expected_call_repr = '<CALL SPXW 4380 2021-07-16>'
    call_repr = str(call)

    assert call_repr == expected_call_repr

def test_put_option_string_representation():
    put = get_4210_put_option()
    expected_put_repr = '<PUT SPXW 4210 2021-07-16>'
    put_repr = str(put)

    assert put_repr == expected_put_repr

# update tests
def test_update_sets_correct_values():
    call = get_4390_call_option()

    # get updated values for 7/2/2021
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4330.27, 6, 6.2, 6.10, 0.1762, 0.004, -0.5858, 2.217, 606)
    test_value = 'test value'
    call.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                open_interest=open_interest, user_defined=test_value)

    expected_price = 6.1
    actual_price = call.option_quote.price
    assert actual_price == expected_price
    assert call.greeks.delta == 0.1762
    assert call.greeks.gamma == 0.004
    assert call.greeks.theta == -0.5858
    assert call.greeks.vega == 2.217
    assert call.extended_properties.open_interest == 606
    assert call.option_quote.spot_price == 4330.27
    assert call.option_quote.quote_date == test_update_quote_date
    assert call.user_defined == test_value

def test_update_raises_exception_if_missing_required_fields():
    call = get_4390_call_option()

    # quote_date
    quote_date = None
    with pytest.raises(ValueError, match="quote_date is required"):
        call.update(quote_date=quote_date, spot_price=4330, bid=6, ask=6.2, price=6.10)

    # spot price
    spot_price = None
    with pytest.raises(ValueError, match="spot_price is required"):
        call.update(quote_date=test_update_quote_date, spot_price=spot_price, bid=6, ask=6.2, price=6.10)

    # bid
    bid = None
    with pytest.raises(ValueError, match="bid is required"):
        call.update(quote_date=test_update_quote_date, spot_price=4330, bid=bid, ask=6.2, price=6.10)

    # ask
    ask = None
    with pytest.raises(ValueError, match="ask is required"):
        call.update(quote_date=test_update_quote_date, spot_price=4330, bid=6, ask=ask, price=6.10)

    # price
    price = None
    with pytest.raises(ValueError, match="price is required"):
        call.update(quote_date=test_update_quote_date, spot_price=4330, bid=6, ask=6.2, price=price)

def test_update_raises_exception_if_quote_date_is_greater_than_expiration():
    bad_quote_date = datetime.datetime.strptime("2021-07-17 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    put = get_4210_put_option()
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4330.27, 8.8, 9.1, 8.95, -0.1471, 0.002, -0.9392, 1.9709, 349)
    with pytest.raises(Exception, match="Cannot update to a date past the option expiration"):
        put.update(bad_quote_date, spot_price, bid, ask, price, delta=delta,
                  gamma=gamma, theta=theta, vega=vega, open_interest=open_interest)


# open trade
def test_open_trade_sets_correct_values():
    call = get_4390_call_option()
    quantity = 10

    premium = call.open_trade(quantity, spot_price=4308.00)
    trade_open_info = call.get_trade_open_info()
    assert trade_open_info.date == test_quote_date
    assert trade_open_info.quantity == 10
    assert trade_open_info.price == 4.20
    assert trade_open_info.premium == 4200
    assert premium == 4200
    assert call.quantity == 10

    # kwargs were set as attributes
    assert call.spot_price == 4308.00

def test_option_that_is_not_open_has_none_position_type():
    call = get_4380_call_option()
    assert call.position_type is None

@pytest.mark.parametrize("quantity, position_type", [(10, OptionPositionType.LONG), (-10, OptionPositionType.SHORT)])
def test_open_trade_has_correct_position_type(quantity, position_type):
    call = get_4380_call_option()
    call.open_trade(quantity)

    assert call.position_type == position_type

@pytest.mark.parametrize("quantity, expected_premium", [(10, 5_550), (1, 555), (-10, -5_550)])
def test_open_trade_returns_correct_open_value(quantity, expected_premium):
    call = get_4380_call_option()
    premium = call.open_trade(quantity)
    assert premium == expected_premium

@pytest.mark.parametrize("quantity, incur_fees_flag, expected_fees", [(10, True, 5.0), (2, True, 1.0), (-3, True, 1.5),
                                                                      (10, False, 0.0), (2, False, 0.0), (-3, False, 0.0)])
def test_open_trade_sets_total_fees_when_incur_fees_flag_is_true(quantity, incur_fees_flag, expected_fees):
    call = get_4380_call_option()
    call.open_trade(quantity=quantity, incur_fees=incur_fees_flag)

    assert call.total_fees == expected_fees

def test_open_trade_when_there_is_no_quote_data_raises_exception():
    _id = 6
    strike = 4390
    test_option = Option(_id, ticker, strike, test_expiration, option_type=OptionType.CALL)
    quantity = 10
    with pytest.raises(ValueError, match="Cannot open a position that does not have price data"):
        test_option.open_trade(quantity)

def test_open_trade_with_invalid_quantity_raises_exception():
    call = get_4390_call_option()

    # quantity is None
    quantity = None
    with pytest.raises(ValueError, match="Quantity must be a non-zero integer."):
        call.open_trade(quantity)

    # quantity is not an integer
    quantity = 1.5
    with pytest.raises(ValueError, match="Quantity must be a non-zero integer."):
        call.open_trade(quantity)

    # quantity is zero
    quantity = 0
    with pytest.raises(ValueError, match="Quantity must be a non-zero integer."):
        call.open_trade(quantity)

def test_open_trade_when_trade_is_already_open_raises_exception():
    call = get_4390_call_option()
    quantity = 10
    call.open_trade(quantity)

    with pytest.raises(ValueError, match="Cannot open position. A position is already open."):
        call.open_trade(quantity)


# close trade tests
def test_close_trade_closes_entire_position_with_default_values():
    call = get_4390_call_option()
    quantity = 10
    call.open_trade(quantity)

    call.close_trade()  # Missing or none quantity closes entire position

    assert call.quantity == 0

def test_close_partial_trade():
    call = get_4390_call_option()
    quantity = 10
    call.open_trade(quantity)

    close_quantity = 2
    call.close_trade(quantity=close_quantity)  # Missing or none quantity closes entire position

    assert call.quantity == 8

@pytest.mark.parametrize("open_qty, close1_qty, close2_qty, expected_qty", [(10, 2, 8, 0), (10, 2, 3, 5),
                                                                            (-10, 2, 8, 0), (-10, 2, 3, -5)])
def test_close_trade_with_multiple_partial_close(open_qty, close1_qty, close2_qty, expected_qty):
    call = get_4380_call_option()
    quantity = open_qty
    call.open_trade(quantity)
    update_4380_call_option(call)

    # close half of contracts
    call.close_trade(quantity=close1_qty)

    update_4380_call_option_2(call)

    call.close_trade(quantity=close2_qty)

    assert call.quantity == expected_qty

@pytest.mark.parametrize("open_quantity, close_quantity", [(10, 12), (-10, -12)])
def test_close_trade_with_greater_than_quantity_open_raises_exception(open_quantity, close_quantity):
    call = get_4380_call_option()
    call.open_trade(open_quantity)
    update_4380_call_option(call)

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        call.close_trade(close_quantity)

@pytest.mark.parametrize("quantity", [10, -10])
def test_close_partial_trade_with_greater_than_remaining_quantity_raises_exception(quantity):
    call = get_4380_call_option()
    call.open_trade(quantity)
    update_4380_call_option(call)
    call.close_trade(quantity=2)  # close partial trade
    update_4380_call_option_2(call)

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        call.close_trade(quantity)

@pytest.mark.parametrize("incur_fees_flag, open_quantity, close_quantity, fee_amount", [(True, 10, 10, 5.0),
                                                                    (True, -10, 10, 5.0), (True, 10, 2, 1.0),
                                                                    (False, 10, 10, 0.0), (False, -10, 10, 0.0),
                                                                                        (False, -10, 2, 0.0)])
def test_close_trade_updates_total_fees_incur_fees_flag(incur_fees_flag, open_quantity, close_quantity, fee_amount):
    call = get_4380_call_option()
    call.open_trade(open_quantity, incur_fees=False)  # do not incur fees on open
    assert call.total_fees == 0.0

    call.close_trade(quantity=close_quantity, incur_fees=incur_fees_flag)  # default incur fees flag is true

    assert call.total_fees == fee_amount

@pytest.mark.parametrize("open_qty, close_qty, close_date, close_price, close_prem, close_pnl, close_fees, remaining_qty",
                         [(10, 10, test_update_quote_date, 8.1, 8_100.0, 2_550.0, 5, 0),
                          (-10, 10, test_update_quote_date, 8.1, -8_100, -2_550, 5, 0),
                          (10, 1, test_update_quote_date, 8.1, 810.0, 255.0, 0.5, 9),
                          (-10, 5, test_update_quote_date, 8.1, -4_050.0, -1_275.0, 2.5, -5)])
def test_close_trade_values_with_one_close_trade(open_qty, close_qty, close_date, close_price,
                                                 close_prem, close_pnl, close_fees, remaining_qty):
    call = get_4380_call_option()
    call.open_trade(open_qty)
    update_4380_call_option(call)

    prem = call.close_trade(quantity=close_qty)
    assert prem == close_prem

    trade_close_info = call.get_trade_close_info()
    assert trade_close_info.date == close_date
    assert trade_close_info.quantity == close_qty if open_qty < 0 else close_qty*-1
    assert trade_close_info.price == close_price
    assert trade_close_info.premium == close_prem
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.fees == close_fees

    assert call.quantity == remaining_qty

@pytest.mark.parametrize("open_qty, close_qty, close_date, close_price, close_prem, close_pnl, close_fees, remaining_qty",
                         [(10, 2, test_update_quote_date2, 11.91, 5_955.0, 3_180.0, 2.5, 5),
                          (-10, 3, test_update_quote_date2, 11.73, -8_210.0, -4_325, 3.5, -3),
                          (10, 1, test_update_quote_date2, 12.33, 3_700.0, 2_035.0, 1.5, 7),
                          (-10, 4, test_update_quote_date2, 11.63, -10_465.0, -5_470.0, 4.5, -1)])
def test_close_trade_values_with_multiple_close_trades(open_qty, close_qty, close_date, close_price, close_prem,
                                                       close_pnl, close_fees, remaining_qty):
    call = get_4380_call_option()
    call.open_trade(open_qty)
    update_4380_call_option(call)

    call.close_trade(quantity=close_qty)
    update_4380_call_option_2(call)
    call.close_trade(quantity=close_qty+1)

    trade_close_info = call.get_trade_close_info()

    assert trade_close_info.date == close_date

    assert trade_close_info.price == close_price
    assert trade_close_info.premium == close_prem
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.fees == close_fees

    assert trade_close_info.quantity == (open_qty - remaining_qty)*-1
    assert call.quantity == remaining_qty


def test_trade_close_records_returns_all_close_trades():
    call = get_4380_call_option()
    call.open_trade(10)
    update_4380_call_option(call)

    call.close_trade(quantity=1)

    records = call.trade_close_records
    assert len(records) == 1

    update_4380_call_option_2(call)
    call.close_trade(quantity=1)

    records = call.trade_close_records
    assert len(records) == 2

def test_total_fees_returns_all_fees_incurred():
    # standard fee is 0.50 per contract
    call = get_4380_call_option()
    call.open_trade(10)

    assert call.total_fees == 5.0

    update_4380_call_option(call)
    call.close_trade(quantity=2)

    assert call.total_fees == 6.0

    update_4380_call_option_2(call)
    call.close_trade(quantity=3)

    assert call.total_fees == 7.5

def test_get_closing_price():
    call = get_4320_call_option()
    call.open_trade(1)
    update_4320_call_option(call)
    expected_close_price = 34.70

    close_price = call.get_closing_price()

    assert close_price == expected_close_price

def test_get_close_price_on_option_that_has_not_been_traded_raises_exception():
    call = get_4320_call_option()
    update_4320_call_option(call)

    with pytest.raises(ValueError, match="Cannot determine closing price on option that does not have an opening trade"):
        call.get_closing_price()

@pytest.mark.parametrize("open_quantity, bid, ask, price, expected_closing_price",
                         [(10, 0.0, 0.10, 0.05, 0.0), (-10, 0.0, 0.10, 0.05, 0.10)])
def test_get_closing_price_on_call_option_when_bid_is_zero(open_quantity, bid, ask, price, expected_closing_price):
    call = get_4380_call_option()
    call.open_trade(open_quantity)

    spot_price, bid, ask, price = (4330.27, bid, ask, price)
    call.update(test_update_quote_date, spot_price, bid, ask, price)

    assert call.get_closing_price() == expected_closing_price

@pytest.mark.parametrize("open_quantity, bid, ask, price, expected_closing_price",
                         [(10, 0.0, 0.10, 0.05, 0.0), (-10, 0.0, 0.10, 0.05, 0.10)])
def test_get_closing_price_on_put_option_when_bid_is_zero(open_quantity, bid, ask, price, expected_closing_price):
    short_call = get_4210_put_option()

    short_call.open_trade(open_quantity)
    spot_price, bid, ask, price = (4297.79, bid, ask, price)
    short_call.update(test_update_quote_date, spot_price, bid, ask, price)

    assert short_call.get_closing_price() == expected_closing_price


def test_get_close_price_is_zero_when_option_expires_otm():
    expiration_quote_date = datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    call = get_4320_call_option()
    call.open_trade(1)
    spot_price, bid, ask, price = (4308, 32.7, 33.2, 32.95)
    call.update(expiration_quote_date, spot_price, bid, ask, price)
    # 4308 < 4320, so this option expires OTM
    assert call.get_closing_price() == 0.0

    put = get_4075_put_option()
    put.open_trade(1)
    spot_price, bid, ask, price = (4076, 5.7, 6, 5.85)
    put.update(expiration_quote_date, spot_price, bid, ask, price)
    # 4076 > 4075, so this option expires OTM
    assert put.get_closing_price() == 0.0

def test_dte_is_none_when_option_does_not_have_quote_data():
    _id = 1
    strike = 4210
    test_option = Option(_id, 'SPXW', strike, test_expiration, OptionType.CALL)

    assert test_option.dte() is None

def test_dte_when_option_has_quote_data():
    put = get_4210_put_option()

    expected_dte = 15
    actual_dte = put.dte()
    assert actual_dte == expected_dte

def test_dte_is_updated_when_quote_date_is_updated():
    call = get_4390_call_option()

    # get updated values for 7/2/2021
    spot_price, bid, ask, price = \
        (4330.27, 6, 6.2, 6.10)
    call.update(test_update_quote_date, spot_price, bid, ask, price)
    expected_dte = 14
    assert call.dte() == expected_dte

@pytest.mark.parametrize("expiration_datetime",
            [datetime.datetime.strptime("2021-07-16 09:31:00.000000", "%Y-%m-%d %H:%M:%S.%f"),
             datetime.datetime.strptime("2021-07-16 11:00:00.000000", "%Y-%m-%d %H:%M:%S.%f"),
             datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f")])
def test_dte_is_zero_on_expiration_day(expiration_datetime):
    call = get_4390_call_option()
    spot_price, bid, ask, price = \
        (4330.27, 6, 6.2, 6.10)
    call.update(expiration_datetime, spot_price, bid, ask, price)
    expected_dte = 0
    assert call.dte() == expected_dte

def test_otm_and_itm_equal_none_when_option_does_not_have_quote_data():
    _id = 1
    strike = 4210

    test_option = Option(_id, 'SPXW', strike, test_expiration, OptionType.CALL)

    assert test_option.itm() is None
    assert test_option.otm() is None

@pytest.mark.parametrize("spot_price, strike, expected_value", [(4140.0, 4140.0, False),
                                                                   (4140.0, 4120.0, False),
                                                                   (4140.0, 4150.0, True)])
def test_call_option_otm(spot_price, strike, expected_value):
    _id = 1
    test_option = Option(_id, ticker, strike, test_expiration, option_type=OptionType.CALL)
    test_option.update(test_update_quote_date, spot_price, 4.1, 4.3, 4.20)

    actual_value = test_option.otm()
    assert actual_value == expected_value

@pytest.mark.parametrize("spot_price, strike, expected_value", [(4140.0, 4140.0, False),
                                                                   (4140.0, 4120.0, True),
                                                                   (4140.0, 4150.0, False)])
def test_put_option_otm(spot_price, strike, expected_value):
    _id = 1
    test_option = Option(_id, ticker, strike, test_expiration, option_type=OptionType.PUT)
    test_option.update(test_update_quote_date, spot_price, 4.1, 4.3, 4.20)

    actual_value = test_option.otm()
    assert actual_value == expected_value

@pytest.mark.parametrize("spot_price, strike, expected_value", [(4140.0, 4140.0, True),
                                                                   (4140.0, 4120.0, True),
                                                                   (4140.0, 4150.0, False)])
def test_call_option_itm(spot_price, strike, expected_value):
    _id = 1
    test_option = Option(_id, ticker, strike, test_expiration, option_type=OptionType.CALL)
    test_option.update(test_update_quote_date, spot_price, 4.1, 4.3, 4.20)

    actual_value = test_option.itm()
    assert actual_value == expected_value

@pytest.mark.parametrize("spot_price, strike, expected_value", [(4140.0, 4140.0, True),
                                                                   (4140.0, 4120.0, False),
                                                                   (4140.0, 4150.0, True)])
def test_put_option_itm(spot_price, strike, expected_value):
    _id = 1
    test_option = Option(_id, ticker, strike, test_expiration, option_type=OptionType.PUT)
    test_option.update(test_update_quote_date, spot_price, 4.1, 4.3, 4.20)

    actual_value = test_option.itm()
    assert actual_value == expected_value

def test_is_expired_returns_none_when_no_quote_data():
    _id = 1
    test_option = Option(_id, ticker, 1000.0, test_expiration, option_type=OptionType.PUT)

    assert test_option.is_expired() is None

@pytest.mark.parametrize("expiration_date_test, quote_date, expected_result", [
    (datetime.datetime.strptime("07-16-2021", "%m-%d-%Y"),
     datetime.datetime.strptime("2021-07-01 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f"), False),
    (datetime.datetime.strptime("06-30-2021", "%m-%d-%Y"),
     datetime.datetime.strptime("2021-07-01 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f"), True),
    (datetime.datetime.strptime("07-16-2021", "%m-%d-%Y"),
     datetime.datetime.strptime("2021-07-16 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f"), False),
    (datetime.datetime.strptime("07-16-2021", "%m-%d-%Y"),
     datetime.datetime.strptime("2021-07-16 16:14:00.000000", "%Y-%m-%d %H:%M:%S.%f"), False),
    (datetime.datetime.strptime("07-16-2021", "%m-%d-%Y"),
     datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f"), True),
    (datetime.datetime.strptime("07-16-2021", "%m-%d-%Y"),
     datetime.datetime.strptime("2021-07-16", "%Y-%m-%d"), False),
    (datetime.datetime.strptime("07-16-2021", "%m-%d-%Y"),
     datetime.datetime.strptime("2021-07-17", "%Y-%m-%d"), True)])
def test_is_expired_returns_correct_result(expiration_date_test, quote_date, expected_result):
    _id = 1
    put_option = Option(_id, ticker, 1000.0, expiration_date_test, option_type=OptionType.PUT)
    # cheat on setting quote data
    put_option._option_quote = option.OptionQuote(quote_date=quote_date, spot_price=1000.0, bid=4.1, ask=4.2, price=4.3)
    actual_result = put_option.is_expired()

    assert actual_result == expected_result

def test_is_trade_open_returns_false_if_no_trade_was_opened():
    call = get_4390_call_option()
    expected_result = False
    assert call.is_trade_open() == expected_result


def test_is_trade_open_returns_true_if_trade_was_opened():
    call = get_4390_call_option()
    call.open_trade(10)
    expected_result = True

    assert call.is_trade_open() == expected_result

def test_is_trade_open_returns_true_if_trade_was_opened_and_partially_closed():
    call = get_4390_call_option()
    call.open_trade(10)
    call.close_trade(5)
    expected_result = True

    assert call.is_trade_open() == expected_result

def test_is_trade_open_returns_false_if_trade_was_opened_and_then_closed():
    call = get_4390_call_option()
    call.open_trade(10)
    call.close_trade(10)
    expected_result = False

    assert call.is_trade_open() == expected_result

def test_get_profit_loss_raises_exception_if_trade_was_not_opened():
    call = get_4380_call_option()

    with pytest.raises(Exception, match="No trade has been opened."):
        call.get_profit_loss()

def test_get_profit_loss_is_zero_if_quote_data_is_not_updated():
    call = get_4380_call_option()
    call.open_trade(10)

    assert call.get_profit_loss() == 0.0

def test_get_profit_loss_is_zero_when_no_contracts_are_open():
    call = get_4380_call_option()
    call.open_trade(10)
    update_4380_call_option(call)
    call.close_trade(10)

    assert call.get_profit_loss() == 0.0

@pytest.mark.parametrize("test_option, quantity, spot_price, bid, ask, price, expected_profit_loss", [
    (get_4380_call_option(), 10, 4330.27, 8, 8.2, 8.10, 2_550.0),
    (get_4380_call_option(), 10, 4349.73, 14.30, 14.60, 14.45, 8_900.0),
    (get_4380_call_option(), 10, 4320.22, 5.4, 5.7, 5.55, 0.0),
    (get_4380_call_option(), -10, 4330.27, 8, 8.2, 8.10, -2_550.0),
    (get_4380_call_option(), -10, 4349.73, 14.30, 14.60, 14.45, -8_900.0),
    (get_4380_call_option(), -10, 4320.22, 5.4, 5.7, 5.55, 0.0),
    (get_4220_put_option(), 10, 4330.27, 9.5, 9.8, 9.65, -5_350.0),
    (get_4220_put_option(), 10, 4349.73, 8.30, 8.50, 8.4, -6_600.0),
    (get_4220_put_option(), 10, 4308, 14.8, 15.2, 15.00, 0.0),
    (get_4220_put_option(), -10, 4330.27, 9.5, 9.8, 9.65, 5_350.0),
    (get_4220_put_option(), -10, 4349.73, 8.30, 8.50, 8.4, 6_600.0),
    (get_4220_put_option(), -10, 4308, 14.8, 15.2, 15.00, 0.0)
])
def test_get_profit_loss_value(test_option, quantity, spot_price, bid, ask, price, expected_profit_loss):
    test_option.open_trade(quantity)
    test_option.update(test_update_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    assert test_option.get_profit_loss() == expected_profit_loss

