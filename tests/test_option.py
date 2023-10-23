import pytest

from options_framework.option_types import OptionPositionType
from options_test_helper import *

# Test initialization and update
def test_option_init_with_required_parameters():
    _id = 1
    strike = 4305
    option = Option(_id, ticker, strike, test_expiration, OptionType.CALL)

    assert option.option_id == _id
    assert option.ticker_symbol == ticker
    assert option.strike == strike
    assert option.expiration == test_expiration
    assert option.bid is None
    assert option.ask is None
    assert option.price is None
    assert option.quote_date is None
    assert option.iv is None
    assert option.delta is None
    assert option.gamma is None
    assert option.theta is None
    assert option.vega is None
    assert option.rho is None

def test_option_init_with_named_parameters():
    _id = 1
    strike = 4305
    bid, ask, price, spot_price = (32.7, 33.2, 32.95, 4308)
    option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, test_quote_date, spot_price, bid, ask, price)

    assert option.bid == bid
    assert option.ask == ask
    assert option.price == price
    assert option.quote_date == test_quote_date


def test_option_init_with_extended_properties():
    bid, ask, price, delta, spot_price, iv, gamma, theta, vega, open_interest, rho = (32.7, 33.2, 32.95,
                                                                                      -0.4916, 4308, 0.0951, 0.0048,
                                                                                      -1.0935, 3.5141, 24, -90.0008)
    _id = 1
    strike = 4305
    fee = 0.5

    option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, test_quote_date, spot_price, bid, ask, price,
                       open_interest=open_interest, iv=iv, delta=delta, gamma=gamma,
                       theta=theta, vega=vega, rho=rho, fee=fee)

    assert option.option_id == _id
    assert option.ticker_symbol == ticker
    assert option.strike == strike
    assert option.expiration == test_expiration
    assert option.bid == bid
    assert option.ask == ask
    assert option.price == price
    assert option.quote_date == test_quote_date
    assert option.iv == iv
    assert option.delta == delta
    assert option.gamma == gamma
    assert option.theta == theta
    assert option.vega == vega
    assert option.rho == rho
    assert option.fee == fee

def test_option_init_with_user_defined_attributes():
    _id = 1
    strike = 4305
    test_value = 'test value'

    bid, ask, price, delta, spot_price, iv, gamma, theta, vega, open_interest, rho = (32.7, 33.2, 32.95,
                                                                                      -0.4916, 4308, 0.0951, 0.0048,
                                                                                      -1.0935, 3.5141, 24, -90.0008)

    option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, test_quote_date, spot_price, bid, ask, price,
                    open_interest=open_interest, iv=iv, delta=delta, gamma=gamma,
                    theta=theta, vega=vega, rho=rho, user_defined=test_value)

    assert option.user_defined == test_value

"""
Test that updating an option updates it's option price and all other values
"""
def test_update_option_price_and_values():
    call = get_4390_call_option()

    # get updated values for 7/2/2021
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4330.27, 6, 6.2, 6.10, 0.1762, 0.004, -0.5858, 2.217, 606)
    test_value = 'test value'
    call.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                open_interest=open_interest, user_defined=test_value)

    expected_price = 6.1
    actual_price = call.price
    assert actual_price == expected_price
    assert call.delta == 0.1762
    assert call.gamma == 0.004
    assert call.theta == -0.5858
    assert call.vega == 2.217
    assert call.open_interest == 606
    assert call.spot_price == 4330.27
    assert call.quote_date == test_update_quote_date
    assert call.user_defined == test_value

# open trade
def test_open_trade_sets_correct_quantity():
    call = get_4390_call_option()
    quantity = 10

    assert call.quantity is None
    call.open_trade(quantity)

    assert call.quantity == quantity

def test_open_trade_when_trade_is_already_open_raises_exception():
    call = get_4390_call_option()
    quantity = 10
    call.open_trade(quantity)

    with pytest.raises(ValueError, match="Cannot open position. A position is already open."):
        call.open_trade(quantity)

def test_trade_spot_price():
    # create option
    call = get_4390_call_option()
    trade_spot_price = call.spot_price
    assert call.trade_spot_price is None

    # open trade
    call.open_trade(1)
    assert call.trade_spot_price == trade_spot_price

    # update trade
    update_4390_call_option(call)
    assert call.trade_spot_price == trade_spot_price
    assert call.trade_spot_price != call.spot_price

    # close trade
    call.close_trade()
    assert call.trade_spot_price == trade_spot_price

def test_trade_price():
    # create option
    call = get_4390_call_option()
    trade_price = call.price
    assert call.trade_price is None

    # open trade
    call.open_trade(1)
    assert call.trade_price == trade_price

    # update trade
    update_4390_call_option(call)
    assert call.trade_price == trade_price
    assert call.trade_price != call.price

    # close trade
    call.close_trade()
    assert call.trade_price == trade_price

# test open trade date
def test_trade_open_date():
    # create option
    call = get_4390_call_option()
    assert call.trade_open_date is None

    # open trade
    call.open_trade(1)
    assert call.trade_open_date == test_quote_date

    # update trade
    update_4390_call_option(call)
    assert call.trade_open_date == test_quote_date
    assert call.trade_open_date != call.quote_date

    # close trade
    call.close_trade()
    assert call.trade_open_date == test_quote_date

def test_trade_dte():
    # create option
    call = get_4390_call_option()
    assert call.trade_dte is None
    trade_dte = call.dte()

    # open trade
    call.open_trade(1)
    assert call.trade_dte == trade_dte

    # update trade
    update_4390_call_option(call)
    assert call.trade_dte == trade_dte
    assert call.trade_dte != call.dte

    # close trade
    call.close_trade()
    assert call.trade_dte == trade_dte

# test close date
def test_trade_close_date():
    # create option
    call = get_4390_call_option()
    assert call.trade_close_date == []

    # open trade
    call.open_trade(1)
    assert call.trade_close_date == []

    # update trade
    update_4390_call_option(call)
    assert call.trade_close_date == []

    # close trade
    call.close_trade()
    assert call.trade_close_date[0] == test_update_quote_date


def test_dte_is_none_when_option_does_not_have_quote_data():
    _id = 1
    strike = 4210
    option = Option(_id, 'WHAT', strike, test_expiration, OptionType.CALL)

    assert option.dte() is None


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


def test_otm_is_none_when_option_is_not_populated_with_values():
    _id = 1
    strike = 4210

    option = Option(_id, 'WHAT', strike, test_expiration, OptionType.CALL)

    assert option.otm is None


def test_itm_is_none_when_option_is_not_populated_with_current_values():
    _id = 1
    strike = 4210

    option = Option(_id, 'WHAT', strike, test_expiration, OptionType.CALL)

    assert option.itm is None


def test_otm_is_false_when_strike_is_lower_than_spot_for_put():
    put = get_4210_put_option()
    spot_price = 4211

    put.update(put.quote_date, spot_price, 10, 15, 12.5)

    assert put.otm == True
    assert put.itm == False


def test_itm_is_true_and_otm_is_false_when_strike_is_equal_to_spot_for_put():
    put = get_4210_put_option()

    put.update(put.quote_date, 4210, 10, 15, 12.5)

    assert put.otm == False
    assert put.itm == True


def test_itm_is_true_when_strike_is_greater_than_spot_for_put():
    put = get_4210_put_option()

    put.update(put.quote_date, 4209, 10, 15, 12.5)

    assert put.otm == False
    assert put.itm == True


def test_otm_is_true_when_strike_is_higher_than_spot_for_call():
    call = get_4320_call_option()

    call.update(call.quote_date, 4319, 10, 15, 12.5)

    assert call.otm == True
    assert call.itm == False


def test_itm_is_true_and_otm_is_false_when_strike_is_equal_to_spot_for_call():
    call = get_4320_call_option()

    call.update(call.quote_date, 4320, 10, 15, 12.5)

    assert call.otm == False
    assert call.itm == True


def test_itm_is_true_when_strike_is_lower_than_spot_for_call():
    call = get_4320_call_option()

    call.update(call.quote_date, 4321, 10, 15, 12.5)

    assert call.otm == False
    assert call.itm == True


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

def test_option_init_raises_exception_if_quote_date_is_greater_than_expiration():
    bad_open_date = datetime.datetime.strptime("2021-07-17 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    strike = 4380
    spot_price, bid, ask, price = (4308, 5.4, 5.7, 5.55)
    with pytest.raises(Exception, match="Cannot create an option with a quote date past its expiration date"):
        Option(id, ticker, strike, test_expiration, OptionType.CALL, quote_date=bad_open_date,
               spot_price=spot_price, bid=bid, ask=ask, price=price)

def test_that_update_raises_exception_if_quote_date_is_greater_than_expiration():
    bad_quote_date = datetime.datetime.strptime("2021-07-17 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    put = get_4210_put_option()
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4330.27, 8.8, 9.1, 8.95, -0.1471, 0.002, -0.9392, 1.9709, 349)
    with pytest.raises(Exception, match="Cannot update to a date past the option expiration"):
        put.update(bad_quote_date, spot_price, bid, ask, price, delta=delta,
                  gamma=gamma, theta=theta, vega=vega, open_interest=open_interest)


def test_option_that_is_not_open_has_none_position_type():
    call = get_4380_call_option()
    assert call.position_type is None

def test_open_long_call_option_has_position_type_long():
    quantity = 1
    call = get_4380_call_option()
    call.open_trade(quantity)

    assert call.position_type == OptionPositionType.LONG

def test_open_short_call_option_has_position_type_short():
    quantity = -1
    call = get_4380_call_option()
    call.open_trade(quantity)

    assert call.position_type == OptionPositionType.SHORT

def test_open_position_incurs_fee():
    quantity = 1
    put = get_4220_put_option()
    put.open_trade(quantity)
    expected_fees = 0.50

    assert put.total_fees == expected_fees

def test_open_position_does_not_incur_fee_when_flag_is_false():
    quantity = 1
    put = get_4220_put_option()
    put.open_trade(quantity, incur_fees=False)
    expected_fees = 0.0

    assert put.total_fees == expected_fees

def test_open_position_fees_are_multiplied_by_quantity():
    quantity = 10
    put = get_4220_put_option()
    put.open_trade(quantity)
    expected_fees = 5.00

    assert put.total_fees == expected_fees

def test_close_position_incurs_fees():
    # standard fee is 0.50.
    quantity = 1
    put = get_4220_put_option()
    put.open_trade(quantity)
    put.close_trade()
    expected_fees = 1

    assert put.total_fees == expected_fees

def test_close_position_does_not_incur_fees_when_flag_is_false():
    quantity = 1
    put = get_4220_put_option()
    put.open_trade(quantity, incur_fees=False)
    put.close_trade(incur_fees=False)
    expected_fees = 0.0

    assert put.total_fees == expected_fees

def test_close_long_position_adds_correct_close_date_and_close_amount():
    quantity = 10
    put = get_4220_put_option() # 15
    put.open_trade(quantity, incur_fees=False)
    update_4220_put_option(put) # 9.65
    put.close_trade(incur_fees=False)

    assert put.trade_close_date[0] == test_update_quote_date


def test_trade_cost_for_long_position():
    quantity = 1
    call = get_4380_call_option()
    call.open_trade(quantity)
    expected_cost = 555

    assert call.position_type == OptionPositionType.LONG
    assert call.total_premium() == expected_cost

def test_trade_cost_for_short_position():
    quantity = -10
    call = get_4380_call_option()
    call.open_trade(quantity)
    expected_cost = -5_550

    assert call.position_type == OptionPositionType.SHORT
    assert call.total_premium() == expected_cost


def test_trade_cost_throws_exception_when_trade_has_not_been_opened():
    call = get_4380_call_option()

    with pytest.raises(Exception, match="No trade has been opened."):
        _ = call.total_premium()


def test_current_value_is_zero_at_position_open():
    quantity = -10
    call = get_4380_call_option()
    call.open_trade(quantity)

    assert call.current_gain_loss() == 0

def test_long_position_current_value_when_option_price_increases():
    quantity = 10
    call = get_4380_call_option()
    call.open_trade(quantity)
    update_4380_call_option(call)
    expected_value = 2_550

    assert call.current_gain_loss() == expected_value


def test_long_position_current_value_when_option_price_decreases():
    quantity = 10
    put = get_4075_put_option()
    put.open_trade(quantity)
    update_4075_put_option(put)
    expected_value = -2_250

    assert put.current_gain_loss() == expected_value

def test_current_value_throws_exception_when_trade_has_not_been_opened():
    call = get_4380_call_option()

    with pytest.raises(Exception, match="No trade has been opened."):
        _ = call.current_gain_loss()

def test_short_position_current_value_when_option_price_increases():
    quantity = -10
    call = get_4380_call_option()
    call.open_trade(quantity)
    update_4380_call_option(call)
    expected_value = -2_550

    assert call.current_gain_loss() == expected_value

def test_short_position_current_value_when_option_price_decreases():
    quantity = -10
    put = get_4075_put_option()
    put.open_trade(quantity)
    update_4075_put_option(put)
    expected_value = 2_250

    assert put.current_gain_loss() == expected_value


def test_long_position_profit_loss_percent_when_option_price_increases():
    quantity = 10
    call = get_4380_call_option()
    call.open_trade(quantity)
    update_4380_call_option(call)
    expected_value = 0.4595

    assert call.profit_loss_percent() == expected_value


def test_long_position_profit_loss_percent_when_option_price_decreases():
    quantity = 10
    put = get_4075_put_option()
    put.open_trade(quantity)
    update_4075_put_option(put)
    expected_value = -0.3846

    assert put.profit_loss_percent() == expected_value

def test_short_position_profit_loss_percent_when_option_price_increases():
    quantity = -10
    call = get_4380_call_option()
    call.open_trade(quantity)
    update_4380_call_option(call)
    expected_value = -0.4595

    assert call.profit_loss_percent() == expected_value


def test_short_position_profit_loss_percent_when_option_price_decreases():
    quantity = -10
    put = get_4075_put_option()
    put.open_trade(quantity)
    update_4075_put_option(put)
    expected_value = 0.3846

    assert put.profit_loss_percent() == expected_value

def test_profit_loss_percent_throws_exception_when_no_trade_was_opened():
    call = get_4380_call_option()

    with pytest.raises(Exception, match="No trade has been opened."):
        _ = call.profit_loss_percent()

def test_is_expired_is_true_when_quote_date_is_at_expiration():
    quote_date = datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    put = get_4210_put_option()
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4330.27, 8.8, 9.1, 8.95, -0.1471, 0.002, -0.9392, 1.9709, 349)
    put.update(quote_date, spot_price, bid, ask, price, delta=delta,
                    gamma=gamma, theta=theta, vega=vega, open_interest=open_interest)

    assert put.is_expired() == True

def test_is_expired_is_false_when_quote_date_time_is_less_than_expiration():
    quote_date = datetime.datetime.strptime("2021-07-16 09:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    put = get_4210_put_option()
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest = \
        (4330.27, 8.8, 9.1, 8.95, -0.1471, 0.002, -0.9392, 1.9709, 349)
    put.update(quote_date, spot_price, bid, ask, price, delta=delta,
               gamma=gamma, theta=theta, vega=vega, open_interest=open_interest)

    assert put.is_expired() == False

def test_is_expired_is_false_when_quote_date_is_less_than_expiration():
    quote_date = datetime.datetime.strptime("2021-07-16", "%Y-%m-%d")
    spot_price, bid, ask, price = (4308, 32.7, 33.2, 32.95)
    _id = 1
    strike = 4305

    option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, quote_date, spot_price, bid, ask, price)

    assert option.is_expired() == False

def test_get_close_price():
    call = get_4320_call_option()
    call.open_trade(1)
    update_4320_call_option(call)
    expected_close_price = 34.70

    close_price = call.get_closing_price()

    assert close_price == expected_close_price

def test_get_close_price_on_option_that_has_not_been_traded_raises_exception():
    call = get_4320_call_option()
    update_4320_call_option(call)

    with pytest.raises(ValueError, match="Cannot determine closing price on option that has not been traded"):
        call.get_closing_price()

# When the bid is zero on a long option, there are no buyers.
# Long options are bought to open, and must be sold to close, and can't be sold for $0
def test_get_close_price_on_long_option_when_bid_is_zero():
    long_call = get_4320_call_option()
    quantity = 1
    quote_date = datetime.datetime.strptime("2021-07-16 09:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    long_call.open_trade(quantity)
    spot_price, bid, ask, price = (4297.79, 0, 0.10, 0.05)
    long_call.update(quote_date, spot_price, bid, ask, price)

    assert long_call.price == price
    assert long_call.get_closing_price() == 0.0

# Normally, the option price is assumed to be halfway between the bid and ask
# When the bid is zero, it implies that there are no buyers, and only sellers at the ask price
# Therefore, the option can only be bought at the ask and cannot be sold at any price
def test_get_close_price_on_short_option_when_bid_is_zero():
    short_call = get_4320_call_option()
    quantity = -1
    quote_date = datetime.datetime.strptime("2021-07-16 09:31:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    short_call.open_trade(quantity)
    spot_price, bid, ask, price = (4297.79, 0, 0.10, 0.05)
    short_call.update(quote_date, spot_price, bid, ask, price)

    assert short_call.price == price
    assert short_call.get_closing_price() == 0.10

# If an option is OTM at expiration, it has a zero value. Sometimes the data
# gives a price, but this is not the actual closing price.
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

# The intrinsic value is the difference between the underlying price and the strike price
# When an option expires ITM, the closing price is the intrinsic value
def test_get_close_price_is_intrinsic_value_when_option_expires_itm():
    expiration_quote_date = datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    long_call = get_4320_call_option()
    long_call.open_trade(1)
    spot_price, bid, ask, price = (4325, 32.7, 33.2, 32.95)
    long_call.update(expiration_quote_date, spot_price, bid, ask, price)
    # 4325 - 4320 == 5
    assert long_call.get_closing_price() == 5.0

    put = get_4075_put_option()
    put.open_trade(1)
    spot_price, bid, ask, price = (4072, 5.7, 6, 5.85)
    put.update(expiration_quote_date, spot_price, bid, ask, price)
    # 4075 - 4072 == 3
    assert put.get_closing_price() == 3.0

