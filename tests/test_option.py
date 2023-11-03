import pytest

from options_framework.option_types import OptionPositionType
import options_framework.option as option
from options_test_helper import *


# Test initialization
def test_option_init_with_only_option_contract_parameters():
    _id = 1
    strike = 100
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
    strike = 100
    spot_price, bid, ask, price = (95, 1.0, 2.0, 1.5)
    test_option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, test_quote_date, spot_price, bid, ask,
                         price)

    option_quote = test_option.option_quote

    assert option_quote.bid == bid
    assert option_quote.ask == ask
    assert option_quote.price == price
    assert option_quote.quote_date == test_quote_date


def test_option_init_with_extended_properties():
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest, rho, iv = (95, 1.0, 2.0, 1.5,
                                                                                      0.3459, -0.1234, 0.0485,
                                                                                      0.0935, 100, 0.132, 0.3301)
    _id = 1
    strike = 100
    fee = 0.5

    test_option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, test_quote_date, spot_price, bid, ask,
                         price, open_interest=open_interest, implied_volatility=iv, delta=delta, gamma=gamma,
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
    strike = 100
    test_value = 'test value'

    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest, rho, iv = (95, 1.0, 2.0, 1.5,
                                                                                      0.3459, -0.1234, 0.0485,
                                                                                      0.0935, 100, 0.132, 0.3301)

    test_option = Option(_id, ticker, strike, test_expiration, OptionType.CALL, test_quote_date, spot_price, bid, ask,
                         price,
                         open_interest=open_interest, iv=iv, delta=delta, gamma=gamma,
                         theta=theta, vega=vega, rho=rho, user_defined=test_value)

    assert test_option.user_defined == test_value


def test_option_init_raises_exception_if_missing_required_fields():
    # missing id
    _id = None
    with pytest.raises(ValueError, match="option_id is required"):
        Option(option_id=_id, symbol=ticker, strike=100, expiration=test_expiration, option_type=OptionType.CALL)

    # missing ticker symbol
    _id = 1
    none_symbol = None
    with pytest.raises(ValueError, match="symbol is required"):
        Option(option_id=_id, symbol=none_symbol, strike=100, expiration=test_expiration, option_type=OptionType.CALL)

    # missing strike
    none_strike = None
    with pytest.raises(ValueError, match="strike is required"):
        Option(option_id=_id, symbol=ticker, strike=none_strike, expiration=test_expiration, option_type=OptionType.CALL)

    # missing expiration
    none_expiration = None
    with pytest.raises(ValueError, match="expiration is required"):
        Option(option_id=_id, symbol=ticker, strike=100, expiration=none_expiration, option_type=OptionType.CALL)

    # missing option type
    none_option_type = None
    with pytest.raises(ValueError, match="option_type is required"):
        Option(option_id=_id, symbol=ticker, strike=100, expiration=test_expiration, option_type=none_option_type)


def test_option_init_raises_exception_if_quote_date_is_greater_than_expiration():
    bad_open_date = datetime.datetime.strptime("2021-07-17 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    strike = 100
    spot_price, bid, ask, price = (95, 1.0, 2.0, 1.5)
    with pytest.raises(Exception, match="Cannot create an option with a quote date past its expiration date"):
        Option(id, ticker, strike, test_expiration, OptionType.CALL, quote_date=bad_open_date,
               spot_price=spot_price, bid=bid, ask=ask, price=price)


@pytest.mark.parametrize("test_option, expected_repr", [
    (get_test_call_option(), '<CALL XYZ 100.0 2021-07-16>'),
    (get_test_put_option(), '<PUT XYZ 100.0 2021-07-16>')])
def test_call_option_string_representation(test_option, expected_repr):
    assert str(test_option) == expected_repr

def test_update_sets_correct_values():
    call = get_test_call_option_extended_properties()

    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest, rho, iv = \
        (95, 3.4, 3.50, 3.45, 0.4714, 0.1239, -0.0401, 0.1149, 1000, 0.279, 0.3453)
    test_value = 'test value'
    call.update(test_update_quote_date, spot_price, bid, ask, price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                rho=rho, implied_volatility=iv,
                open_interest=open_interest, user_defined=test_value)

    assert call.option_quote.spot_price == spot_price
    assert call.option_quote.quote_date == test_update_quote_date
    assert call.option_quote.bid == bid
    assert call.option_quote.ask == ask
    assert call.greeks.delta == delta
    assert call.greeks.gamma == gamma
    assert call.greeks.theta == theta
    assert call.greeks.vega == vega
    assert call.greeks.rho == rho
    assert call.extended_properties.open_interest == open_interest
    assert call.extended_properties.implied_volatility == iv
    assert call.user_defined == test_value


def test_update_raises_exception_if_missing_required_fields():
    call = get_4390_call_option()

    # quote_date
    none_quote_date = None
    with pytest.raises(ValueError, match="quote_date is required"):
        call.update(quote_date=none_quote_date, spot_price=4330, bid=6, ask=6.2, price=6.10)

    # spot price
    none_spot_price = None
    with pytest.raises(ValueError, match="spot_price is required"):
        call.update(quote_date=test_update_quote_date, spot_price=none_spot_price, bid=6, ask=6.2, price=6.10)

    # bid
    none_bid = None
    with pytest.raises(ValueError, match="bid is required"):
        call.update(quote_date=test_update_quote_date, spot_price=4330, bid=none_bid, ask=6.2, price=6.10)

    # ask
    none_ask = None
    with pytest.raises(ValueError, match="ask is required"):
        call.update(quote_date=test_update_quote_date, spot_price=4330, bid=6, ask=none_ask, price=6.10)

    # price
    none_price = None
    with pytest.raises(ValueError, match="price is required"):
        call.update(quote_date=test_update_quote_date, spot_price=4330, bid=6, ask=6.2, price=none_price)


def test_update_raises_exception_if_quote_date_is_greater_than_expiration():
    bad_quote_date = datetime.datetime.strptime("2021-07-17 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    put = get_test_put_option()
    spot_price, bid, ask, price = (105, 1.0, 2.0, 1.5)
    with pytest.raises(Exception, match="Cannot update to a date past the option expiration"):
        put.update(bad_quote_date, spot_price, bid, ask, price)


# open trade
def test_open_trade_sets_correct_trade_open_info_values():
    test_option = get_test_call_option()
    quantity = 10

    trade_open_info = test_option.open_trade(quantity, comment="my super insightful comment")
    assert trade_open_info.date == test_quote_date
    assert trade_open_info.quantity == 10
    assert trade_open_info.price == 1.5
    assert trade_open_info.premium == 1_500.0
    assert test_option.quantity == 10

    # kwargs were set as attributes
    assert test_option.comment == "my super insightful comment"


def test_option_that_is_not_open_has_none_position_type():
    test_option = get_test_call_option()
    assert test_option.position_type is None


@pytest.mark.parametrize("quantity, position_type", [(10, OptionPositionType.LONG), (-10, OptionPositionType.SHORT)])
def test_open_trade_has_correct_position_type(quantity, position_type):
    test_option = get_test_call_option()
    test_option.open_trade(quantity)

    assert test_option.position_type == position_type


@pytest.mark.parametrize("test_option, quantity, expected_premium", [
    (get_test_call_option(), 10, 1_500.0),
    (get_test_call_option(), 5, 750.0),
    (get_test_call_option(), -10, -1_500.0),
    (get_test_put_option(), 10, 1_500.0),
    (get_test_put_option(), -10, -1_500.0),
    (get_test_put_option(), 5, 750.0),
    ])
def test_open_trade_returns_correct_premium_value(test_option, quantity, expected_premium):
    trade_open_info = test_option.open_trade(quantity)
    assert trade_open_info.premium == expected_premium


@pytest.mark.parametrize("quantity, incur_fees_flag, expected_fees", [(10, True, 5.0), (2, True, 1.0), (-3, True, 1.5),
                                                                      (10, False, 0.0), (2, False, 0.0),
                                                                      (-3, False, 0.0)])
def test_open_trade_sets_total_fees_when_incur_fees_flag_is_true(quantity, incur_fees_flag, expected_fees):
    test_option = get_test_call_option()
    test_option.fee_per_contract = standard_fee
    test_option.open_trade(quantity=quantity, incur_fees=incur_fees_flag)

    assert test_option.total_fees == expected_fees


def test_open_trade_when_there_is_no_quote_data_raises_exception():
    test_option = Option(1, ticker, 100, test_expiration, OptionType.CALL)
    with pytest.raises(ValueError, match="Cannot open a position that does not have price data"):
        test_option.open_trade(1)

@pytest.mark.parametrize("quantity", [None, 1.5, 0, -1.5, "abc"])
def test_open_trade_with_invalid_quantity_raises_exception(quantity):
    test_option = get_test_call_option()

    with pytest.raises(ValueError, match="Quantity must be a non-zero integer."):
        test_option.open_trade(quantity)


def test_open_trade_when_trade_is_already_open_raises_exception():
    test_option = get_test_call_option()
    quantity = 10
    test_option.open_trade(quantity)

    with pytest.raises(ValueError, match="Cannot open position. A position is already open."):
        test_option.open_trade(quantity)


def test_close_trade_closes_entire_position_with_default_values():
    test_option = get_test_call_option()
    quantity = 10
    test_option.open_trade(quantity)
    assert test_option.quantity == quantity

    test_option.close_trade()  # Missing quantity closes entire position

    assert test_option.quantity == 0

@pytest.mark.parametrize("quantity, close_quantity, remaining_quantity", [
    (10, 8, 2), (-10, -8, -2), (10, None, 0), (-10, None, 0)])
def test_close_partial_trade(quantity, close_quantity, remaining_quantity):
    test_option = get_test_call_option()
    test_option.open_trade(quantity)
    test_option.close_trade(quantity=close_quantity)

    assert test_option.quantity == remaining_quantity


@pytest.mark.parametrize("open_qty, close1_qty, close2_qty, expected_qty", [(10, 2, 8, 0), (10, 2, 3, 5),
                                                                            (-10, -2, -8, 0), (-10, -2, -3, -5)])
def test_close_trade_with_multiple_partial_close(open_qty, close1_qty, close2_qty, expected_qty):
    test_option = get_test_call_option()
    test_option.open_trade(open_qty)

    test_option.close_trade(quantity=close1_qty)
    test_option.close_trade(quantity=close2_qty)

    assert test_option.quantity == expected_qty


@pytest.mark.parametrize("open_quantity, close_quantity", [(10, 12), (-10, -12)])
def test_close_trade_with_greater_than_quantity_open_raises_exception(open_quantity, close_quantity):
    test_option = get_test_call_option()
    test_option.open_trade(open_quantity)

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        test_option.close_trade(close_quantity)


@pytest.mark.parametrize("open_qty, close1_qty, close2_qty", [(10, 6, 6), (10, 10, 1), (-10, -7, -4), (-10, -10, -1)])
def test_close_partial_trade_with_greater_than_remaining_quantity_raises_exception(open_qty, close1_qty, close2_qty):
    test_option = get_test_call_option()
    test_option.open_trade(open_qty)
    test_option.close_trade(quantity=close1_qty)  # close partial trade

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        test_option.close_trade(close2_qty)


@pytest.mark.parametrize("incur_fees_flag, open_quantity, close_quantity, fee_amount", [(True, 10, 10, 5.0),
                                                                                        (True, -10, -10, 5.0),
                                                                                        (True, 10, 2, 1.0),
                                                                                        (False, 10, 10, 0.0),
                                                                                        (False, -10, -10, 0.0),
                                                                                        (False, -10, -2, 0.0)])
def test_close_trade_updates_total_fees_incur_fees_flag(incur_fees_flag, open_quantity, close_quantity, fee_amount):
    test_option = get_test_call_option()
    test_option.fee_per_contract = standard_fee
    test_option.open_trade(open_quantity, incur_fees=False)  # do not incur fees on open
    assert test_option.total_fees == 0.0

    test_option.close_trade(quantity=close_quantity, incur_fees=incur_fees_flag)

    assert test_option.total_fees == fee_amount

# "open_qty, close_qty, expected_qty, close_dt, close_price, close_pnl, close_pnl_pct, close_fees", [
#         (10, 10, -10, test_update_quote_date, 10.0, 0.0, 0.0, 5.0),
#         (-10, -10, 10, test_update_quote_date, 10.0, 0.0, 0.0, 5.0),
#         (10, 1, test_update_quote_date, 10.0, 0.0, 0.0, 0.5),
#         (-10, 5, test_update_quote_date, 10.0, 0.0, 0.0, 2.5)
@pytest.mark.parametrize("open_qty, close_qty, expected_qty, close_dt, close_pnl, close_pnl_pct, close_fees", [
    (10, 10, -10, test_update_quote_date, 8_500.0, 5.6667, 5.0),
    (-10, -10, 10, test_update_quote_date, -8_500.0, -5.6667, 5.0),
    (10, 1, -1, test_update_quote_date, 850.0, 5.6667, 0.5),
    (-10, -5, 5, test_update_quote_date, -4_250.0, -5.6667, 2.5)
    ])
def test_close_trade_values_with_one_close_trade(open_qty, close_qty, expected_qty, close_dt, close_pnl,
                                                 close_pnl_pct, close_fees):
    test_option = get_test_call_option()
    test_option.fee_per_contract = standard_fee
    test_option.open_trade(open_qty)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    trade_close_info = test_option.close_trade(close_qty)

    assert trade_close_info.date == quote_date
    assert trade_close_info.quantity == close_qty*-1
    assert trade_close_info.price == price
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.profit_loss_percent == close_pnl_pct
    assert trade_close_info.fees == close_fees


@pytest.mark.parametrize(
    "open_qty, cqty1, cqty2, close_date, close_price, close_pnl, pnl_pct, close_fees, closed_qty, remaining_qty",
    [(10, 2, 3, test_update_quote_date2, 7.0, 2_750.0, 1.8333, 2.5, -5, 5),
     (-10, -3, -5, test_update_quote_date2, 6.88, -4_300, -2.8667, 4.0, 8, -2),
     (10, 8, 1, test_update_quote_date2, 9.44, 7_150.0, 4.7667, 4.5, -9, 1),
     (-10, -1, -1, test_update_quote_date2, 7.5, -1_200.0, -0.8000, 1.0, 2, -8)
     ])
def test_call_option_close_trade_values_with_multiple_close_trades(open_qty, cqty1, cqty2, close_date, close_price,
                                                                   close_pnl, pnl_pct, close_fees,
                                                                   closed_qty, remaining_qty):
    test_option = get_test_call_option()
    test_option.fee_per_contract = standard_fee
    test_option.open_trade(open_qty)
    # first update
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(quantity=cqty1)

    # second update
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_2()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(quantity=cqty2)

    # get close info for closed trades
    trade_close_info = test_option.get_trade_close_info()
    assert trade_close_info.date == close_date
    assert trade_close_info.price == close_price
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.fees == close_fees

    assert trade_close_info.quantity == closed_qty
    assert test_option.quantity == remaining_qty


@pytest.mark.parametrize(
    "open_qty, cqty1, cqty2, close_date, close_price, close_pnl, pnl_pct, close_fees, closed_qty, remaining_qty",
    [(10, 2, 3, test_update_quote_date2, 7.0, 2_750.0, 1.8333, 2.5, -5, 5),
     (-10, -3, -5, test_update_quote_date2, 6.88, -4_300, -2.8667, 4.0, 8, -2),
     (10, 8, 1, test_update_quote_date2, 9.44, 7_150.0, 4.7667, 4.5, -9, 1),
     (-10, -1, -1, test_update_quote_date2, 7.5, -1_200.0, -0.8000, 1.0, 2, -8)
     ])
def test_put_option_close_trade_values_with_multiple_close_trades(open_qty, cqty1, cqty2, close_date, close_price,
                                                                   close_pnl, pnl_pct, close_fees,
                                                                   closed_qty, remaining_qty):
    test_option = get_test_put_option()
    test_option.fee_per_contract = standard_fee
    test_option.open_trade(open_qty)
    # first update
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(quantity=cqty1)

    # second update
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_2()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(quantity=cqty2)

    # get close info for closed trades
    trade_close_info = test_option.get_trade_close_info()
    assert trade_close_info.date == close_date
    assert trade_close_info.price == close_price
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.fees == close_fees

    assert trade_close_info.quantity == closed_qty
    assert test_option.quantity == remaining_qty


def test_trade_close_records_returns_all_close_trades():
    test_option = get_test_call_option()
    test_option.open_trade(10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    test_option.close_trade(quantity=3)

    records = test_option.trade_close_records
    assert len(records) == 1

    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_2()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(quantity=6)

    records = test_option.trade_close_records
    assert len(records) == 2


def test_total_fees_returns_all_fees_incurred():
    # standard fee is 0.50 per contract
    _id, strike, spot_price, bid, ask, price = (1, 100, 90, 1.0, 2.0, 1.5)
    test_option = Option(_id, ticker, strike, test_expiration, OptionType.CALL,
                         quote_date=test_quote_date, spot_price=spot_price, bid=bid,
                         ask=ask, price=price, fee=standard_fee) # add fee when creating option object

    test_option.open_trade(10)

    assert test_option.total_fees == 5.0

    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(quantity=2)

    assert test_option.total_fees == 6.0

    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(quantity=3)

    assert test_option.total_fees == 7.5


def test_get_closing_price():
    test_option = get_test_call_option()
    test_option.open_trade(1)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    expected_close_price = 10.0

    close_price = test_option.get_closing_price()

    assert close_price == expected_close_price


def test_get_close_price_on_option_that_has_not_been_traded_raises_exception():
    test_option = get_test_call_option()
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    with pytest.raises(ValueError,
                       match="Cannot determine closing price on option that does not have an opening trade"):
        test_option.get_closing_price()


@pytest.mark.parametrize("open_qty, expected_closing_price", [
    (1, 0.0), (-1, 0.05)
])
def test_get_closing_price_on_call_option_when_bid_is_zero(open_qty, expected_closing_price):
    test_option = get_test_call_option()
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    # open trade
    test_option.open_trade(open_qty)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_3()
    assert bid == 0.0
    test_option.update(quote_date, spot_price, bid, ask, price)

    assert test_option.get_closing_price() == expected_closing_price


@pytest.mark.parametrize("open_qty, expected_closing_price", [
    (1, 0.0), (-1, 0.05)
])
def test_get_closing_price_on_put_option_when_bid_is_zero(open_qty, expected_closing_price):
    test_option = get_test_put_option()
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    # open trade
    test_option.open_trade(open_qty)
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_3()
    assert bid == 0.0
    test_option.update(quote_date, spot_price, bid, ask, price)

    assert test_option.get_closing_price() == expected_closing_price


def test_call_option_get_close_price_is_zero_when_option_expires_otm():
    test_option = get_test_put_option()
    test_option.open_trade(1)
    _, spot_price, bid, ask, price = get_test_put_option_update_values_3()
    test_option.update(at_expiration_quote_date, spot_price, bid, ask, price)

    assert test_option.otm()
    assert test_option.option_quote.price != 0.0
    assert test_option.get_closing_price() == 0.0

def test_put_option_get_close_price_is_zero_when_option_expires_otm():
    test_option = get_test_put_option()
    test_option.open_trade(1)
    _, spot_price, bid, ask, price = get_test_put_option_update_values_3()
    test_option.update(at_expiration_quote_date, spot_price, bid, ask, price)

    assert test_option.otm()
    assert test_option.option_quote.price != 0.0
    assert test_option.get_closing_price() == 0.0

def test_dte_is_none_when_option_does_not_have_quote_data():
    test_option = Option(1, ticker, 100, test_expiration, OptionType.CALL)

    assert test_option.dte() is None


def test_dte_when_option_has_quote_data():
    test_option = get_test_call_option()

    expected_dte = 15
    actual_dte = test_option.dte()
    assert actual_dte == expected_dte


def test_dte_is_updated_when_quote_date_is_updated():
    test_option = get_test_call_option()
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    expected_dte = 14
    assert test_option.dte() == expected_dte


@pytest.mark.parametrize("expiration_datetime",
                         [datetime.datetime.strptime("2021-07-16 09:31:00.000000", "%Y-%m-%d %H:%M:%S.%f"),
                          datetime.datetime.strptime("2021-07-16 11:00:00.000000", "%Y-%m-%d %H:%M:%S.%f"),
                          datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f")])
def test_dte_is_zero_on_expiration_day(expiration_datetime):
    test_option = get_test_call_option()
    _, spot_price, bid, ask, price = get_test_put_option_update_values_1()
    test_option.update(expiration_datetime, spot_price, bid, ask, price)

    expected_dte = 0
    assert test_option.dte() == expected_dte


def test_otm_and_itm_equal_none_when_option_does_not_have_quote_data():
    test_option = Option(1, ticker, 100, test_expiration, OptionType.CALL)

    assert test_option.itm() is None
    assert test_option.otm() is None


@pytest.mark.parametrize("option_type, spot_price, strike, expected_value", [
    (OptionType.CALL, 99.99, 100.0, True), (OptionType.CALL, 100.0, 100.0, False),
    (OptionType.CALL, 100.01, 100.0, False),
    (OptionType.PUT, 99.99, 100.0, False), (OptionType.PUT, 100.0, 100.0, False),
    (OptionType.PUT, 100.01, 100.0, True)])
def test_call_option_otm(option_type, spot_price, strike, expected_value):
    bid, ask, price = (9.50, 10.5, 10.00)
    test_option = Option(1, ticker, 100, test_expiration, option_type,
                         quote_date=test_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    actual_value = test_option.otm()
    assert actual_value == expected_value


@pytest.mark.parametrize("option_type, spot_price, strike, expected_value", [
    (OptionType.CALL, 99.99, 100.0, False), (OptionType.CALL, 100.0, 100.0, True),
    (OptionType.CALL, 100.01, 100.0, True),
    (OptionType.PUT, 99.99, 100.0, True), (OptionType.PUT, 100.0, 100.0, True),
    (OptionType.PUT, 100.01, 100.0, False)])
def test_call_option_itm(option_type, spot_price, strike, expected_value):
    bid, ask, price = (9.50, 10.5, 10.00)
    test_option = Option(1, ticker, 100, test_expiration, option_type,
                         quote_date=test_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    actual_value = test_option.itm()
    assert actual_value == expected_value

def test_is_expired_returns_none_when_no_quote_data():
    test_option = Option(1, ticker, 100, test_expiration, OptionType.CALL)

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
    test_option = get_test_call_option()

    # cheat to set data manually
    contract = option.OptionContract(1, ticker, expiration_date_test, 100.0, OptionType.CALL)
    test_option._option_contract = contract

    _, spot_price, bid, ask, price = get_test_put_option_update_values_1()
    quote = option.OptionQuote(quote_date, spot_price, bid, ask, price)
    test_option._option_quote = quote

    actual_result = test_option.is_expired()

    assert actual_result == expected_result


def test_is_trade_open_returns_false_if_no_trade_was_opened():
    test_option = get_test_call_option()
    expected_result = False
    assert test_option.is_trade_open() == expected_result


def test_is_trade_open_returns_true_if_trade_was_opened():
    test_option = get_test_call_option()
    test_option.open_trade(10)
    expected_result = True

    assert test_option.is_trade_open() == expected_result


def test_is_trade_open_returns_true_if_trade_was_opened_and_partially_closed():
    test_option = get_test_call_option()
    test_option.open_trade(10)
    test_option.close_trade(5)
    expected_result = True

    assert test_option.is_trade_open() == expected_result


def test_is_trade_open_returns_false_if_trade_was_opened_and_then_closed():
    test_option = get_test_call_option()
    test_option.open_trade(10)
    test_option.close_trade(10)
    expected_result = False

    assert test_option.is_trade_open() == expected_result


def test_get_open_profit_loss_raises_exception_if_trade_was_not_opened():
    test_option = get_test_call_option()

    with pytest.raises(Exception, match="No trade has been opened."):
        test_option.get_open_profit_loss()


def test_get_open_profit_loss_is_zero_if_quote_data_is_not_updated():
    test_option = get_test_call_option()
    test_option.open_trade(10)

    assert test_option.get_open_profit_loss() == 0.0


def test_get_open_profit_loss_is_zero_when_no_contracts_are_open():
    test_option = get_test_call_option()
    test_option.open_trade(10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(10)

    assert test_option.get_open_profit_loss() == 0.0


@pytest.mark.parametrize("test_option, quantity, price, expected_profit_loss", [
    (get_test_call_option(), 10, 1.6, 100.0),
    (get_test_call_option(), 10, 1.4, -100.0),
    (get_test_call_option(), 10, 1.5, 0.0),
    (get_test_call_option(), -10, 1.6, -100.0),
    (get_test_call_option(), -10, 1.4, 100.0),
    (get_test_call_option(), -10, 1.5, 0.0),
    (get_test_put_option(), 10, 1.6, 100.0),
    (get_test_put_option(), 10, 1.4, -100.0),
    (get_test_put_option(), 10, 1.5, 0.0),
    (get_test_put_option(), -10, 1.6, -100.0),
    (get_test_put_option(), -10, 1.4, 100.0),
    (get_test_put_option(), -10, 1.5, 0.0)
])
def test_get_open_profit_loss_value(test_option, quantity, price, expected_profit_loss):
    test_option.open_trade(quantity)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    actual_profit_loss = test_option.get_open_profit_loss()
    assert actual_profit_loss == expected_profit_loss

def test_get_open_profit_loss_percent_raises_exception_if_trade_was_not_opened():
    test_option = get_test_call_option()

    with pytest.raises(Exception, match="No trade has been opened."):
        test_option.get_open_profit_loss_percent()


def test_get_profit_loss_percent_return_zero_when_no_contracts_are_open():
    test_option = get_test_call_option()
    test_option.open_trade(1)
    test_option.close_trade(1)

    assert test_option.get_open_profit_loss_percent() == 0.0


@pytest.mark.parametrize("test_option, quantity, price, expected_profit_loss_pct", [
    (get_test_call_option(), 10, 2.25, 0.5),
    (get_test_call_option(), 10, 1.17, -0.22),
    (get_test_call_option(), 10, 1.5, 0.0),
    (get_test_call_option(), -10, 2.25, -0.50),
    (get_test_call_option(), -10, 1.17, 0.22),
    (get_test_call_option(), -10, 1.5, 0.0),
    (get_test_put_option(), 10, 2.25, 0.5),
    (get_test_put_option(), 10, 1.17, -0.22),
    (get_test_put_option(), 10, 1.5, 0.0),
    (get_test_put_option(), -10, 2.25, -0.50),
    (get_test_put_option(), -10, 1.17, 0.22),
    (get_test_put_option(), -10, 1.5, 0.0)
])
def test_get_profit_loss_percent_value(test_option, quantity, price, expected_profit_loss_pct):
    test_option.open_trade(quantity)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    actual_profit_loss = test_option.get_open_profit_loss_percent()
    assert actual_profit_loss == expected_profit_loss_pct

@pytest.mark.parametrize("quote_date, expected_days_in_trade", [
    (datetime.datetime.strptime("2021-07-01 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 0),
    (datetime.datetime.strptime("2021-07-01 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 0),
    (datetime.datetime.strptime("2021-07-07 11:14:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 6),
    (datetime.datetime.strptime("2021-07-13 10:53:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 12),
    (datetime.datetime.strptime("2021-07-15 10:05:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 14),
    (datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 15)
])
def test_get_days_in_trade(quote_date, expected_days_in_trade):
    test_option = get_test_call_option()
    test_option.open_trade(1)

    _, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    assert test_option.get_days_in_trade() == expected_days_in_trade

def test_get_total_profit_loss_raises_exception_if_not_traded():
    test_option = get_4380_call_option()

    with pytest.raises(Exception, match="No trade has been opened."):
        test_option.get_total_profit_loss()

@pytest.mark.parametrize("test_option, qty, price, expected_value", [
    (get_test_call_option(), 10, 2.0, 500.0),
    (get_test_call_option(), -10, 2.0, -500.0),
    (get_test_put_option(), 10, 2.0, 500.0),
    (get_test_put_option(), -10, 2.0, -500.0),
])
def test_get_total_profit_loss_returns_unrealized_when_no_contracts_are_closed(test_option, qty, price, expected_value):
    test_option = get_test_call_option()
    test_option.open_trade(qty)

    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    assert test_option.get_total_profit_loss() == expected_value


def test_get_total_profit_loss_returns_closed_pnl_when_all_contracts_are_closed():
    test_option = get_test_call_option()
    test_option.open_trade(10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(10)

    assert test_option.get_total_profit_loss() == 8_500.0

def test_get_total_profit_loss_returns_unrealized_and_closed_pnl_when_partially_closed():
    test_option = get_test_call_option()
    test_option.open_trade(10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(5)  # 4250
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_2()
    test_option.update(quote_date, spot_price, bid, ask, price)  # 1750

    assert test_option.get_total_profit_loss() == 6_000.0

def test_get_total_profit_loss_returns_unrealized_and_closed_pnl_when_multiple_close_trades():
    test_option = get_test_call_option()
    test_option.open_trade(10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(3)  # 2550
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_2()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(3)  # 1050
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_2()
    test_option.update(quote_date, spot_price, bid, ask, 8.0)  # 2600

    actual_value = test_option.get_total_profit_loss()
    assert actual_value == 6_200.0


def test_get_total_profit_loss_percent_raises_exception_if_not_traded():
    test_option = get_test_call_option()

    with pytest.raises(Exception, match="No trade has been opened."):
        test_option.get_total_profit_loss_percent()

@pytest.mark.parametrize("test_option, qty, price, expected_value", [
    (get_test_call_option(), 10, 1.8, 0.2),
    (get_test_call_option(), -10, 1.8, -0.2),
    (get_test_put_option(), 10, 1.8, 0.2),
    (get_test_put_option(), -10, 1.8, -0.2),
])
def test_get_total_profit_loss_percent_returns_unrealized_when_no_contracts_are_closed(
        test_option, qty, price, expected_value):
    test_option = get_test_call_option()
    test_option.open_trade(qty)

    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)

    actual_value = test_option.get_total_profit_loss_percent()
    assert actual_value == expected_value

@pytest.mark.parametrize("test_option, qty, price, expected_value", [
    (get_test_call_option(), 10, 1.8, 0.2),
    (get_test_call_option(), -10, 1.8, -0.2),
    (get_test_put_option(), 10, 1.8,  0.2),
    (get_test_put_option(), -10, 1.8, -0.2),
])
def test_get_total_profit_loss_percent_returns_closed_pnl_when_all_contracts_are_closed(test_option, qty, price,
                                                                                        expected_value):
    test_option.open_trade(qty)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price)
    test_option.close_trade(qty)

    assert test_option.get_total_profit_loss_percent() == expected_value

@pytest.mark.parametrize("test_option, qty, close_qty_1, close_qty_2, price1, price2, price3, expected_value", [
    (get_test_call_option(), 10, 4, 2, 1.8, 2.2, 0.10, -0.2),
    (get_test_call_option(), -10, -4, -2,  1.8, 2.2, 0.10, 0.2),
    (get_test_call_option(), 10, 4, 2, 3.0, 4.5, 6, 2.0),
    (get_test_call_option(), -10, -4, -2, 3.0, 4.5, 6, -2.0),
])
def test_get_total_profit_loss_percent_returns_unrealized_and_closed_pnl_when_multiple_close_trades(test_option, qty,
                                                                                                    close_qty_1,
                                                                                                    close_qty_2,
                                                                                                    price1, price2,
                                                                                                    price3,
                                                                                                    expected_value):
    test_option.open_trade(qty)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1()
    test_option.update(quote_date, spot_price, bid, ask, price1)
    it1 = test_option.close_trade(close_qty_1)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_2()
    test_option.update(quote_date, spot_price, bid, ask, price2)
    it2 = test_option.close_trade(close_qty_2)  # 1050
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_2()
    test_option.update(quote_date, spot_price, bid, ask, price3)  # 2600

    actual_value = test_option.get_total_profit_loss_percent()
    assert actual_value == expected_value


