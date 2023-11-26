import datetime
import pytest

from options_framework.option_types import OptionPositionType, OptionType, OptionStatus
from options_framework import option
from options_framework.option import Option
from options_framework.utils.exceptions import InvalidAssignmentError


def test_option_init_with_only_option_contract_parameters(option_id, ticker, test_expiration):
    strike = 100
    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.CALL)

    assert test_option.option_id == option_id
    assert test_option.symbol == ticker
    assert test_option.strike == strike
    assert test_option.expiration == test_expiration

    assert test_option.quantity == 0
    assert OptionStatus.CREATED in test_option.status


def test_option_init_with_quote_data(option_id, ticker, test_expiration, test_quote_date):
    strike = 100
    spot_price, bid, ask, price = (95, 1.0, 2.0, 1.5)
    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.CALL, quote_date=test_quote_date, spot_price=spot_price,
                         bid=bid, ask=ask, price=price)

    assert test_option.bid == bid
    assert test_option.ask == ask
    assert test_option.price == price
    assert test_option.quote_date == test_quote_date
    assert OptionStatus.INITIALIZED in test_option.status


def test_option_init_with_extended_properties(option_id, ticker, test_expiration, test_quote_date, standard_fee):
    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest, rho, iv = (95, 1.0, 2.0, 1.5,
                                                                                      0.3459, -0.1234, 0.0485,
                                                                                      0.0935, 100, 0.132, 0.3301)
    strike = 100

    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.CALL, quote_date=test_quote_date, spot_price=spot_price,
                         bid=bid, ask=ask, price=price, open_interest=open_interest, implied_volatility=iv,
                         delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho, fee_per_contract=standard_fee)

    assert test_option.option_id == option_id
    assert test_option.symbol == ticker
    assert test_option.strike == strike
    assert test_option.expiration == test_expiration
    assert test_option.bid == bid
    assert test_option.ask == ask
    assert test_option.price == price
    assert test_option.quote_date == test_quote_date

    assert test_option.delta == delta
    assert test_option.gamma == gamma
    assert test_option.theta == theta
    assert test_option.vega == vega
    assert test_option.rho == rho

    assert test_option.implied_volatility == iv
    assert test_option.open_interest == open_interest

    assert test_option.fee_per_contract == standard_fee
    assert OptionStatus.INITIALIZED in test_option.status


def test_option_set_user_defined_attributes(option_id, ticker, test_expiration, test_quote_date):
    strike = 100
    test_value_1 = 'test value 1'
    test_value_2 = 100

    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest, rho, iv = (95, 1.0, 2.0, 1.5,
                                                                                      0.3459, -0.1234, 0.0485,
                                                                                      0.0935, 100, 0.132, 0.3301)

    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.CALL, quote_date=test_quote_date, spot_price=spot_price,
                         bid=bid, ask=ask, price=price, open_interest=open_interest,
                         implied_volatility=iv, delta=delta, gamma=gamma,
                         theta=theta, vega=vega, rho=rho,
                         user_defined={'user_defined1': test_value_1, 'user_defined2': test_value_2})

    assert test_option.user_defined['user_defined1'] == test_value_1
    assert test_option.user_defined['user_defined2'] == test_value_2


def test_option_init_raises_exception_if_missing_required_fields(option_id, ticker, test_expiration):
    # missing id
    none_id = None
    with pytest.raises(ValueError, match="option_id cannot be None"):
        Option(option_id=none_id, symbol=ticker, strike=100, expiration=test_expiration, option_type=OptionType.CALL)

    # missing ticker symbol

    none_symbol = None
    with pytest.raises(ValueError, match="symbol cannot be None"):
        Option(option_id=option_id, symbol=none_symbol, strike=100, expiration=test_expiration,
               option_type=OptionType.CALL)

    # missing strike
    none_strike = None
    with pytest.raises(ValueError, match="strike cannot be None"):
        Option(option_id=option_id, symbol=ticker, strike=none_strike, expiration=test_expiration,
               option_type=OptionType.CALL)

    # missing expiration
    none_expiration = None
    with pytest.raises(ValueError, match="expiration cannot be None"):
        Option(option_id=option_id, symbol=ticker, strike=100, expiration=none_expiration, option_type=OptionType.CALL)

    # missing option type
    none_option_type = None
    with pytest.raises(ValueError, match="option_type cannot be None"):
        Option(option_id=option_id, symbol=ticker, strike=100, expiration=test_expiration, option_type=none_option_type)


def test_option_init_raises_exception_if_quote_date_is_greater_than_expiration(option_id, ticker, test_expiration):
    bad_open_date = datetime.datetime.strptime("2021-07-17 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    strike = 100
    spot_price, bid, ask, price = (95, 1.0, 2.0, 1.5)
    with pytest.raises(Exception, match="Cannot create an option with a quote date past its expiration date"):
        Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
               option_type=OptionType.CALL, quote_date=bad_open_date,
               spot_price=spot_price, bid=bid, ask=ask, price=price)


@pytest.mark.parametrize("option_type, expected_repr", [
    (OptionType.CALL, '<CALL XYZ 100.0 2021-07-16>'),
    (OptionType.PUT, '<PUT XYZ 100.0 2021-07-16>')])
def test_call_option_string_representation(get_test_call_option, get_test_put_option, option_type, expected_repr):
    test_option = get_test_call_option if option_type == OptionType.CALL else get_test_put_option
    assert str(test_option) == expected_repr


def test_update_sets_correct_values(option_id, test_expiration, test_quote_date, ticker, strike,
                                    test_update_quote_date):
    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.CALL)
    assert OptionStatus.CREATED in test_option.status

    spot_price, bid, ask, price, delta, gamma, theta, vega, open_interest, rho, iv = \
        (95, 3.4, 3.50, 3.45, 0.4714, 0.1239, -0.0401, 0.1149, 1000, 0.279, 0.3453)
    test_value_1 = 'test value 1'
    test_value_2 = 100
    test_option.update(quote_date=test_update_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price,
                       delta=delta, gamma=gamma, theta=theta, vega=vega,
                       rho=rho, implied_volatility=iv,
                       open_interest=open_interest, user_defined1=test_value_1, user_defined2=test_value_2)

    assert test_option.spot_price == spot_price
    assert test_option.quote_date == test_update_quote_date
    assert test_option.bid == bid
    assert test_option.ask == ask
    assert test_option.delta == delta
    assert test_option.gamma == gamma
    assert test_option.theta == theta
    assert test_option.vega == vega
    assert test_option.rho == rho
    assert test_option.open_interest == open_interest
    assert test_option.implied_volatility == iv
    assert test_option.user_defined['user_defined1'] == test_value_1
    assert test_option.user_defined['user_defined2'] == test_value_2
    assert OptionStatus.INITIALIZED in test_option.status


def test_update_raises_exception_if_missing_required_fields(get_test_call_option, test_update_quote_date):
    test_option = get_test_call_option

    # quote_date
    none_quote_date = None
    with pytest.raises(ValueError, match="quote_date cannot be None"):
        test_option.update(quote_date=none_quote_date, spot_price=90.0, bid=1.0, ask=2.0, price=1.5)

    # spot price
    none_spot_price = None
    with pytest.raises(ValueError, match="spot_price cannot be None"):
        test_option.update(quote_date=test_update_quote_date, spot_price=none_spot_price, bid=1.0, ask=2.0, price=1.5)

    # bid
    none_bid = None
    with pytest.raises(ValueError, match="bid cannot be None"):
        test_option.update(quote_date=test_update_quote_date, spot_price=90.0, bid=none_bid, ask=2.0, price=1.5)

    # ask
    none_ask = None
    with pytest.raises(ValueError, match="ask cannot be None"):
        test_option.update(quote_date=test_update_quote_date, spot_price=90.0, bid=1.0, ask=none_ask, price=1.5)

    # price
    none_price = None
    with pytest.raises(ValueError, match="price cannot be None"):
        test_option.update(quote_date=test_update_quote_date, spot_price=90.0, bid=1.0, ask=2.0, price=none_price)


def test_update_raises_exception_if_quote_date_is_greater_than_expiration(get_test_put_option):
    bad_quote_date = datetime.datetime.strptime("2021-07-17 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    test_option = get_test_put_option
    spot_price, bid, ask, price = (105, 1.0, 2.0, 1.5)
    with pytest.raises(Exception, match="Cannot update to a date past the option expiration"):
        test_option.update(quote_date=bad_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)


def test_open_trade_sets_correct_trade_open_info_values(get_test_call_option, test_quote_date):
    test_option = get_test_call_option
    assert test_option.status == OptionStatus.INITIALIZED
    quantity = 10

    trade_open_info = test_option.open_trade(quantity=quantity, comment="my super insightful comment")
    assert trade_open_info.date == test_quote_date
    assert trade_open_info.quantity == 10
    assert trade_open_info.price == 1.5
    assert trade_open_info.premium == 1_500.0
    assert test_option.quantity == 10
    assert OptionStatus.TRADE_IS_OPEN in test_option.status

    # kwargs were set as user_defined items
    assert test_option.user_defined['comment'] == "my super insightful comment"


def test_option_that_is_not_open_has_none_position_type(get_test_call_option):
    test_option = get_test_call_option
    assert test_option.position_type is None


@pytest.mark.parametrize("quantity, position_type", [(10, OptionPositionType.LONG), (-10, OptionPositionType.SHORT)])
def test_open_trade_has_correct_position_type(get_test_call_option, quantity, position_type):
    test_option = get_test_call_option
    test_option.open_trade(quantity=quantity)

    assert test_option.position_type == position_type


@pytest.mark.parametrize("option_type, quantity, expected_premium", [
    (OptionType.CALL, 10, 1_500.0),
    (OptionType.CALL, 5, 750.0),
    (OptionType.CALL, -10, -1_500.0),
    (OptionType.PUT, 10, 1_500.0),
    (OptionType.PUT, -10, -1_500.0),
    (OptionType.PUT, 5, 750.0),
])
def test_open_trade_returns_correct_premium_value(get_test_call_option, get_test_put_option, option_type, quantity,
                                                  expected_premium):
    test_option = get_test_call_option if option_type == OptionType.CALL else get_test_put_option
    trade_open_info = test_option.open_trade(quantity=quantity)
    assert trade_open_info.premium == expected_premium


@pytest.mark.parametrize("quantity, incur_fees, expected_fees", [(10, True, 5.0), (2, True, 1.0), (-3, True, 1.5),
                                                                 (10, False, 0.0), (2, False, 0.0),
                                                                 (-3, False, 0.0)])
def test_open_trade_sets_total_fees_when_incur_fees_is_true(get_test_call_option, standard_fee, quantity,
                                                            incur_fees, expected_fees):
    test_option = get_test_call_option
    test_option.fee_per_contract = standard_fee
    test_option.incur_fees = incur_fees
    test_option.open_trade(quantity=quantity)

    assert test_option.total_fees == expected_fees


def test_open_trade_when_quote_data_not_initialized_raises_exception(option_id, ticker, test_expiration):
    test_option = Option(option_id=option_id, symbol=ticker, strike=100, expiration=test_expiration,
                         option_type=OptionType.CALL)
    assert OptionStatus.CREATED in test_option.status
    with pytest.raises(ValueError, match="Cannot open a position that does not have price data"):
        test_option.open_trade(quantity=1)


@pytest.mark.parametrize("quantity", [None, 1.5, 0, -1.5, "abc"])
def test_open_trade_with_invalid_quantity_raises_exception(get_test_call_option, quantity):
    test_option = get_test_call_option

    with pytest.raises(ValueError, match="Quantity must be a non-zero integer."):
        test_option.open_trade(quantity=quantity)


def test_open_trade_when_trade_is_already_open_raises_exception(get_test_call_option):
    test_option = get_test_call_option
    quantity = 10
    test_option.open_trade(quantity=quantity)
    assert OptionStatus.TRADE_IS_OPEN in test_option.status

    with pytest.raises(ValueError, match="Cannot open position. A position is already open."):
        test_option.open_trade(quantity=quantity)


@pytest.mark.parametrize("quantity, close_quantity, remaining_quantity, status", [
    (10, 8, 2, OptionStatus.TRADE_PARTIALLY_CLOSED), (-10, -8, -2, OptionStatus.TRADE_PARTIALLY_CLOSED),
    (10, None, 0, OptionStatus.TRADE_IS_CLOSED), (-10, None, 0, OptionStatus.TRADE_IS_CLOSED)])
def test_close_partial_or_full_trade(get_test_call_option, quantity, close_quantity, remaining_quantity, status):
    test_option = get_test_call_option
    test_option.open_trade(quantity=quantity)
    test_option.close_trade(quantity=close_quantity)

    assert test_option.quantity == remaining_quantity
    assert status in test_option.status


@pytest.mark.parametrize("open_qty, close1_qty, close2_qty, expected_qty", [(10, 2, 8, 0), (10, 2, 3, 5),
                                                                            (-10, -2, -8, 0), (-10, -2, -3, -5)])
def test_close_trade_with_multiple_partial_close(get_test_call_option, open_qty, close1_qty, close2_qty, expected_qty):
    test_option = get_test_call_option
    test_option.open_trade(quantity=open_qty)

    test_option.close_trade(quantity=close1_qty)
    test_option.close_trade(quantity=close2_qty)

    assert test_option.quantity == expected_qty


@pytest.mark.parametrize("open_quantity, close_quantity", [(10, 12), (-10, -12)])
def test_close_trade_with_greater_than_quantity_open_raises_exception(get_test_call_option, open_quantity,
                                                                      close_quantity):
    test_option = get_test_call_option
    test_option.open_trade(quantity=open_quantity)

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        test_option.close_trade(quantity=close_quantity)


@pytest.mark.parametrize("open_qty, close1_qty, close2_qty", [(10, 6, 6), (10, 9, 2), (-10, -7, -4), (-10, -9, -2)])
def test_close_partial_trade_with_greater_than_remaining_quantity_raises_exception(get_test_call_option, open_qty,
                                                                                   close1_qty, close2_qty):
    test_option = get_test_call_option
    test_option.open_trade(quantity=open_qty)
    test_option.close_trade(quantity=close1_qty)  # close partial trade

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        test_option.close_trade(quantity=close2_qty)


@pytest.mark.parametrize("incur_fees_flag, open_quantity, close_quantity, fee_amount", [(True, 10, 10, 10.0),
                                                                                        (True, -10, -10, 10.0),
                                                                                        (True, 10, 2, 6.0),
                                                                                        (False, 10, 10, 0.0),
                                                                                        (False, -10, -10, 0.0),
                                                                                        (False, -10, -2, 0.0)])
def test_close_trade_updates_total_fees_incur_fees_flag(get_test_call_option, standard_fee, incur_fees_flag,
                                                        open_quantity, close_quantity, fee_amount):
    test_option = get_test_call_option
    test_option.fee_per_contract = standard_fee
    test_option.incur_fees = incur_fees_flag
    test_option.open_trade(quantity=open_quantity)
    test_option.close_trade(quantity=close_quantity)

    assert test_option.total_fees == fee_amount


@pytest.mark.parametrize("open_qty, close_qty, expected_qty, close_dt, close_pnl, close_pnl_pct, close_fees, status", [
    (10, 10, -10, None, 8_500.0, 5.6667, 5.0, OptionStatus.TRADE_IS_CLOSED),
    (-10, -10, 10, None, -8_500.0, -5.6667, 5.0, OptionStatus.TRADE_IS_CLOSED),
    (10, 1, -1, None, 850.0, 5.6667, 0.5, OptionStatus.TRADE_PARTIALLY_CLOSED),
    (-10, -5, 5, None, -4_250.0, -5.6667, 2.5, OptionStatus.TRADE_PARTIALLY_CLOSED)
])
def test_close_trade_values_with_one_close_trade(get_test_call_option, standard_fee,
                                                 get_test_call_option_update_values_1, open_qty, close_qty,
                                                 expected_qty, close_dt, close_pnl,
                                                 close_pnl_pct, close_fees, status):
    test_option = get_test_call_option
    test_option.fee_per_contract = standard_fee
    test_option.open_trade(quantity=open_qty)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    trade_close_info = test_option.close_trade(quantity=close_qty)

    assert trade_close_info.date == quote_date
    assert trade_close_info.quantity == close_qty * -1
    assert trade_close_info.price == price
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.profit_loss_percent == close_pnl_pct
    assert trade_close_info.fees == close_fees
    assert status in test_option.status


@pytest.mark.parametrize(
    "open_qty, cqty1, cqty2, close_price, close_pnl, pnl_pct, close_fees, closed_qty, remaining_qty",
    [(10, 2, 3, 7.0, 2_750.0, 1.8333, 2.5, -5, 5),
     (-10, -3, -5, 6.88, -4_300, -2.8667, 4.0, 8, -2),
     (10, 8, 1, 9.44, 7_150.0, 4.7667, 4.5, -9, 1),
     (-10, -1, -1, 7.5, -1_200.0, -0.8000, 1.0, 2, -8)
     ])
def test_call_option_close_trade_values_with_multiple_close_trades(
        test_update_quote_date2,
        get_test_call_option,
        get_test_call_option_update_values_1,
        get_test_call_option_update_values_2,
        standard_fee, open_qty, cqty1, cqty2, close_price, close_pnl, pnl_pct, close_fees, closed_qty, remaining_qty):
    close_date = test_update_quote_date2
    test_option = get_test_call_option
    test_option.fee_per_contract = standard_fee
    test_option.open_trade(quantity=open_qty)
    # first update
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=cqty1)

    # second update
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_2
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=cqty2)

    # get close info for closed trades
    trade_close_info = test_option.trade_close_info
    assert trade_close_info.date == close_date
    assert trade_close_info.price == close_price
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.fees == close_fees

    assert trade_close_info.quantity == closed_qty
    assert test_option.quantity == remaining_qty
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in test_option.status
    assert OptionStatus.TRADE_IS_OPEN in test_option.status


@pytest.mark.parametrize(
    "open_qty, cqty1, cqty2, close_price, close_pnl, pnl_pct, close_fees, closed_qty, remaining_qty",
    [(10, 2, 3, 7.0, 2_750.0, 1.8333, 2.5, -5, 5),
     (-10, -3, -5, 6.88, -4_300, -2.8667, 4.0, 8, -2),
     (10, 8, 1, 9.44, 7_150.0, 4.7667, 4.5, -9, 1),
     (-10, -1, -1, 7.5, -1_200.0, -0.8000, 1.0, 2, -8)
     ])
def test_put_option_close_trade_values_with_multiple_close_trades(test_update_quote_date2, get_test_put_option,
                                                                  get_test_put_option_update_values_1,
                                                                  get_test_put_option_update_values_2, standard_fee,
                                                                  open_qty, cqty1, cqty2, close_price,
                                                                  close_pnl, pnl_pct, close_fees,
                                                                  closed_qty, remaining_qty):
    close_date = test_update_quote_date2
    test_option = get_test_put_option
    test_option.fee_per_contract = standard_fee
    test_option.open_trade(quantity=open_qty)
    # first update
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=cqty1)

    # second update
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_2
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=cqty2)

    # get close info for closed trades
    trade_close_info = test_option.trade_close_info
    assert trade_close_info.date == close_date
    assert trade_close_info.price == close_price
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.fees == close_fees

    assert trade_close_info.quantity == closed_qty
    assert test_option.quantity == remaining_qty
    assert OptionStatus.TRADE_IS_OPEN in test_option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in test_option.status


def test_trade_close_records_returns_all_close_trades(get_test_call_option, get_test_call_option_update_values_1,
                                                      get_test_call_option_update_values_2):
    test_option = get_test_call_option
    test_option.open_trade(quantity=10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    test_option.close_trade(quantity=3)

    records = test_option.trade_close_records
    assert len(records) == 1

    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_2
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=6)

    records = test_option.trade_close_records
    assert len(records) == 2


def test_total_fees_returns_all_fees_incurred(option_id, ticker, test_expiration, test_quote_date, standard_fee,
                                              get_test_call_option_update_values_1):
    strike, spot_price, bid, ask, price = (100, 90, 1.0, 2.0, 1.5)
    test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                         option_type=OptionType.CALL,
                         quote_date=test_quote_date, spot_price=spot_price, bid=bid,
                         ask=ask, price=price, fee_per_contract=standard_fee)  # add fee when creating option object

    test_option.open_trade(quantity=10)

    assert test_option.total_fees == 5.0

    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=2)

    assert test_option.total_fees == 6.0

    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=3)

    assert test_option.total_fees == 7.5


def test_get_closing_price(get_test_call_option, get_test_call_option_update_values_1):
    test_option = get_test_call_option
    test_option.open_trade(quantity=1)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    expected_close_price = 10.0

    close_price = test_option.get_closing_price()

    assert close_price == expected_close_price


def test_get_close_price_on_option_that_has_not_been_traded_raises_exception(get_test_call_option,
                                                                             get_test_call_option_update_values_1):
    test_option = get_test_call_option
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    with pytest.raises(ValueError,
                       match="Cannot determine closing price on option that does not have an opening trade"):
        test_option.get_closing_price()


@pytest.mark.parametrize("open_qty, expected_closing_price", [
    (1, 0.0), (-1, 0.05)
])
def test_get_closing_price_on_call_option_when_bid_is_zero(open_qty, expected_closing_price, get_test_call_option,
                                                           get_test_call_option_update_values_1,
                                                           get_test_call_option_update_values_3):
    test_option = get_test_call_option
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    # open trade
    test_option.open_trade(quantity=open_qty)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_3
    assert bid == 0.0
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    assert test_option.get_closing_price() == expected_closing_price


@pytest.mark.parametrize("open_qty, expected_closing_price", [
    (1, 0.0), (-1, 0.05)
])
def test_get_closing_price_on_put_option_when_bid_is_zero(open_qty, expected_closing_price, get_test_put_option,
                                                          get_test_put_option_update_values_1,
                                                          get_test_put_option_update_values_3):
    test_option = get_test_put_option
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    # open trade
    test_option.open_trade(quantity=open_qty)
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_3
    assert bid == 0.0
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    assert test_option.get_closing_price() == expected_closing_price


@pytest.mark.parametrize("option_type", [OptionType.CALL, OptionType.PUT])
def test_call_option_get_close_price_is_zero_when_option_expires_otm(get_test_put_option,
                                                                     get_test_call_option,
                                                                     get_test_put_option_update_values_3,
                                                                     get_test_call_option_update_values_3,
                                                                     at_expiration_quote_date, option_type):
    test_option = get_test_put_option if option_type == OptionType.PUT else get_test_call_option
    test_option.open_trade(quantity=1)
    _, spot_price, bid, ask, price = get_test_put_option_update_values_3 if option_type == OptionType.PUT \
        else get_test_call_option_update_values_3
    test_option.update(quote_date=at_expiration_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    assert test_option.otm()
    assert test_option.price != 0.0
    assert test_option.get_closing_price() == 0.0


def test_dte_is_none_when_option_does_not_have_quote_data(option_id, ticker, test_expiration):
    test_option = Option(option_id=option_id, symbol=ticker, strike=100, expiration=test_expiration,
                         option_type=OptionType.CALL)

    assert test_option.dte() is None


def test_dte_when_option_has_quote_data(get_test_call_option):
    test_option = get_test_call_option

    expected_dte = 15
    actual_dte = test_option.dte()
    assert actual_dte == expected_dte


def test_dte_is_updated_when_quote_date_is_updated(get_test_call_option, get_test_put_option_update_values_1):
    test_option = get_test_call_option
    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    expected_dte = 14
    assert test_option.dte() == expected_dte


@pytest.mark.parametrize("expiration_datetime",
                         [datetime.datetime.strptime("2021-07-16 09:31:00.000000", "%Y-%m-%d %H:%M:%S.%f"),
                          datetime.datetime.strptime("2021-07-16 11:00:00.000000", "%Y-%m-%d %H:%M:%S.%f"),
                          datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f")])
def test_dte_is_zero_on_expiration_day(get_test_call_option, get_test_put_option_update_values_1, expiration_datetime):
    test_option = get_test_call_option
    _, spot_price, bid, ask, price = get_test_put_option_update_values_1
    test_option.update(quote_date=expiration_datetime, spot_price=spot_price, bid=bid, ask=ask, price=price)

    expected_dte = 0
    assert test_option.dte() == expected_dte


def test_otm_and_itm_equal_none_when_option_does_not_have_quote_data(option_id, ticker, test_expiration):
    test_option = Option(option_id=option_id, symbol=ticker, strike=100, expiration=test_expiration,
                         option_type=OptionType.CALL)

    assert test_option.itm() is None
    assert test_option.otm() is None


@pytest.mark.parametrize("option_type, spot_price, strike, expected_value", [
    (OptionType.CALL, 99.99, 100.0, True), (OptionType.CALL, 100.0, 100.0, False),
    (OptionType.CALL, 100.01, 100.0, False),
    (OptionType.PUT, 99.99, 100.0, False), (OptionType.PUT, 100.0, 100.0, False),
    (OptionType.PUT, 100.01, 100.0, True)])
def test_call_option_otm(option_id, ticker, test_expiration, test_quote_date, option_type, spot_price, strike,
                         expected_value):
    bid, ask, price = (9.50, 10.5, 10.00)
    test_option = Option(option_id=option_id, symbol=ticker, strike=100, expiration=test_expiration,
                         option_type=option_type,
                         quote_date=test_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    actual_value = test_option.otm()
    assert actual_value == expected_value


@pytest.mark.parametrize("option_type, spot_price, strike, expected_value", [
    (OptionType.CALL, 99.99, 100.0, False), (OptionType.CALL, 100.0, 100.0, True),
    (OptionType.CALL, 100.01, 100.0, True),
    (OptionType.PUT, 99.99, 100.0, True), (OptionType.PUT, 100.0, 100.0, True),
    (OptionType.PUT, 100.01, 100.0, False)])
def test_call_option_itm(option_id, ticker, test_expiration, test_quote_date, option_type, spot_price, strike,
                         expected_value):
    bid, ask, price = (9.50, 10.5, 10.00)
    test_option = Option(option_id=option_id, symbol=ticker, strike=100, expiration=test_expiration,
                         option_type=option_type,
                         quote_date=test_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    actual_value = test_option.itm()
    assert actual_value == expected_value


def test_set_expired_does_not_set_expired_flag_when_no_quote_data(option_id, ticker, test_expiration):
    test_option = Option(option_id=option_id, symbol=ticker, strike=100, expiration=test_expiration,
                         option_type=OptionType.CALL)

    test_option._set_expired()
    assert OptionStatus.EXPIRED not in test_option.status


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
def test_set_expired_sets_expired_flag_correctly(get_test_put_option, ticker, get_test_put_option_update_values_1,
                                                 expiration_date_test, quote_date, expected_result):
    test_option = get_test_put_option
    test_option.expiration = expiration_date_test

    _, spot_price, bid, ask, price = get_test_put_option_update_values_1
    test_option.quote_datetime = quote_date
    test_option.spot_price = spot_price
    test_option.bid = bid
    test_option.ask = ask
    test_option.price = price

    assert OptionStatus.EXPIRED not in test_option.status

    test_option._set_expired()

    assert (OptionStatus.EXPIRED in test_option.status) == expected_result


def test_is_trade_is_open_status_if_no_trade_was_opened(get_test_call_option):
    test_option = get_test_call_option
    assert (OptionStatus.TRADE_IS_OPEN in test_option.status) == False


def test_trade_is_open_status_is_true_if_trade_was_opened(get_test_call_option):
    test_option = get_test_call_option
    test_option.open_trade(quantity=10)
    assert (OptionStatus.TRADE_IS_OPEN in test_option.status) == True


def test_trade_is_open_status_is_true_if_partially_closed(get_test_call_option):
    test_option = get_test_call_option
    test_option.open_trade(quantity=10)
    test_option.close_trade(quantity=5)
    assert (OptionStatus.TRADE_IS_OPEN in test_option.status) == True


def test_trade_is_open_is_false_if_closed(get_test_call_option):
    test_option = get_test_call_option
    test_option.open_trade(quantity=10)
    test_option.close_trade(quantity=10)
    assert (OptionStatus.TRADE_IS_OPEN in test_option.status) == False


def test_get_unrealized_profit_loss_raises_exception_if_trade_was_not_opened(get_test_call_option):
    test_option = get_test_call_option

    with pytest.raises(Exception, match="This option has no transactions."):
        test_option.get_unrealized_profit_loss()


def test_get_unrealized_profit_loss_is_zero_if_quote_data_has_not_changed(get_test_call_option):
    test_option = get_test_call_option
    test_option.open_trade(quantity=10)
    pnl = test_option.get_unrealized_profit_loss()
    assert pnl == 0.0


def test_get_unrealized_profit_loss_is_zero_when_trade_is_closed(get_test_call_option,
                                                                 get_test_call_option_update_values_1):
    test_option = get_test_call_option
    test_option.open_trade(quantity=10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=10)

    pnl = test_option.get_unrealized_profit_loss()

    assert pnl == 0.0


@pytest.mark.parametrize("option_type, quantity, price, expected_profit_loss", [
    (OptionType.CALL, 10, 1.6, 100.0),
    (OptionType.CALL, 10, 1.4, -100.0),
    (OptionType.CALL, 10, 1.5, 0.0),
    (OptionType.CALL, -10, 1.6, -100.0),
    (OptionType.CALL, -10, 1.4, 100.0),
    (OptionType.CALL, -10, 1.5, 0.0),
    (OptionType.PUT, 10, 1.6, 100.0),
    (OptionType.PUT, 10, 1.4, -100.0),
    (OptionType.PUT, 10, 1.5, 0.0),
    (OptionType.PUT, -10, 1.6, -100.0),
    (OptionType.PUT, -10, 1.4, 100.0),
    (OptionType.PUT, -10, 1.5, 0.0)
])
def test_get_unrealized_profit_loss_value(get_test_call_option, get_test_put_option,
                                          get_test_call_option_update_values_1,
                                          option_type, quantity, price, expected_profit_loss):
    test_option = get_test_call_option if option_type == OptionType.CALL else get_test_put_option
    test_option.open_trade(quantity=quantity)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    actual_profit_loss = test_option.get_unrealized_profit_loss()
    assert actual_profit_loss == expected_profit_loss


def test_unrealized_profit_loss_percent_raises_exception_if_trade_was_not_opened(get_test_call_option):
    test_option = get_test_call_option

    with pytest.raises(Exception, match="This option has no transactions."):
        test_option.get_unrealized_profit_loss_percent()


def test_get_unrealized_profit_loss_percent_returns_zero_when_trade_is_closed(get_test_call_option):
    test_option = get_test_call_option
    test_option.open_trade(quantity=1)
    test_option.close_trade(quantity=1)

    actual_value = test_option.get_unrealized_profit_loss_percent()
    assert actual_value == 0.0


@pytest.mark.parametrize("option_type, quantity, price, expected_profit_loss_pct", [
    (OptionType.CALL, 10, 2.25, 0.5),
    (OptionType.CALL, 10, 1.17, -0.22),
    (OptionType.CALL, 10, 1.5, 0.0),
    (OptionType.CALL, -10, 2.25, -0.50),
    (OptionType.CALL, -10, 1.17, 0.22),
    (OptionType.CALL, -10, 1.5, 0.0),
    (OptionType.PUT, 10, 2.25, 0.5),
    (OptionType.PUT, 10, 1.17, -0.22),
    (OptionType.PUT, 10, 1.5, 0.0),
    (OptionType.PUT, -10, 2.25, -0.50),
    (OptionType.PUT, -10, 1.17, 0.22),
    (OptionType.PUT, -10, 1.5, 0.0)
])
def test_get_unrealized_profit_loss_percent_value(get_test_call_option, get_test_put_option,
                                                  get_test_call_option_update_values_1,
                                                  option_type, quantity, price, expected_profit_loss_pct):
    test_option = get_test_call_option if option_type == OptionType.CALL else get_test_put_option
    test_option.open_trade(quantity=quantity)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    actual_profit_loss = test_option.get_unrealized_profit_loss_percent()
    assert actual_profit_loss == expected_profit_loss_pct


@pytest.mark.parametrize("quote_date, expected_days_in_trade", [
    (datetime.datetime.strptime("2021-07-01 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 0),
    (datetime.datetime.strptime("2021-07-01 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 0),
    (datetime.datetime.strptime("2021-07-07 11:14:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 6),
    (datetime.datetime.strptime("2021-07-13 10:53:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 12),
    (datetime.datetime.strptime("2021-07-15 10:05:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 14),
    (datetime.datetime.strptime("2021-07-16 16:15:00.000000", "%Y-%m-%d %H:%M:%S.%f"), 15)
])
def test_get_days_in_trade(get_test_call_option_update_values_1, get_test_call_option, quote_date,
                           expected_days_in_trade):
    test_option = get_test_call_option
    test_option.open_trade(quantity=1)

    _, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    days_in_trade = test_option.get_days_in_trade()
    assert days_in_trade == expected_days_in_trade


def test_get_profit_loss_raises_exception_if_not_traded(get_test_call_option):
    test_option = get_test_call_option

    with pytest.raises(Exception, match="This option has not been traded."):
        test_option.get_profit_loss()


@pytest.mark.parametrize("option_type, qty, price, expected_value", [
    (OptionType.CALL, 10, 2.0, 500.0),
    (OptionType.CALL, -10, 2.0, -500.0),
    (OptionType.PUT, 10, 2.0, 500.0),
    (OptionType.PUT, -10, 2.0, -500.0),
])
def test_get_total_profit_loss_returns_unrealized_when_no_contracts_are_closed(get_test_call_option,
                                                                               get_test_put_option,
                                                                               get_test_call_option_update_values_1,
                                                                               option_type, qty, price, expected_value):
    test_option = get_test_call_option if option_type == OptionType.CALL else get_test_put_option
    test_option.open_trade(quantity=qty)

    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    actual_value = test_option.get_profit_loss()
    assert actual_value == expected_value


def test_get_profit_loss_returns_closed_pnl_when_all_contracts_are_closed(get_test_call_option,
                                                                          get_test_call_option_update_values_1):
    test_option = get_test_call_option
    test_option.open_trade(quantity=10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=10)

    assert test_option.get_profit_loss() == 8_500.0


def test_get_profit_loss_returns_unrealized_and_closed_pnl_when_partially_closed(get_test_call_option,
                                                                                 get_test_call_option_update_values_1,
                                                                                 get_test_call_option_update_values_2):
    test_option = get_test_call_option
    test_option.open_trade(quantity=10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(5)  # 4250
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_2
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)  # 1750

    assert test_option.get_profit_loss() == 6_000.0


def test_get_total_profit_loss_returns_unrealized_and_closed_pnl_when_multiple_close_trades(
        get_test_call_option,
        get_test_call_option_update_values_1,
        get_test_call_option_update_values_2):
    test_option = get_test_call_option
    test_option.open_trade(quantity=10)
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=3)  # 2550
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_2
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=3)  # 1050
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_2
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=8.0)  # 2600

    actual_value = test_option.get_profit_loss()
    assert actual_value == 6_200.0


def test_get_profit_loss_percent_raises_exception_if_not_traded(get_test_call_option):
    test_option = get_test_call_option

    with pytest.raises(Exception, match="This option has not been traded."):
        test_option.get_profit_loss_percent()


@pytest.mark.parametrize("option_type, qty, price, expected_value", [
    (OptionType.CALL, 10, 1.8, 0.2),
    (OptionType.CALL, -10, 1.8, -0.2),
    (OptionType.PUT, 10, 1.8, 0.2),
    (OptionType.PUT, -10, 1.8, -0.2),
])
def test_get_profit_loss_percent_returns_unrealized_when_no_contracts_are_closed(
        get_test_call_option, get_test_put_option, get_test_call_option_update_values_1, option_type, qty, price,
        expected_value):
    test_option = get_test_call_option if option_type == OptionType.CALL else get_test_put_option
    test_option.open_trade(quantity=qty)

    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    actual_value = test_option.get_profit_loss_percent()
    assert actual_value == expected_value


@pytest.mark.parametrize("option_type, qty, price, expected_value", [
    (OptionType.CALL, 10, 1.8, 0.2),
    (OptionType.CALL, -10, 1.8, -0.2),
    (OptionType.PUT, 10, 1.8, 0.2),
    (OptionType.PUT, -10, 1.8, -0.2),
])
def test_get_total_profit_loss_percent_returns_closed_pnl_when_all_contracts_are_closed(get_test_call_option,
                                                                                        get_test_put_option,
                                                                                        get_test_call_option_update_values_1,
                                                                                        option_type, qty, price,
                                                                                        expected_value):
    test_option = get_test_call_option if option_type == OptionType.CALL else get_test_put_option
    test_option.open_trade(quantity=qty)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    test_option.close_trade(quantity=qty)

    assert test_option.get_profit_loss_percent() == expected_value


@pytest.mark.parametrize(" qty, close_qty_1, close_qty_2, price1, price2, price3, expected_value", [
    (10, 4, 2, 1.8, 2.2, 0.10, -0.2),
    (-10, -4, -2, 1.8, 2.2, 0.10, 0.2),
    (10, 4, 2, 3.0, 4.5, 6, 2.0),
    (-10, -4, -2, 3.0, 4.5, 6, -2.0),
])
def test_get_total_profit_loss_percent_returns_unrealized_and_closed_pnl_when_multiple_close_trades(
        get_test_call_option, get_test_call_option_update_values_1, get_test_call_option_update_values_2, qty,
        close_qty_1,
        close_qty_2,
        price1, price2,
        price3,
        expected_value):
    test_option = get_test_call_option
    test_option.open_trade(quantity=qty)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_1
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price1)
    test_option.close_trade(quantity=close_qty_1)
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_2
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price2)
    test_option.close_trade(quantity=close_qty_2)  # 1050
    quote_date, spot_price, bid, ask, _ = get_test_call_option_update_values_2
    test_option.update(quote_date=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price3)  # 2600

    actual_value = test_option.get_profit_loss_percent()
    assert actual_value == expected_value


def test_single_option_properties_return_none_when_no_quote_data(option_id, ticker, strike, test_expiration):
    test_option = test_option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=test_expiration,
                                       option_type=OptionType.CALL)

    assert test_option.quote_date is None
    assert test_option.spot_price is None
    assert test_option.bid is None
    assert test_option.ask is None
    assert test_option.price is None

    assert test_option.delta is None
    assert test_option.gamma is None
    assert test_option.theta is None
    assert test_option.vega is None
    assert test_option.rho is None

    assert test_option.open_interest is None
    assert test_option.implied_volatility is None
