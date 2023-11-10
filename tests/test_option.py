import pytest

from options_framework_archive.option_types import OptionPositionType
import options_framework_archive.option as option
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
    test_option = get_test_call_option()

    # quote_date
    none_quote_date = None
    with pytest.raises(ValueError, match="quote_date is required"):
        test_option.update(quote_date=none_quote_date, spot_price=90.0, bid=1.0, ask=2.0, price=1.5)

    # spot price
    none_spot_price = None
    with pytest.raises(ValueError, match="spot_price is required"):
        test_option.update(quote_date=test_update_quote_date, spot_price=none_spot_price, bid=1.0, ask=2.0, price=1.5)

    # bid
    none_bid = None
    with pytest.raises(ValueError, match="bid is required"):
        test_option.update(quote_date=test_update_quote_date, spot_price=90.0, bid=none_bid, ask=2.0, price=1.5)

    # ask
    none_ask = None
    with pytest.raises(ValueError, match="ask is required"):
        test_option.update(quote_date=test_update_quote_date, spot_price=90.0, bid=1.0, ask=none_ask, price=1.5)

    # price
    none_price = None
    with pytest.raises(ValueError, match="price is required"):
        test_option.update(quote_date=test_update_quote_date, spot_price=90.0, bid=1.0, ask=2.0, price=none_price)


def test_update_raises_exception_if_quote_date_is_greater_than_expiration():
    bad_quote_date = datetime.datetime.strptime("2021-07-17 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    put = get_test_put_option()
    spot_price, bid, ask, price = (105, 1.0, 2.0, 1.5)
    with pytest.raises(Exception, match="Cannot update to a date past the option expiration"):
        put.update(bad_quote_date, spot_price, bid, ask, price)




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



def test_get_open_profit_loss_percent_raises_exception_if_trade_was_not_opened():
    test_option = get_test_call_option()

    with pytest.raises(Exception, match="No trade has been opened."):
        test_option.get_open_profit_loss_percent()


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




def test_single_option_properties_return_none_when_property_group_is_none():
    test_option = test_option = Option(id, ticker, 100.0, test_expiration, OptionType.CALL)

    assert test_option.option_quote is None
    assert test_option.quote_date is None
    assert test_option.spot_price is None
    assert test_option.bid is None
    assert test_option.ask is None
    assert test_option.price is None

    assert test_option.greeks is None
    assert test_option.delta is None
    assert test_option.gamma is None
    assert test_option.theta is None
    assert test_option.vega is None
    assert test_option.rho is None

    assert test_option.extended_properties is None
    assert test_option.open_interest is None
    assert test_option.implied_volatility is None


