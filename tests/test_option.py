import pytest
import copy
from dateutil import relativedelta
from options_framework.option import Option
from options_framework.option_types import OptionPositionType, OptionStatus
from options_framework.config import settings

from test_data.test_option_data import *


@pytest.fixture
def get_data():
    def get_options_data(option_id):
        all_data = daily_option_data
        select_data =  [x for x in all_data if x['option_id'] == option_id]
        return select_data
    return get_options_data

@pytest.fixture
def get_intraday_data():
    def get_options_data(option_id):
        all_data = intraday_option_data
        select_data = [x for x in all_data if x['option_id'] == option_id]
        return select_data

    return get_options_data


def test_option_init_with_quote_data(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    test_values = copy.deepcopy(call_data[1])

    test_option = Option(option_id=test_values['option_id'],
                         symbol=test_values['symbol'],
                         strike=test_values['strike'],
                         expiration=test_values['expiration'],
                         option_type=test_values['option_type'],
                         quote_datetime=test_values['quote_datetime'],
                         spot_price=test_values['spot_price'],
                         bid=test_values['bid'],
                         ask=test_values['ask'],
                         price=test_values['price'])

    assert test_option.option_id == 'AAPL20150117C00010000'
    assert test_option.symbol == 'AAPL'
    assert test_option.expiration == datetime.date(2015, 1, 17)
    assert test_option.strike == 100.0
    assert test_option.spot_price == 110.38
    assert test_option.bid == 10.7
    assert test_option.ask == 10.85
    assert test_option.price == 10.77
    assert test_option.quote_datetime == datetime.datetime(2014, 12, 31, 0, 0)


def test_option_init_with_extended_properties(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    test_values = copy.deepcopy(call_data[1])
    test_values['rho'] = 0.1234
    test_option = Option(option_id=test_values['option_id'], symbol=test_values['symbol'], strike=test_values['strike'],
                         expiration=test_values['expiration'], option_type=test_values['option_type'],
                         quote_datetime=test_values['quote_datetime'], spot_price=test_values['spot_price'],
                         bid=test_values['bid'], ask=test_values['ask'], price=test_values['price'],
                         open_interest=test_values['open_interest'], implied_volatility=test_values['implied_volatility'],
                         volume=test_values['volume'],delta=test_values['delta'], gamma=test_values['gamma'], theta=test_values['theta'],
                         vega=test_values['vega'], rho=test_values['rho'])

    assert test_option.delta == 0.8628
    assert test_option.gamma == 0.021
    assert test_option.theta == -25.8122
    assert test_option.vega == 5.1267
    assert test_option.rho == 0.1234

    assert test_option.implied_volatility == 0.447
    assert test_option.open_interest == 179345
    assert test_option.volume == 3345


def test_option_set_user_defined_attributes(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    test_values = copy.deepcopy(call_data[0])

    test_value_1 = 'first'
    test_value_2 = 'second'

    test_option = Option(option_id=test_values['option_id'], symbol=test_values['symbol'], strike=test_values['strike'],
                         expiration=test_values['expiration'], option_type=test_values['option_type'],
                         quote_datetime=test_values['quote_datetime'], spot_price=test_values['spot_price'],
                         bid=test_values['bid'], ask=test_values['ask'], price=test_values['price'],
                         user_defined={'user_defined1': test_value_1, 'user_defined2': test_value_2})

    assert test_option.user_defined['user_defined1'] == test_value_1
    assert test_option.user_defined['user_defined2'] == test_value_2


def test_option_init_raises_exception_if_missing_required_fields(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    test_values = copy.deepcopy(call_data[0])
    option_id = test_values['option_id']
    symbol = test_values['symbol']
    expiration = test_values['expiration']
    option_type = test_values['option_type']
    strike = test_values['strike']

    # missing id
    none_id = None
    with pytest.raises(ValueError, match="option_id cannot be None"):
        Option(option_id=none_id, symbol=symbol, strike=strike, expiration=expiration, option_type=option_type)

    # missing ticker symbol
    none_symbol = None
    with pytest.raises(ValueError, match="symbol cannot be None"):
        Option(option_id=option_id, symbol=none_symbol, strike=strike, expiration=expiration,
               option_type=option_id)

    # missing strike
    none_strike = None
    with pytest.raises(ValueError, match="strike cannot be None"):
        Option(option_id=option_id, symbol=symbol, strike=none_strike, expiration=expiration,
               option_type=option_type)

    # missing expiration
    none_expiration = None
    with pytest.raises(ValueError, match="expiration cannot be None"):
        Option(option_id=option_id, symbol=symbol, strike=strike, expiration=none_expiration, option_type=option_type)

    # missing option type
    none_option_type = None
    with pytest.raises(ValueError, match="option_type cannot be None"):
        Option(option_id=option_id, symbol=symbol, strike=strike, expiration=expiration, option_type=none_option_type)


def test_option_init_raises_exception_if_quote_date_is_greater_than_expiration(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    test_values = copy.deepcopy(call_data[0])

    bad_quote_date = test_values['quote_datetime'] + datetime.timedelta(days=100)

    with pytest.raises(Exception, match="Cannot create an option with a quote date past its expiration date"):
        Option(option_id=test_values['option_id'], symbol=test_values['symbol'], strike=test_values['strike'],
               expiration=test_values['expiration'], option_type=test_values['option_type'],
               quote_datetime=bad_quote_date, spot_price=test_values['spot_price'],
               bid=test_values['bid'], ask=test_values['ask'], price=test_values['price'])


def test_option_init_quote_datetime_raises_error_if_is_not_datetime_or_timestamp_type(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    test_values = copy.deepcopy(call_data[0])

    bad_quote_date = test_values['quote_datetime'].date()

    with pytest.raises(Exception, match="quote datetime must be python datetime.datetime or pandas Timestamp"):
        Option(option_id=test_values['option_id'], symbol=test_values['symbol'], strike=test_values['strike'],
               expiration=test_values['expiration'], option_type=test_values['option_type'],
               quote_datetime=bad_quote_date, spot_price=test_values['spot_price'],
               bid=test_values['bid'], ask=test_values['ask'], price=test_values['price'])

def test_option_update_quote_datetime_raises_error_if_is_not_datetime_or_timestamp_type(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    data = copy.deepcopy(call_data[0])
    call = Option(**data)

    update = copy.deepcopy(call_data[1])
    update['quote_datetime'] = update['quote_datetime'].date()

    with pytest.raises(Exception, match="Wrong format for option date. Must be python datetime.datetime. Date was provided in <class 'datetime.date'> format."):
        call.next(update)


@pytest.mark.parametrize("option_type, expected_repr", [
    ('call', '<CALL(AAPL20150117C00010000) AAPL 100.0 2015-01-17>'),
    ('put', '<PUT(AAPL20150117P00010000) AAPL 100.0 2015-01-17>')])
def test_string_representation(get_data, option_type, expected_repr):
    option_id = 'AAPL20150117C00010000' if option_type == 'call' else 'AAPL20150117P00010000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])
    option = Option(**option_data)

    assert str(option) == expected_repr


def test_update_sets_correct_values(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    call = Option(**option_data)
    update = copy.deepcopy(call_data[1])
    update['rho'] = 0.4321

    call.next(update)

    assert call.spot_price == update['spot_price']
    assert call.quote_datetime == update['quote_datetime']
    assert call.bid == update['bid']
    assert call.ask == update['ask']
    assert call.delta == update['delta']
    assert call.gamma == update['gamma']
    assert call.theta == update['theta']
    assert call.vega == update['vega']
    assert call.rho == update['rho']
    assert call.open_interest == update['open_interest']
    assert call.implied_volatility == update['implied_volatility']


def test_update_sets_expiration_status_if_quote_date_is_greater_than_expiration(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    call = Option(**option_data)
    update = copy.deepcopy(call_data[1])
    update['quote_datetime'] = update['quote_datetime'] + datetime.timedelta(days=call.dte() + 1)

    call.next(update)

    assert OptionStatus.EXPIRED in call.status


def test_open_trade_sets_correct_trade_open_info_values(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    call = Option(**option_data)
    quantity = 10

    trade_open_info = call.open_trade(quantity=quantity, comment="my super insightful comment",
                                      what="whatever")
    assert trade_open_info.date == call.quote_datetime
    assert trade_open_info.quantity == 10
    assert trade_open_info.price == 12.77
    assert trade_open_info.premium == 12_770.0
    assert call.quantity == 10
    assert OptionStatus.TRADE_IS_OPEN in call.status

    # kwargs were set as user_defined items
    assert call.user_defined['comment'] == "my super insightful comment"
    assert call.user_defined['what'] == "whatever"


def test_option_that_is_not_open_has_none_position_type(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    data = copy.deepcopy(call_data[0])
    option = Option(**data)
    assert option.position_type is None


@pytest.mark.parametrize("quantity, position_type", [(10, OptionPositionType.LONG), (-10, OptionPositionType.SHORT)])
def test_open_trade_has_correct_position_type(get_data, quantity, position_type):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    data = copy.deepcopy(call_data[0])
    option = Option(**data)
    option.open_trade(quantity=quantity)

    assert option.position_type == position_type

@pytest.mark.parametrize("option_type, quantity, expected_premium", [
    ('call', 10, 12_770.0),
    ('call', 5, 6_385.0),
    ('call', -10, -12_770.0),
    ('put', 10, 170.0),
    ('put', -10, -170.0),
    ('put', 5, 85.0),
])
def test_open_trade_returns_correct_premium_value(get_data, incur_fees_false, option_type, quantity,
                                                  expected_premium):
    option_id = 'AAPL20150117C00010000' if option_type == 'call' else 'AAPL20150117P00010000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])
    test_option = Option(**option_data)

    trade_open_info = test_option.open_trade(quantity=quantity)
    assert trade_open_info.premium == expected_premium


@pytest.mark.parametrize("quantity, expected_fees", [(10, 5.0), (2, 1.0), (-3, 1.5)])
def test_open_trade_sets_total_fees_when_incur_fees_is_true(get_data, incur_fees_true, quantity,
                                                            expected_fees):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)
    option.open_trade(quantity=quantity)

    assert option.total_fees == expected_fees


@pytest.mark.parametrize("quantity, expected_fees", [(10, 0.0), (2, 0.0), (-3, 0.0)])
def test_open_trade_sets_total_fees_to_zero_when_incur_fees_is_false(get_data, incur_fees_false, quantity,
                                                                     expected_fees):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)
    option.open_trade(quantity=quantity)

    assert option.total_fees == expected_fees


@pytest.mark.parametrize("quantity", [None, 1.5, 0, -1.5, "abc"])
def test_open_trade_with_invalid_quantity_raises_exception(get_data, quantity):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    with pytest.raises(ValueError):
        option.open_trade(quantity=quantity)


def test_open_trade_when_trade_is_already_open_raises_exception(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    quantity = 10
    option.open_trade(quantity=quantity)

    assert OptionStatus.TRADE_IS_OPEN in option.status

    with pytest.raises(ValueError, match="Cannot open position. A position is already open."):
        option.open_trade(quantity=quantity)


@pytest.mark.parametrize("quantity, close_quantity, remaining_quantity, status", [
    (10, 8, 2, OptionStatus.TRADE_PARTIALLY_CLOSED), (-10, -8, -2, OptionStatus.TRADE_PARTIALLY_CLOSED),
    (10, None, 0, OptionStatus.TRADE_IS_CLOSED), (-10, None, 0, OptionStatus.TRADE_IS_CLOSED)])
def test_close_partial_or_full_trade(get_data, quantity, close_quantity, remaining_quantity, status):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=quantity)
    option.close_trade(quantity=close_quantity)

    assert option.quantity == remaining_quantity
    assert status in option.status


@pytest.mark.parametrize("open_qty, close1_qty, close2_qty, expected_qty", [(10, 2, 8, 0), (10, 2, 3, 5),
                                                                            (-10, -2, -8, 0), (-10, -2, -3, -5)])
def test_close_trade_with_multiple_partial_close(get_data, open_qty, close1_qty, close2_qty, expected_qty):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=open_qty)

    option.close_trade(quantity=close1_qty)
    option.close_trade(quantity=close2_qty)

    assert option.quantity == expected_qty


@pytest.mark.parametrize("open_quantity, close_quantity", [(10, 12), (-10, -12)])
def test_close_trade_with_greater_than_quantity_open_raises_exception(get_data, open_quantity,
                                                                      close_quantity):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=open_quantity)

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        option.close_trade(quantity=close_quantity)


@pytest.mark.parametrize("open_qty, close1_qty, close2_qty", [(10, 6, 6), (10, 9, 2), (-10, -7, -4), (-10, -9, -2)])
def test_close_partial_trade_with_greater_than_remaining_quantity_raises_exception(get_data, open_qty,
                                                                                   close1_qty, close2_qty):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=open_qty)
    option.close_trade(quantity=close1_qty)  # close partial trade

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        option.close_trade(quantity=close2_qty)


@pytest.mark.parametrize("incur_fees_flag, fee_per_contract, open_quantity, close_quantity, fee_amount", [(True, 0.65, 10, 10, 13.0),
                                                                                        (True, 0.25, -10, -10, 5.0),
                                                                                        (True, 0.5, 10, 2, 6.0),
                                                                                        (False, 0.25, 10, 10, 0.0),
                                                                                        (False, 1.0, -10, -10, 0.0),
                                                                                        (False, 0.5, -10, -2, 0.0)])
def test_close_trade_updates_total_fees_incur_fees_flag(get_data, incur_fees_flag, fee_per_contract,
                                                        open_quantity, close_quantity, fee_amount):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.incur_fees = incur_fees_flag
    option.fee_per_contract = fee_per_contract
    option.open_trade(quantity=open_quantity)
    option.close_trade(quantity=close_quantity)

    assert option.total_fees == fee_amount
    pass


@pytest.mark.parametrize("open_qty, close_qty, expected_qty, close_dt, close_pnl, close_pnl_pct, close_fees, status", [
    (10, 10, -10, None, -2000.0, -0.1566, 5.0, OptionStatus.TRADE_IS_CLOSED),
    (10, 1, -1, None, -200.0, -0.1566, 0.5, OptionStatus.TRADE_PARTIALLY_CLOSED),
    (-10, -5, 5, None, 1000.0, 0.1566, 2.5, OptionStatus.TRADE_PARTIALLY_CLOSED)
])
def test_close_trade_values_with_one_close_trade(get_data, open_qty, close_qty,
                                                 expected_qty, close_dt, close_pnl,
                                                 close_pnl_pct, close_fees, status):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=open_qty)

    next_update = copy.deepcopy(call_data[1])
    option.next(next_update)
    trade_close_info = option.close_trade(quantity=close_qty)

    assert trade_close_info.date == next_update['quote_datetime']
    assert trade_close_info.quantity == close_qty * -1
    assert trade_close_info.price == next_update['price']
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.profit_loss_percent == close_pnl_pct
    assert trade_close_info.fees == close_fees
    assert trade_close_info.quantity == expected_qty
    assert status in option.status


@pytest.mark.parametrize(
    "open_qty, cqty1, cqty2, weighted_price, close_pnl, pnl_pct, close_fees, closed_qty, remaining_qty",
    [(10, 2, 3, 10.12, -1_327.0, -0.1039, 2.5, -5, 5),
     (-10, -3, -5, 10.09, 2_145.0, 0.1680, 4.0, 8, -2),
     (10, 8, 1, 10.65, -1_909.0, -0.1495, 4.5, -9, 1),
     (-10, -1, -1, 10.22, 509.0, 0.0399, 1.0, 2, -8)
     ])
def test_partial_option_close_trade_with_multiple_transactions(get_data, open_qty, cqty1, cqty2, weighted_price,
                                                               close_pnl, pnl_pct, close_fees,
                                                               closed_qty, remaining_qty):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)


    option.open_trade(quantity=open_qty)

    # first update
    first_update = copy.deepcopy(call_data[1])
    close_date = first_update['quote_datetime']
    option.next(first_update)
    trade_close_info = option.close_trade(quantity=cqty1)
    assert trade_close_info.date == close_date
    assert trade_close_info.price == 10.77

    # second update
    second_update = copy.deepcopy(call_data[2])
    close_date = second_update['quote_datetime']
    option.next(second_update)
    option.close_trade(quantity=cqty2)
    trade_close_info = option.trade_close_info

    # get close info for closed trades

    assert trade_close_info.date == close_date
    assert trade_close_info.price == weighted_price
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.fees == close_fees
    assert trade_close_info.profit_loss_percent == pnl_pct
    assert trade_close_info.quantity == closed_qty
    assert option.quantity == remaining_qty
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status
    assert OptionStatus.TRADE_IS_OPEN in option.status


def test_trade_close_records_returns_all_close_trades(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=10)

    next_update = copy.deepcopy(call_data[1])
    option.next(next_update)

    option.close_trade(quantity=3)

    records = option.trade_close_records
    assert len(records) == 1

    next_update = copy.deepcopy(call_data[2])
    option.next(next_update)
    option.close_trade(quantity=6)

    records = option.trade_close_records
    assert len(records) == 2


def test_total_fees_returns_all_fees_incurred(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=10)

    assert option.total_fees == 5.0

    next_update = copy.deepcopy(call_data[1])
    option.next(next_update)
    option.close_trade(quantity=2)

    assert option.total_fees == 6.0

    next_update = copy.deepcopy(call_data[2])
    option.next(next_update)
    option.close_trade(quantity=3)

    assert option.total_fees == 7.5


def test_get_closing_price(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=1)

    next_update = copy.deepcopy(call_data[1])
    option.next(next_update)
    expected_close_price = 10.77

    close_price = option.get_closing_price()

    assert close_price == expected_close_price


def test_get_close_price_on_option_that_has_not_been_traded_raises_exception(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    with pytest.raises(ValueError,
                       match="Cannot determine closing price on option that does not have an opening trade"):
        option.get_closing_price()


@pytest.mark.parametrize("option_type, position_type, expected_closing_price", [
    ('call', OptionPositionType.LONG, 0.0), ('call', OptionPositionType.SHORT, 10.90),
    ('put', OptionPositionType.LONG, 0.0), ('put', OptionPositionType.SHORT, 10.90),
])
def test_get_closing_price_on_call_option_when_bid_is_zero(get_data, option_type, position_type, expected_closing_price):
    # When the bid is zero and option is long, you must sell to close, but bid of zero implies no buyers, so cannot sell.
    # When the bid is zero and option is short, you must buy to close, but since there are no sellers, the ask price is the price.
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option_data['option_type'] = option_type
    option = Option(**option_data)

    # open trade
    quantity = 1 if position_type == OptionPositionType.LONG else -1
    option.open_trade(quantity=quantity)

    next_update = copy.deepcopy(call_data[1])
    next_update['bid'] = 0.0
    next_update['ask'] = 10.90
    option.next(next_update)

    assert option.position_type == position_type
    assert option.get_closing_price() == expected_closing_price


def test_option_update_skips_date_has_correct_quote_datetime(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=1)

    next_update = copy.deepcopy(call_data[-1]) # skip to the end
    option.next(next_update)

    assert option.quote_datetime == next_update['quote_datetime']



@pytest.mark.parametrize("option_type, closing_price", [
    ('call', 99.99), ('put', 100.01)
])
def test_option_get_close_price_is_zero_when_option_expires_otm(get_data,option_type, closing_price):
    option_id = 'AAPL20150102C00010000' if option_type == 'call' else  'AAPL20150102P00010000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])
    option = Option(**option_data)

    option.open_trade(quantity=1)

    next_update = copy.deepcopy(data[1])
    next_update['spot_price'] = closing_price

    option.next(next_update)

    # move quote date past expiration
    quote_date = datetime.datetime(option.expiration.year, option.expiration.month, option.expiration.day+1)
    next_update = copy.deepcopy(data[2])
    next_update['quote_datetime'] = quote_date

    option.next(next_update)
    otm = option.otm()
    assert otm == True
    assert option.price != 0.0
    assert option.get_closing_price() == 0.0


def test_dte_when_option_has_quote_data(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    expected_dte = 18
    actual_dte = option.dte()
    assert actual_dte == expected_dte


def test_dte_is_updated_when_quote_date_is_updated(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    assert option.dte() == 18

    next_update = copy.deepcopy(call_data[1])
    option.next(next_update)

    expected_dte = 17
    assert option.dte() == expected_dte


def test_dte_is_zero_on_expiration_day(get_data):
    option_id = 'AAPL20150102C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    next_update = copy.deepcopy(call_data[-1]) # move to last update
    option.next(next_update)

    expected_dte = 0
    assert option.dte() == expected_dte


@pytest.mark.parametrize("option_type, spot_price, expected_value", [
    ('call', 100.00, False), ('call', 99.99, True),
    ('call', 100.01, False),
    ('put', 100.00, False), ('put', 100.01, True),
    ('put', 99.99, False)])
def test_option_otm(get_data, option_type, spot_price,expected_value):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option_data['option_type'] = option_type
    option = Option(**option_data)

    option.spot_price = spot_price

    actual_value = option.otm()
    assert actual_value == expected_value


@pytest.mark.parametrize("option_type, spot_price, expected_value", [
    ('call', 99.99, False), ('call', 100.00, True),
    ('call', 100.011, True),
    ('put', 100.00, True), ('put', 99.99, True),
    ('put', 100.01, False)])
def test_option_itm(get_data, option_type, spot_price,expected_value):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option_data['option_type'] = option_type
    option = Option(**option_data)

    option.spot_price = spot_price

    actual_value = option.itm()
    assert actual_value == expected_value

def test_expired_for_daily_data_next_day(get_data):
    option_id = 'AAPL20150102C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    assert OptionStatus.INITIALIZED in option.status

    option.open_trade(quantity=1)

    next_update = copy.deepcopy(call_data[-1])
    option.next(next_update)

    assert option.quote_datetime.date() == option.expiration

    # advance to the day after expiration
    next_update['quote_datetime'] = next_update['quote_datetime'] + datetime.timedelta(days=1)

    option.next(next_update)

    assert OptionStatus.EXPIRED in option.status

def test_check_expired_sets_expired_flag_correctly(get_intraday_data):
    option_id = 'SPXW20160429C00208000'
    data = get_intraday_data(option_id)
    option_data = copy.deepcopy(data[0])
    option = Option(**option_data)

    next_update = copy.deepcopy(data[1])
    option.next(next_update)

    assert OptionStatus.EXPIRED not in option.status

    next_update = copy.deepcopy(data[-2])
    tm = next_update['quote_datetime'].time()

    assert next_update['expiration'] == option.expiration
    assert tm == datetime.time(16,0)

    option.next(next_update) # This should mark option as expired

    assert OptionStatus.EXPIRED in option.status


def test_no_trade_is_open_status_if_trade_was_not_opened(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    assert (OptionStatus.TRADE_IS_OPEN in option.status) == False


def test_trade_is_open_status_is_true_if_trade_was_opened(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=10)
    assert (OptionStatus.TRADE_IS_OPEN in option.status) == True


def test_trade_is_open_status_is_true_if_partially_closed(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=10)
    option.close_trade(quantity=5)
    assert (OptionStatus.TRADE_IS_OPEN in option.status) == True


def test_trade_is_open_is_false_if_closed(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=10)
    option.close_trade(quantity=10)
    assert (OptionStatus.TRADE_IS_OPEN in option.status) == False


def test_get_unrealized_profit_loss_raises_exception_if_trade_was_not_opened(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    with pytest.raises(Exception, match="This option has no transactions."):
        option.get_unrealized_profit_loss()


def test_get_unrealized_profit_loss_is_zero_if_quote_data_has_not_changed(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=10)
    pnl = option.get_unrealized_profit_loss()
    assert pnl == 0.0


def test_get_unrealized_profit_loss_is_zero_when_trade_is_closed(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=10)

    next_update = copy.deepcopy(call_data[1])
    option.next(next_update)
    option.close_trade(quantity=10)

    pnl = option.get_unrealized_profit_loss()

    assert pnl == 0.0


@pytest.mark.parametrize("option_type, quantity, option_price, expected_profit_loss", [
    ('call', 10, 11.00, 1_000.0),
    ('call', 10, 9.00, -1_000.0),
    ('call', 10, 10.00, 0.0),
    ('call', -10, 11.00, -1_000.0),
    ('call', -10, 9.00, 1_000.0),
    ('call', -10, 10.00, 0.0),
    ('put', 10, 9.00, -1_000.0),
    ('put', 10, 11.00, 1_000.0),
    ('put', 10, 10.00, 0.0),
    ('put', -10, 9.00, 1_000.0),
    ('put', -10, 11.00, -1_000.0),
    ('put', -10, 10.00, 0.0)
])
def test_get_unrealized_profit_loss_value(get_data,
                                          option_type, quantity, option_price, expected_profit_loss):
    option_id = 'AAPL20150102C00010000' if option_type == 'call' else 'AAPL20150102P00010000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])
    option_data['price'] = 10.00
    option = Option(**option_data)

    option.open_trade(quantity=quantity)

    next_update = copy.deepcopy(data[1])
    next_update['price'] = option_price
    option.next(next_update)

    actual_profit_loss = option.get_unrealized_profit_loss()
    assert actual_profit_loss == expected_profit_loss


def test_unrealized_profit_loss_percent_raises_exception_if_trade_was_not_opened(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    with pytest.raises(Exception, match="This option has no transactions."):
        option.get_unrealized_profit_loss_percent()


def test_get_unrealized_profit_loss_percent_returns_zero_when_trade_is_closed(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=1)
    option.close_trade(quantity=1)

    actual_value = option.get_unrealized_profit_loss_percent()
    assert actual_value == 0.0


@pytest.mark.parametrize("option_type, quantity, option_price, expected_profit_loss_pct", [
    ('call', 10, 10.50, 0.05),
    ('call', 10, 9.50, -0.05),
    ('call', 10, 10.0, 0.0),
    ('call', -10, 10.50, -0.05),
    ('call', -10, 9.5, 0.05),
    ('call', -10, 10.0, 0.0),
    ('put', 10, 10.5, 0.05),
    ('put', 10, 9.5, -0.05),
    ('put', 10, 10.0, 0.0),
    ('put', -10, 10.5, -0.05),
    ('put', -10, 9.5, 0.05),
    ('put', -10, 10.0, 0.0)
])
def test_get_unrealized_profit_loss_percent_value(get_data,
                                                  option_type, quantity, option_price, expected_profit_loss_pct):
    option_id = 'AAPL20150102C00010000' if option_type == 'call' else 'AAPL20150102P00010000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])

    # set price of option to 10 before opening trade
    option_data['price'] = 10.00
    option = Option(**option_data)

    option.open_trade(quantity=quantity)

    next_update = copy.deepcopy(data[1])

    # update price for test
    next_update['price'] = option_price
    option.next(next_update)

    actual_profit_loss = option.get_unrealized_profit_loss_percent()
    assert actual_profit_loss == expected_profit_loss_pct


def test_get_days_in_trade(get_data):
    option_id = 'AAPL20150117C00010000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])
    option = Option(**option_data)

    option.open_trade(quantity=1)
    assert option.get_days_in_trade() == 0

    next_update = copy.deepcopy(data[1])
    option.next(next_update)

    assert option.get_days_in_trade() == 1

    last_update = copy.deepcopy(data[-1])
    option.next(last_update)

    assert option.get_days_in_trade() == 8


def test_get_profit_loss_raises_exception_if_not_traded(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    with pytest.raises(Exception, match="This option has not been traded."):
        option.get_profit_loss()


@pytest.mark.parametrize("option_type, qty, test_price, expected_value", [
    ('call', 10, 15.0, 5000.0),
    ('call', 10, 5.0, -5000.0),
    ('call', -10, 15.0, -5000.0),
    ('call', -10, 5.0, 5000.0),
    ('put', 10, 15.0, 5000.0),
    ('put', 10, 5.0, -5000.0),
    ('put', -10, 15.0, -5000.0),
    ('put', -10, 5.0, 5000.0),

])
def test_get_total_profit_loss_returns_unrealized_when_no_contracts_are_closed(get_data,
                                                                               option_type, qty, test_price, expected_value):
    option_id = 'AAPL20150102C00010000' if option_type == 'call' else 'AAPL20150102P00010000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])

    # set price before opening option
    option_data['price'] = 10.0
    option = Option(**option_data)
    option.open_trade(quantity=qty)

    next_update = copy.deepcopy(data[1])
    next_update['price'] = test_price
    option.next(next_update)

    actual_value = option.get_profit_loss()
    assert actual_value == expected_value


def test_get_profit_loss_returns_closed_pnl_when_all_contracts_are_closed(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option_data['price'] = 10.0
    option = Option(**option_data)

    option.open_trade(quantity=10)

    next_update = copy.deepcopy(call_data[1])
    next_update['price'] = 10.10
    option.next(next_update)
    option.close_trade(quantity=10)

    assert option.get_profit_loss() == 100.0


def test_get_profit_loss_returns_unrealized_and_closed_pnl_when_partially_closed(get_data):
    option_id = 'AAPL20150117P00010000'
    put_data = get_data(option_id)
    option_data = copy.deepcopy(put_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=10)

    next_update = copy.deepcopy(put_data[1])
    option.next(next_update)

    option.close_trade(quantity=5)

    next_update = copy.deepcopy(put_data[2])
    option.next(next_update)

    assert option.get_profit_loss() == 130.0

def test_get_total_profit_loss_returns_unrealized_and_closed_pnl_when_multiple_close_trades(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=-10) # price 12.77

    # close the first 3 contracts at updated price
    next_update = copy.deepcopy(call_data[1])
    option.next(next_update) # price 10.77
    option.close_trade(quantity=-3)  # $600

    # close another 3 contracts at updated price
    next_update = copy.deepcopy(call_data[2])
    option.next(next_update) # price 9.68
    option.close_trade(quantity=-3)  # $927

    # update the price to the next time slot values
    next_update = copy.deepcopy(call_data[3])
    option.next(next_update) # price 6.95, unrealized for 4 contracts = 2_328

    actual_value = option.get_profit_loss() # 600+927 realized, 2_328 unrealized = 3_855 total
    assert actual_value == 3_855.0


def test_get_profit_loss_percent_raises_exception_if_not_traded(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    with pytest.raises(Exception, match="This option has not been traded."):
        option.get_profit_loss_percent()


@pytest.mark.parametrize("option_type, qty, test_price, expected_value", [
    ('call', 10, 12.0, 0.2),
    ('call', -10, 12.0, -0.2),
    ('put', 10, 12.0, 0.2),
    ('put', -10, 12.0, -0.2),
])
def test_get_profit_loss_percent_returns_unrealized_when_no_contracts_are_closed(get_data, option_type,
                                                                                 qty, test_price, expected_value):
    option_id = 'AAPL20150102C00010000' if option_type == 'call' else 'AAPL20150102P00010000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])

    # set open price to $10.00
    option_data['price'] = 10.0
    option = Option(**option_data)
    option.open_trade(quantity=qty)

    # set next update price to test price
    next_update = copy.deepcopy(data[1])
    next_update['price'] = test_price

    option.next(next_update)
    actual_value = option.get_profit_loss_percent()
    assert actual_value == expected_value


@pytest.mark.parametrize("option_type, qty, test_price, expected_value", [
    ('call', 10, 12, 0.2),
    ('call', -10, 12, -0.2),
    ('put', 10, 12, 0.2),
    ('put', -10, 12, -0.2),
])
def test_get_total_profit_loss_percent_returns_closed_pnl_when_all_contracts_are_closed(get_data,
                                                                                        option_type, qty, test_price,
                                                                                        expected_value):
    option_id = 'AAPL20150102C00010000' if option_type == 'call' else 'AAPL20150102P00010000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])

    # set open price to $10.00
    option_data['price'] = 10.0
    option = Option(**option_data)
    option.open_trade(quantity=qty)

    # set next update price to test price
    next_update = copy.deepcopy(data[1])
    next_update['price'] = test_price
    option.next(next_update)
    option.close_trade(quantity=qty)

    assert option.get_profit_loss_percent() == expected_value


@pytest.mark.parametrize(" qty, close_qty_1, close_qty_2, price1, price2, price3, expected_value", [
    (10, 4, 2, 9.0, 8.0, 6.0, -0.24),
    (-10, -4, -2, 9.0, 8.0, 6.0, 0.24),
    (10, 4, 2, 9.0, 8.0, 6.0, -0.24),
    (-10, -4, -2, 9.0, 8.0, 6.0, 0.24),
])
def test_get_total_profit_loss_percent_returns_unrealized_and_closed_pnl_when_multiple_close_trades(
        get_data,
        qty,
        close_qty_1,
        close_qty_2,
        price1, price2,
        price3,
        expected_value):

    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)

    # set open price
    option_data = copy.deepcopy(call_data[0])
    option_data['price'] = 10.0 # starting price
    option = Option(**option_data)
    option.open_trade(quantity=qty)

    # first price update, close partial
    next_update = copy.deepcopy(call_data[1])
    next_update['price'] = price1
    option.next(next_update)
    option.close_trade(quantity=close_qty_1)

    # second price update, close partial
    next_update = copy.deepcopy(call_data[2])
    next_update['price'] = price2
    option.next(next_update)
    option.close_trade(quantity=close_qty_2)

    # third update - no close
    next_update = copy.deepcopy(call_data[2])
    next_update['price'] = price3
    option.next(next_update)

    actual_value = option.get_profit_loss_percent()
    assert actual_value == expected_value


def test_option_properties_return_none_when_no_data(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    data = copy.deepcopy(call_data[0])
    required_fields = ['quote_datetime', 'option_id', 'symbol', 'strike', 'expiration', 'option_type', 'spot_price', 'bid', 'ask', 'price']
    option_data = {k: data[k] for k in required_fields if k in data}
    option = Option(**option_data)

    assert option.delta is None
    assert option.gamma is None
    assert option.theta is None
    assert option.vega is None
    assert option.rho is None

    assert option.open_interest is None
    assert option.implied_volatility is None


def test_open_option_emits_open_transaction_completed_event(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)
    test_open_info = None

    class MyPortfolio:

        @staticmethod
        def on_option_opened(trade_open_info):
            nonlocal test_open_info
            test_open_info = trade_open_info

    my_portfolio = MyPortfolio()
    option.bind(open_transaction_completed=my_portfolio.on_option_opened)

    option.open_trade(quantity=1)

    assert test_open_info is not None
    assert test_open_info.option_id == option.option_id
    assert test_open_info.date == option.quote_datetime
    assert test_open_info.quantity == 1


def test_close_option_emits_close_transaction_completed_event(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)
    test_close_info = None

    # create handler method
    class MyPortfolio:

        @staticmethod
        def on_option_closed(trade_close_info):
            nonlocal test_close_info
            test_close_info = trade_close_info

    my_portfolio = MyPortfolio()
    option.bind(close_transaction_completed=my_portfolio.on_option_closed)

    # open trade
    option.open_trade(quantity=10)

    # advance to next update and close trade
    next_update = copy.deepcopy(call_data[1])
    quote_date = next_update['quote_datetime']
    option.next(next_update)
    option.close_trade(quantity=5)

    assert test_close_info is not None
    assert test_close_info.option_id == option.option_id
    assert test_close_info.date == quote_date
    assert test_close_info.quantity == -5


def test_update_to_expired_date_emits_option_expired_event(get_data):
    option_id = 'AAPL20150102C00010000'
    call_data = get_data('AAPL20150102C00010000')
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    expired_option_id = None

    # Create handler method and get option id of expiring option
    class MyPortfolio:

        @staticmethod
        def on_option_expired(option_id):
            nonlocal expired_option_id
            expired_option_id = option_id

    my_portfolio = MyPortfolio()
    option.bind(option_expired=my_portfolio.on_option_expired)

    # update to day after last day of option
    next_update = copy.deepcopy(call_data[-1])
    expired_quote_date = next_update['quote_datetime'] + relativedelta.relativedelta(days=1)
    next_update['quote_datetime'] = expired_quote_date
    option.next(next_update) # should cause expired status

    assert expired_option_id == option.option_id


def test_fees_incurred_event_emitted_when_open_or_close_fees_are_incurred(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)
    my_fees = None

    assert option.incur_fees == True
    assert option.fee_per_contract == 0.5

    # create handler method
    class MyPortfolio:

        @staticmethod
        def on_fees_incurred(fees):
            nonlocal my_fees
            my_fees = fees

    my_portfolio = MyPortfolio()
    option.bind(fees_incurred=my_portfolio.on_fees_incurred)

    option.open_trade(quantity=10)
    assert my_fees == 5.0

    my_fees = 0

    next_update = copy.deepcopy(call_data[1])
    option.next(next_update)
    assert my_fees == 0

    option.close_trade(quantity=5)
    assert my_fees == 2.5


def test_current_value_is_zero_if_no_trades(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    assert option.current_value == 0.0


def test_current_value_is_same_as_open_premium_if_no_price_change(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    open_info = option.open_trade(quantity=1)
    premium = open_info.premium

    assert option.current_value == premium


def test_current_value_is_updated_when_price_changes(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=1)

    next_update = copy.deepcopy(call_data[1])
    option.next(next_update)

    new_premium = next_update['price'] * 100

    assert option.current_value == new_premium


def test_current_value_price_changes_when_partially_closed(get_data):
    option_id = 'AAPL20150117C00010000'
    call_data = get_data(option_id)
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=10) # price = 12.77

    next_update = copy.deepcopy(call_data[1])
    option.next(next_update) # price = 10.77
    assert option.current_value == 10_770.0

    option.close_trade(quantity=5)
    assert option.current_value == 5_385.0

    next_update = copy.deepcopy(call_data[2])
    option.next(next_update)  # price = 9.68
    assert option.current_value == 4_840.0

    next_update = copy.deepcopy(call_data[3])
    option.next(next_update) # price = 6.95
    option.close_trade(quantity=2)
    assert option.current_value == 2_085.0

    next_update = copy.deepcopy(call_data[4])
    option.next(next_update) # price = 6.85
    assert option.current_value == 2_055.0

    next_update = copy.deepcopy(call_data[5])
    option.next(next_update)  # price = 8.05
    assert option.current_value == 2_415.0

    option.close_trade(quantity=3)
    assert option.current_value == 0.0

def test_call_get_closing_price_for_expiring_itm(get_data):
    option_id = 'AAPL20150102C00010000'
    call_data = get_data('AAPL20150102C00010000')
    option_data = copy.deepcopy(call_data[0])
    option = Option(**option_data)

    option.open_trade(quantity=1)

    # update to last day of option
    last_update = copy.deepcopy(call_data[-1])
    option.next(last_update)

    quote_datetime = last_update['quote_datetime']
    last_update['quote_datetime'] = datetime.datetime(quote_datetime.year, quote_datetime.month, quote_datetime.day + 1)
    option.next(last_update) # one day past expiration

    # strike = 100.0
    # spot price @ closing = 109.33
    closing_price = option.get_closing_price()

    assert closing_price == 9.33 # 109.33 - 100.00

def test_put_get_closing_price_for_expiring_itm(get_data):
    option_id = 'AAPL20150102P00012000'
    data = get_data(option_id)
    option_data = copy.deepcopy(data[0])
    option = Option(**option_data)

    option.open_trade(quantity=1)

    # update to last day of option
    last_update = copy.deepcopy(data[-1])
    option.next(last_update)

    quote_datetime = last_update['quote_datetime']
    last_update['quote_datetime'] = datetime.datetime(quote_datetime.year, quote_datetime.month, quote_datetime.day + 1)
    option.next(last_update) # one day past expiration

    # strike = 120.0
    # spot price @ closing = 109.33
    closing_price = option.get_closing_price()

    assert closing_price == 10.67


def test_option_emits_events(get_intraday_data):
    option_id = 'SPXW20160429P00208000'
    data = get_intraday_data(option_id)
    option_data = copy.deepcopy(data[0])
    option = Option(**option_data)

    open_trx_fired = None
    close_trx_fired = None
    apply_fees_fired = 0
    option_expired_fired = None

    class Listener():

        @staticmethod
        def on_option_opened(info):
            nonlocal open_trx_fired
            open_trx_fired = info

        @staticmethod
        def on_option_closed(info):
            nonlocal close_trx_fired
            close_trx_fired = info

        @staticmethod
        def on_fees_applied(fees):
            nonlocal apply_fees_fired
            apply_fees_fired = fees

        @staticmethod
        def on_expired(_id):
            nonlocal option_expired_fired
            option_expired_fired = _id

    listener = Listener()

    # open_transaction_completed event
    option.bind(open_transaction_completed=listener.on_option_opened)
    option.open_trade(quantity=1)

    # close_transaction_completed event
    option.bind(close_transaction_completed=listener.on_option_closed)
    option.close_trade(quantity=1)
    assert close_trx_fired is not None

    # fees_incurred event
    option = Option(**option_data)
    option.bind(fees_incurred=listener.on_fees_applied)
    option.incur_fees = True
    option.fee_per_contract = 0.5
    option.open_trade(quantity=1)
    assert apply_fees_fired > 0

    # option_expired event
    option.bind(option_expired=listener.on_expired)
    next_update = copy.deepcopy(data[-2])
    option.next(next_update)
    assert option_expired_fired == option.option_id
