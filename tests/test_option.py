import pytest
from options_framework.option_types import OptionPositionType, OptionStatus
from options_framework.config import settings

from test_data.test_option_daily import *
from test_data.test_options_intraday import *


@pytest.fixture(scope='function')
def test_values_call():
    vals = next(x for x in daily_test_data if x['option_id'] == 'AAPL140207C00512500')
    option = Option(option_id=vals['option_id'], symbol=vals['symbol'], strike=vals['strike'],
                    expiration=vals['expiration'],
                    option_type=vals['option_type'], quote_datetime=vals['quote_datetime'],
                    spot_price=vals['spot_price'],
                    bid=vals['bid'], ask=vals['ask'], price=vals['price'], volume=vals['volume'],
                    open_interest=vals['open_interest'], implied_volatility=vals['implied_volatility'],
                    delta=vals['delta'], gamma=vals['gamma'], theta=vals['theta'], vega=vals['vega'], rho=vals['rho'])
    return vals, option


@pytest.fixture
def test_values_put(scope='function'):
    vals = next(x for x in daily_test_data if x['option_id'] == 'AAPL140214P00520000')
    option = Option(option_id=vals['option_id'], symbol=vals['symbol'], strike=vals['strike'],
                    expiration=vals['expiration'],
                    option_type=vals['option_type'], quote_datetime=vals['quote_datetime'],
                    spot_price=vals['spot_price'],
                    bid=vals['bid'], ask=vals['ask'], price=vals['price'], volume=vals['volume'],
                    open_interest=vals['open_interest'], implied_volatility=vals['implied_volatility'],
                    delta=vals['delta'], gamma=vals['gamma'], theta=vals['theta'], vega=vals['vega'], rho=vals['rho'])
    return vals, option


@pytest.fixture
def test_values_put_expiring():
    option_data = (x for x in daily_test_data if x['option_id'] == 'AAPL140207P00512500')
    vals = next(option_data)
    option = Option(option_id=vals['option_id'], symbol=vals['symbol'], strike=vals['strike'],
                    expiration=vals['expiration'],
                    option_type=vals['option_type'], quote_datetime=vals['quote_datetime'],
                    spot_price=vals['spot_price'],
                    bid=vals['bid'], ask=vals['ask'], price=vals['price'], volume=vals['volume'],
                    open_interest=vals['open_interest'], implied_volatility=vals['implied_volatility'],
                    delta=vals['delta'], gamma=vals['gamma'], theta=vals['theta'], vega=vals['vega'], rho=vals['rho'])
    updates = list(option_data)
    df = pd.DataFrame(updates, columns=fields)
    return option, df, updates


@pytest.fixture
def call_updates():
    updates = [x for x in daily_test_data if x['option_id'] == 'AAPL140207C00512500'][1:]
    df = pd.DataFrame(updates, columns=fields)
    return df, updates


@pytest.fixture
def put_updates():
    updates = [x for x in daily_test_data if x['option_id'] == 'AAPL140214P00520000'][1:]
    df = pd.DataFrame(updates, columns=fields)
    return df, updates


@pytest.fixture
def call_intraday_option():
    option_data = (x for x in intraday_test_data if x['option_id'] == 'SPXW20160309C00001990')
    vals = next(option_data)
    updates = list(option_data)

    option = Option(option_id=vals['option_id'], symbol=vals['symbol'], strike=vals['strike'],
                    expiration=vals['expiration'],
                    option_type=vals['option_type'], quote_datetime=vals['quote_datetime'],
                    spot_price=vals['spot_price'],
                    bid=vals['bid'], ask=vals['ask'], price=vals['price'])
    df = pd.DataFrame(updates, columns=fields)
    return option, df, updates


def test_option_init_with_quote_data(test_values_call):
    test_values, _ = test_values_call

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

    assert test_option.option_id == 'AAPL140207C00512500'
    assert test_option.symbol == 'AAPL'
    assert test_option.expiration == datetime.date(2014, 2, 7)
    assert test_option.strike == 512.5
    assert test_option.spot_price == 512.59
    assert test_option.bid == 2.14
    assert test_option.ask == 2.27
    assert test_option.price == 2.21
    assert test_option.quote_datetime == datetime.datetime(2014, 2, 5)


def test_option_init_with_extended_properties(test_values_call):
    test_values, _ = test_values_call

    test_option = Option(option_id=test_values['option_id'], symbol=test_values['symbol'], strike=test_values['strike'],
                         expiration=test_values['expiration'], option_type=test_values['option_type'],
                         quote_datetime=test_values['quote_datetime'], spot_price=test_values['spot_price'],
                         bid=test_values['bid'], ask=test_values['ask'], price=test_values['price'],
                         open_interest=test_values['open_interest'], implied_volatility=test_values['implied_volatility'],
                         delta=test_values['delta'], gamma=test_values['gamma'], theta=test_values['theta'],
                         vega=test_values['vega'], rho=test_values['rho'])

    assert test_option.delta == 0.4817
    assert test_option.gamma == 0.0675
    assert test_option.theta == -270.1394
    assert test_option.vega == 12.3377
    assert test_option.rho == 0.1635

    assert test_option.implied_volatility == 0.1903
    assert test_option.open_interest == 3704


def test_option_set_user_defined_attributes(test_values_call):
    test_values, _ = test_values_call

    test_value_1 = 'first'
    test_value_2 = 'second'

    test_option = Option(option_id=test_values['option_id'], symbol=test_values['symbol'], strike=test_values['strike'],
                         expiration=test_values['expiration'], option_type=test_values['option_type'],
                         quote_datetime=test_values['quote_datetime'], spot_price=test_values['spot_price'],
                         bid=test_values['bid'], ask=test_values['ask'], price=test_values['price'],
                         user_defined={'user_defined1': test_value_1, 'user_defined2': test_value_2})

    assert test_option.user_defined['user_defined1'] == test_value_1
    assert test_option.user_defined['user_defined2'] == test_value_2


def test_option_init_raises_exception_if_missing_required_fields(test_values_call):
    test_values, _ = test_values_call
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


def test_option_init_raises_exception_if_quote_date_is_greater_than_expiration(test_values_call):
    test_values, _ = test_values_call

    bad_quote_date = test_values['quote_datetime'] + datetime.timedelta(days=100)

    with pytest.raises(Exception, match="Cannot create an option with a quote date past its expiration date"):
        Option(option_id=test_values['option_id'], symbol=test_values['symbol'], strike=test_values['strike'],
               expiration=test_values['expiration'], option_type=test_values['option_type'],
               quote_datetime=bad_quote_date, spot_price=test_values['spot_price'],
               bid=test_values['bid'], ask=test_values['ask'], price=test_values['price'])


def test_option_init_quote_datetime_raises_error_if_is_not_datetime_or_timestamp_type(test_values_call):
    test_values, _ = test_values_call

    bad_quote_date = test_values['quote_datetime'].date()

    with pytest.raises(Exception, match="quote datetime must be python datetime.datetime or pandas Timestamp"):
        Option(option_id=test_values['option_id'], symbol=test_values['symbol'], strike=test_values['strike'],
               expiration=test_values['expiration'], option_type=test_values['option_type'],
               quote_datetime=bad_quote_date, spot_price=test_values['spot_price'],
               bid=test_values['bid'], ask=test_values['ask'], price=test_values['price'])

def test_option_update_quote_datetimeraises_error_if_is_not_datetime_or_timestamp_type(test_values_call, call_updates):
    _, call = test_values_call
    _, updates = call_updates

    update_date = updates[0]['quote_datetime'].date()

    with pytest.raises(Exception, match="Wrong format for option date. Must be python datetime.datetime. Date was provided in <class 'datetime.date'> format."):
        call.next_update(update_date)


@pytest.mark.parametrize("option_type, expected_repr", [
    (OptionType.CALL, '<CALL(AAPL140207C00512500) AAPL 512.5 2014-02-07>'),
    (OptionType.PUT, '<PUT(AAPL140214P00520000) AAPL 520 2014-02-14>')])
def test_call_option_string_representation(test_values_call, test_values_put, option_type, expected_repr):
    if option_type == OptionType.CALL:
        _, test_option = test_values_call
    else:
        _, test_option = test_values_put

    assert str(test_option) == expected_repr


def test_update_sets_correct_values(test_values_call, call_updates):
    _, call = test_values_call
    update_df, updates = call_updates

    call.update_cache = update_df
    call.next_update(updates[0]['quote_datetime'])

    assert call.spot_price == updates[0]['spot_price']
    assert call.quote_datetime == updates[0]['quote_datetime']
    assert call.bid == updates[0]['bid']
    assert call.ask == updates[0]['ask']
    assert call.delta == updates[0]['delta']
    assert call.gamma == updates[0]['gamma']
    assert call.theta == updates[0]['theta']
    assert call.vega == updates[0]['vega']
    assert call.rho == updates[0]['rho']
    assert call.open_interest == updates[0]['open_interest']
    assert call.implied_volatility == updates[0]['implied_volatility']


def test_update_sets_expiration_status_if_quote_date_is_greater_than_expiration(test_values_call, call_updates):
    _, call = test_values_call
    update_df, updates = call_updates
    update_df.iloc[0]['quote_datetime'] = updates[1]['quote_datetime'] + datetime.timedelta(days=2)

    call.update_cache = update_df
    call.next_update(updates[1]['quote_datetime'] + datetime.timedelta(days=2))

    assert OptionStatus.EXPIRED in call.status


def test_open_trade_sets_correct_trade_open_info_values(test_values_call):
    values, call = test_values_call
    quantity = 10

    trade_open_info = call.open_trade(quantity=quantity, comment="my super insightful comment",
                                      what="whatever")
    assert trade_open_info.date == values['quote_datetime']
    assert trade_open_info.quantity == 10
    assert trade_open_info.price == 2.21
    assert trade_open_info.premium == 2_210.0
    assert call.quantity == 10
    assert OptionStatus.TRADE_IS_OPEN in call.status

    # kwargs were set as user_defined items
    assert call.user_defined['comment'] == "my super insightful comment"
    assert call.user_defined['what'] == "whatever"


def test_option_that_is_not_open_has_none_position_type(test_values_call):
    _, call = test_values_call
    assert call.position_type is None


@pytest.mark.parametrize("quantity, position_type", [(10, OptionPositionType.LONG), (-10, OptionPositionType.SHORT)])
def test_open_trade_has_correct_position_type(test_values_call, quantity, position_type):
    _, call = test_values_call

    call.open_trade(quantity=quantity)

    assert call.position_type == position_type

@pytest.mark.parametrize("option_type, quantity, expected_premium", [
    (OptionType.CALL, 10, 2_210.0),
    (OptionType.CALL, 5, 1_105.0),
    (OptionType.CALL, -10, -2_210.0),
    (OptionType.PUT, 10, 13_300.0),
    (OptionType.PUT, -10, -13_300.0),
    (OptionType.PUT, 5, 6_650.0),
])
def test_open_trade_returns_correct_premium_value(test_values_call, test_values_put, incur_fees_false, option_type, quantity,
                                                  expected_premium):
    if option_type == OptionType.CALL:
        _, test_option = test_values_call
    else:
        _, test_option = test_values_put

    trade_open_info = test_option.open_trade(quantity=quantity)
    assert trade_open_info.premium == expected_premium


@pytest.mark.parametrize("quantity, expected_fees", [(10, 5.0), (2, 1.0), (-3, 1.5)])
def test_open_trade_sets_total_fees_when_incur_fees_is_true(test_values_call, incur_fees_true, quantity,
                                                            expected_fees):
    _, call = test_values_call
    call.open_trade(quantity=quantity)

    assert call.total_fees == expected_fees


@pytest.mark.parametrize("quantity, expected_fees", [(10, 0.0), (2, 0.0), (-3, 0.0)])
def test_open_trade_sets_total_fees_to_zero_when_incur_fees_is_false(test_values_call, incur_fees_false, quantity,
                                                                     expected_fees):
    _, call = test_values_call
    call.open_trade(quantity=quantity)

    assert call.total_fees == expected_fees


@pytest.mark.parametrize("quantity", [None, 1.5, 0, -1.5, "abc"])
def test_open_trade_with_invalid_quantity_raises_exception(test_values_call, quantity):
    _, call = test_values_call

    with pytest.raises(ValueError):
        call.open_trade(quantity=quantity)


def test_open_trade_when_trade_is_already_open_raises_exception(test_values_call):
    _, call = test_values_call
    quantity = 10
    call.open_trade(quantity=quantity)
    assert OptionStatus.TRADE_IS_OPEN in call.status

    with pytest.raises(ValueError, match="Cannot open position. A position is already open."):
        call.open_trade(quantity=quantity)


@pytest.mark.parametrize("quantity, close_quantity, remaining_quantity, status", [
    (10, 8, 2, OptionStatus.TRADE_PARTIALLY_CLOSED), (-10, -8, -2, OptionStatus.TRADE_PARTIALLY_CLOSED),
    (10, None, 0, OptionStatus.TRADE_IS_CLOSED), (-10, None, 0, OptionStatus.TRADE_IS_CLOSED)])
def test_close_partial_or_full_trade(test_values_call, quantity, close_quantity, remaining_quantity, status):
    _, call = test_values_call
    call.open_trade(quantity=quantity)
    call.close_trade(quantity=close_quantity)

    assert call.quantity == remaining_quantity
    assert status in call.status


@pytest.mark.parametrize("open_qty, close1_qty, close2_qty, expected_qty", [(10, 2, 8, 0), (10, 2, 3, 5),
                                                                            (-10, -2, -8, 0), (-10, -2, -3, -5)])
def test_close_trade_with_multiple_partial_close(test_values_call, open_qty, close1_qty, close2_qty, expected_qty):
    _, call = test_values_call
    call.open_trade(quantity=open_qty)

    call.close_trade(quantity=close1_qty)
    call.close_trade(quantity=close2_qty)

    assert call.quantity == expected_qty


@pytest.mark.parametrize("open_quantity, close_quantity", [(10, 12), (-10, -12)])
def test_close_trade_with_greater_than_quantity_open_raises_exception(test_values_call, open_quantity,
                                                                      close_quantity):
    _, call = test_values_call
    call.open_trade(quantity=open_quantity)

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        call.close_trade(quantity=close_quantity)


@pytest.mark.parametrize("open_qty, close1_qty, close2_qty", [(10, 6, 6), (10, 9, 2), (-10, -7, -4), (-10, -9, -2)])
def test_close_partial_trade_with_greater_than_remaining_quantity_raises_exception(test_values_call, open_qty,
                                                                                   close1_qty, close2_qty):
    _, call = test_values_call
    call.open_trade(quantity=open_qty)
    call.close_trade(quantity=close1_qty)  # close partial trade

    with pytest.raises(ValueError, match="Quantity to close is greater than the current open quantity."):
        call.close_trade(quantity=close2_qty)


@pytest.mark.parametrize("incur_fees_flag, open_quantity, close_quantity, fee_amount", [(True, 10, 10, 10.0),
                                                                                        (True, -10, -10, 10.0),
                                                                                        (True, 10, 2, 6.0),
                                                                                        (False, 10, 10, 0.0),
                                                                                        (False, -10, -10, 0.0),
                                                                                        (False, -10, -2, 0.0)])
def test_close_trade_updates_total_fees_incur_fees_flag(test_values_call, incur_fees_true, incur_fees_flag,
                                                        open_quantity, close_quantity, fee_amount):
    _, call = test_values_call

    call.fee_per_contract = call
    settings['incur_fees'] = incur_fees_flag
    call.open_trade(quantity=open_quantity)
    call.close_trade(quantity=close_quantity)

    assert call.total_fees == fee_amount


@pytest.mark.parametrize("open_qty, close_qty, expected_qty, close_dt, close_pnl, close_pnl_pct, close_fees, status", [
    (10, 10, -10, None, 100.0, 0.0452, 5.0, OptionStatus.TRADE_IS_CLOSED),
    (10, 1, -1, None, 10.0, 0.0452, 0.5, OptionStatus.TRADE_PARTIALLY_CLOSED),
    (-10, -5, 5, None, -50.0, -0.0452, 2.5, OptionStatus.TRADE_PARTIALLY_CLOSED)
])
def test_close_trade_values_with_one_close_trade(test_values_call, call_updates, incur_fees_true,
                                                 open_qty, close_qty,
                                                 expected_qty, close_dt, close_pnl,
                                                 close_pnl_pct, close_fees, status):
    _, call = test_values_call
    update_df, updates = call_updates

    call.update_cache = update_df

    call.open_trade(quantity=open_qty)

    call.next_update(quote_datetime=updates[0]['quote_datetime'])
    trade_close_info = call.close_trade(quantity=close_qty)

    assert trade_close_info.date == updates[0]['quote_datetime']
    assert trade_close_info.quantity == close_qty * -1
    assert trade_close_info.price == updates[0]['price']
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.profit_loss_percent == close_pnl_pct
    assert trade_close_info.fees == close_fees
    assert trade_close_info.quantity == expected_qty
    assert status in call.status


@pytest.mark.parametrize(
    "open_qty, cqty1, cqty2, close_price, close_pnl, pnl_pct, close_fees, closed_qty, remaining_qty",
    [(10, 2, 3, 7.53, -2_884.0, -0.2168, 2.5, -5, 5),
     (-10, -3, -5, 7.4, 4_716.0, 0.3546, 4.0, 8, -2),
     (10, 8, 1, 10.02, -2_956.0, -0.2223, 4.5, -9, 1),
     (-10, -1, -1, 8.04, 1_052.0, 0.0791, 1.0, 2, -8)
     ])
def test_partial_option_close_trade_with_multiple_transactions(test_values_put, put_updates
        , open_qty, cqty1, cqty2, close_price, close_pnl, pnl_pct, close_fees, closed_qty, remaining_qty):
    _, put = test_values_put
    df, updates = put_updates
    put.update_cache = df

    put.open_trade(quantity=open_qty) # price = 13.3

    # first update
    close_date = updates[0]['quote_datetime']
    put.next_update(quote_datetime=close_date)
    trade_close_info = put.close_trade(quantity=cqty1)
    assert trade_close_info.date == close_date
    assert trade_close_info.price == 10.58

    # second update
    close_date = updates[1]['quote_datetime']
    put.next_update(quote_datetime=close_date)
    put.close_trade(quantity=cqty2) # price = 5.5
    trade_close_info = put.trade_close_info

    # get close info for closed trades

    assert trade_close_info.date == close_date
    assert trade_close_info.price == close_price
    assert trade_close_info.profit_loss == close_pnl
    assert trade_close_info.fees == close_fees
    assert trade_close_info.profit_loss_percent == pnl_pct
    assert trade_close_info.quantity == closed_qty
    assert put.quantity == remaining_qty
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in put.status
    assert OptionStatus.TRADE_IS_OPEN in put.status


def test_trade_close_records_returns_all_close_trades(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates

    call.open_trade(quantity=10)
    call.update_cache = df

    call.next_update(updates[0]['quote_datetime'])

    call.close_trade(quantity=3)

    records = call.trade_close_records
    assert len(records) == 1

    call.next_update(updates[1]['quote_datetime'])
    call.close_trade(quantity=6)

    records = call.trade_close_records
    assert len(records) == 2


def test_total_fees_returns_all_fees_incurred(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates

    call.open_trade(quantity=10)

    assert call.total_fees == 5.0

    call.update_cache = df
    call.next_update(updates[0]['quote_datetime'])
    call.close_trade(quantity=2)

    assert call.total_fees == 6.0

    call.next_update(updates[1]['quote_datetime'])
    call.close_trade(quantity=3)

    assert call.total_fees == 7.5


def test_get_closing_price(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.open_trade(quantity=1)
    call.update_cache = df
    call.next_update(updates[0]['quote_datetime'])
    expected_close_price = 2.31

    close_price = call.get_closing_price()

    assert close_price == expected_close_price


def test_get_close_price_on_option_that_has_not_been_traded_raises_exception(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates

    call.update_cache = df
    call.next_update(updates[0]['quote_datetime'])

    with pytest.raises(ValueError,
                       match="Cannot determine closing price on option that does not have an opening trade"):
        call.get_closing_price()


@pytest.mark.parametrize("open_qty, expected_closing_price", [
    (1, 0.0), (-1, 7.55)
])
def test_get_closing_price_on_call_option_when_bid_is_zero(test_values_call, call_updates, open_qty, expected_closing_price):
    _, call = test_values_call
    df, updates = call_updates
    df.loc[1, 'bid'] = 0.0

    call.update_cache = df
    call.next_update(updates[0]['quote_datetime'])

    # open trade
    call.open_trade(quantity=open_qty)

    call.next_update(updates[1]['quote_datetime'])

    assert call.get_closing_price() == expected_closing_price


@pytest.mark.parametrize("open_qty, expected_closing_price", [
    (1, 0.0), (-1, 5.55)
])
def test_get_closing_price_on_put_option_when_bid_is_zero(test_values_put, put_updates,
                                                          open_qty, expected_closing_price):
    _, put = test_values_put
    df, updates = put_updates
    df.loc[1, 'bid'] = 0.0

    put.update_cache = df
    put.next_update(updates[0]['quote_datetime'])

    # open trade
    put.open_trade(quantity=open_qty)

    put.next_update(updates[1]['quote_datetime'])

    assert put.get_closing_price() == expected_closing_price

def test_option_update_skips_date_has_correct_quote_datetime(test_values_put, put_updates):
    _, put = test_values_put
    df, updates = put_updates

    put.update_cache = df
    put.open_trade(quantity=1)
    put.next_update(updates[1]['quote_datetime'])

    assert put.quote_datetime == updates[1]['quote_datetime']



@pytest.mark.parametrize("option_type", [OptionType.CALL, OptionType.PUT])
def test_option_get_close_price_is_zero_when_option_expires_otm(test_values_call, call_updates, test_values_put_expiring, option_type):
    _, call = test_values_call
    df, updates = call_updates
    df.loc[1, 'spot_price'] = 512.0
    call.update_cache = df

    put, df, updates = test_values_put_expiring
    put.update_cache = df

    test_option = put if option_type == OptionType.PUT else call
    test_option.open_trade(quantity=1)


    test_option.next_update(updates[1]['quote_datetime'])

    # make option expired
    expired_date = datetime.datetime(2014, 2, 8)
    test_option.next_update(expired_date)

    assert test_option.otm() == True
    assert test_option.price != 0.0
    assert test_option.get_closing_price() == 0.0


def test_dte_when_option_has_quote_data(test_values_call):
    _, call = test_values_call

    expected_dte = 2
    actual_dte = call.dte()
    assert actual_dte == expected_dte


def test_dte_is_updated_when_quote_date_is_updated(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.update_cache = df
    call.next_update(updates[0]['quote_datetime'])

    expected_dte = 1
    assert call.dte() == expected_dte


def test_dte_is_zero_on_expiration_day(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.update_cache = df
    call.next_update(updates[1]['quote_datetime'])

    expected_dte = 0
    assert call.dte() == expected_dte


@pytest.mark.parametrize("option_type, spot_price, expected_value", [
    (OptionType.CALL, 512.50, False), (OptionType.CALL, 512.49, True),
    (OptionType.CALL, 512.51, False),
    (OptionType.PUT, 520.0, False), (OptionType.PUT, 520.01, True),
    (OptionType.PUT, 519.99, False)])
def test_call_option_otm(test_values_call, test_values_put, option_type, spot_price,
                         expected_value):
    if option_type == OptionType.CALL:
        _, test_option = test_values_call # 512.5 strike
    else:
        _, test_option = test_values_put # 520 strike

    test_option.spot_price = spot_price

    actual_value = test_option.otm()
    assert actual_value == expected_value


@pytest.mark.parametrize("option_type, spot_price, expected_value", [
    (OptionType.CALL, 512.49, False), (OptionType.CALL, 512.5, True),
    (OptionType.CALL, 512.51, True),
    (OptionType.PUT, 520.0, True), (OptionType.PUT, 519.99, True),
    (OptionType.PUT, 520.01, False)])
def test_call_option_itm(test_values_call, test_values_put, option_type, spot_price,
                         expected_value):
    _, call = test_values_call # 512.5 strike
    _, put = test_values_put # 520 strike

    test_option = call if option_type == OptionType.CALL else put
    test_option.spot_price = spot_price

    actual_value = test_option.itm()
    assert actual_value == expected_value

def test_expired_for_daily_data_next_day(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.update_cache = df

    assert OptionStatus.INITIALIZED in call.status

    call.open_trade(quantity=1)
    call.next_update(updates[1]['quote_datetime'])

    assert call.quote_datetime.date() == call.expiration

    next_date = updates[1]['quote_datetime'] + datetime.timedelta(days=1)
    call.next_update(next_date)

    assert OptionStatus.EXPIRED in call.status


@pytest.mark.parametrize("test_quote_datetime, expected_result", [
    (datetime.datetime(2016, 3, 9, 9, 45), False),
    (datetime.datetime(2016, 3, 10, 9, 31), True),
    (datetime.datetime(2016, 3, 9, 16, 14), False),
    (datetime.datetime(2016, 3, 9, 16, 15), True),
])
def test_check_expired_sets_expired_flag_correctly(call_intraday_option, test_quote_datetime, expected_result):
    call, df, updates = call_intraday_option

    assert OptionStatus.EXPIRED not in call.status
    call.quote_datetime = test_quote_datetime
    call._check_expired()

    assert (OptionStatus.EXPIRED in call.status) == expected_result


def test_no_trade_is_open_status_if_trade_was_not_opened(test_values_call):
    _, call = test_values_call
    assert (OptionStatus.TRADE_IS_OPEN in call.status) == False


def test_trade_is_open_status_is_true_if_trade_was_opened(test_values_call):
    _, call = test_values_call
    call.open_trade(quantity=10)
    assert (OptionStatus.TRADE_IS_OPEN in call.status) == True


def test_trade_is_open_status_is_true_if_partially_closed(test_values_call):
    _, call = test_values_call
    call.open_trade(quantity=10)
    call.close_trade(quantity=5)
    assert (OptionStatus.TRADE_IS_OPEN in call.status) == True


def test_trade_is_open_is_false_if_closed(test_values_call):
    _, call = test_values_call
    call.open_trade(quantity=10)
    call.close_trade(quantity=10)
    assert (OptionStatus.TRADE_IS_OPEN in call.status) == False


def test_get_unrealized_profit_loss_raises_exception_if_trade_was_not_opened(test_values_call):
    _, call = test_values_call

    with pytest.raises(Exception, match="This option has no transactions."):
        call.get_unrealized_profit_loss()


def test_get_unrealized_profit_loss_is_zero_if_quote_data_has_not_changed(test_values_call):
    _, call = test_values_call
    call.open_trade(quantity=10)
    pnl = call.get_unrealized_profit_loss()
    assert pnl == 0.0


def test_get_unrealized_profit_loss_is_zero_when_trade_is_closed(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.update_cache = df

    call.open_trade(quantity=10)
    call.next_update(updates[0]['quote_datetime'])
    call.close_trade(quantity=10)

    pnl = call.get_unrealized_profit_loss()

    assert pnl == 0.0


@pytest.mark.parametrize("option_type, quantity, price, expected_profit_loss", [
    (OptionType.CALL, 10, 2.31, 100.0),
    (OptionType.CALL, 10, 2.11, -100.0),
    (OptionType.CALL, 10, 2.21, 0.0),
    (OptionType.CALL, -10, 2.31, -100.0),
    (OptionType.CALL, -10, 2.11, 100.0),
    (OptionType.CALL, -10, 2.21, 0.0),
    (OptionType.PUT, 10, 13.4, 100.0),
    (OptionType.PUT, 10, 13.2, -100.0),
    (OptionType.PUT, 10, 13.3, 0.0),
    (OptionType.PUT, -10, 13.4, -100.0),
    (OptionType.PUT, -10, 13.2, 100.0),
    (OptionType.PUT, -10, 13.3, 0.0)
])
def test_get_unrealized_profit_loss_value(test_values_call, test_values_put, call_updates, put_updates,
                                          option_type, quantity, price, expected_profit_loss):
    if option_type == OptionType.CALL:
        _, test_option = test_values_call
        df, updates = call_updates
    else:
        _, test_option = test_values_put
        df, updates = put_updates
    test_option.update_cache = df

    test_option.open_trade(quantity=quantity)

    test_option.update_cache.loc[0, 'price'] = price
    test_option.next_update(updates[0]['quote_datetime'])

    actual_profit_loss = test_option.get_unrealized_profit_loss()
    assert actual_profit_loss == expected_profit_loss


def test_unrealized_profit_loss_percent_raises_exception_if_trade_was_not_opened(test_values_call):
    _, call = test_values_call

    with pytest.raises(Exception, match="This option has no transactions."):
        call.get_unrealized_profit_loss_percent()


def test_get_unrealized_profit_loss_percent_returns_zero_when_trade_is_closed(test_values_call):
    _, call = test_values_call
    call.open_trade(quantity=1)
    call.close_trade(quantity=1)

    actual_value = call.get_unrealized_profit_loss_percent()
    assert actual_value == 0.0


@pytest.mark.parametrize("option_type, quantity, test_price, expected_profit_loss_pct", [
    (OptionType.CALL, 10, 10.50, 0.05),
    (OptionType.CALL, 10, 9.50, -0.05),
    (OptionType.CALL, 10, 10.0, 0.0),
    (OptionType.CALL, -10, 10.50, -0.05),
    (OptionType.CALL, -10, 9.5, 0.05),
    (OptionType.CALL, -10, 10.0, 0.0),
    (OptionType.PUT, 10, 10.5, 0.05),
    (OptionType.PUT, 10, 9.5, -0.05),
    (OptionType.PUT, 10, 10.0, 0.0),
    (OptionType.PUT, -10, 10.5, -0.05),
    (OptionType.PUT, -10, 9.5, 0.05),
    (OptionType.PUT, -10, 10.0, 0.0)
])
def test_get_unrealized_profit_loss_percent_value(test_values_call, test_values_put,
                                                  call_updates, put_updates,
                                                  option_type, quantity, test_price, expected_profit_loss_pct):
    if option_type == OptionType.CALL:
        _, test_option = test_values_call
        df, updates = call_updates
    else:
        _, test_option = test_values_put
        df, updates = put_updates
    test_option.update_cache = df

    # set price of option to 10 before opening trade
    df.loc[0, 'price'] = 10
    df.loc[1, 'price'] = test_price
    test_option.update_cache = df

    test_option.next_update(updates[0]['quote_datetime'])
    test_option.open_trade(quantity=quantity)

    # update price for test

    test_option.next_update(updates[1]['quote_datetime'])

    actual_profit_loss = test_option.get_unrealized_profit_loss_percent()
    assert actual_profit_loss == expected_profit_loss_pct


@pytest.mark.parametrize("quote_date, expected_days_in_trade", [
    (datetime.datetime.strptime("2016-03-08 09:45", "%Y-%m-%d %H:%M"), 0),
    (datetime.datetime.strptime("2016-03-08 16:15", "%Y-%m-%d %H:%M"), 0),
    (datetime.datetime.strptime("2016-03-09 09:55", "%Y-%m-%d %H:%M"), 1),
])
def test_get_days_in_trade(call_intraday_option, quote_date, expected_days_in_trade):
    call, df, updates = call_intraday_option
    call.update_cache = df
    call.open_trade(quantity=1)


    call.next_update(quote_date)
    days_in_trade = call.get_days_in_trade()
    assert days_in_trade == expected_days_in_trade


def test_get_profit_loss_raises_exception_if_not_traded(test_values_call):
    _, call = test_values_call

    with pytest.raises(Exception, match="This option has not been traded."):
        call.get_profit_loss()
        pass


@pytest.mark.parametrize("option_type, qty, test_price, expected_value", [
    (OptionType.CALL, 10, 15.0, 5000.0),
    (OptionType.CALL, 10, 5.0, -5000.0),
    (OptionType.CALL, -10, 15.0, -5000.0),
    (OptionType.CALL, -10, 5.0, 5000.0),
    (OptionType.PUT, 10, 15.0, 5000.0),
    (OptionType.PUT, 10, 5.0, -5000.0),
    (OptionType.PUT, -10, 15.0, -5000.0),
    (OptionType.PUT, -10, 5.0, 5000.0),

])
def test_get_total_profit_loss_returns_unrealized_when_no_contracts_are_closed(test_values_call, test_values_put, call_updates, put_updates,
                                                                               option_type, qty, test_price, expected_value):
    if option_type == OptionType.CALL:
        _, test_option = test_values_call
        df, updates = call_updates
    else:
        _, test_option = test_values_put
        df, updates = put_updates
    df.loc[0, 'price'] = 10.0
    df.loc[1, 'price'] = test_price
    test_option.update_cache = df

    test_option.next_update(updates[0]['quote_datetime'])
    test_option.open_trade(quantity=qty)

    test_option.next_update(updates[1]['quote_datetime'])

    actual_value = test_option.get_profit_loss()
    assert actual_value == expected_value


def test_get_profit_loss_returns_closed_pnl_when_all_contracts_are_closed(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.update_cache = df

    call.open_trade(quantity=10)
    call.next_update(updates[0]['quote_datetime'])
    call.close_trade(quantity=10)

    assert call.get_profit_loss() == 100.0


def test_get_profit_loss_returns_unrealized_and_closed_pnl_when_partially_closed(test_values_call, call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.update_cache = df

    call.open_trade(quantity=10)

    call.next_update(updates[0]['quote_datetime'])
    call.close_trade(quantity=5) # up $50 - $10 for 5 closed contracts
    call.next_update(updates[1]['quote_datetime']) # up $497 per contract, $2_485

    assert call.get_profit_loss() == 2_535.0

def test_get_total_profit_loss_returns_unrealized_and_closed_pnl_when_multiple_close_trades(
        test_values_put,
        put_updates):
    _, put = test_values_put
    df, updates = put_updates
    put.update_cache = df

    put.open_trade(quantity=-10) # price 13.3

    # close the first 3 contracts at updated price
    put.next_update(updates[0]['quote_datetime']) # price 10.58
    put.close_trade(quantity=-3)  # $816

    # close another 3 contracts at updated price
    put.next_update(updates[1]['quote_datetime']) # price 5.5
    put.close_trade(quantity=-3)  # $2_340

    # update the price to the next time slot values
    put.next_update(updates[2]['quote_datetime']) # price 1.42, unrealized for 4 contracts = 4_752

    actual_value = put.get_profit_loss()
    assert actual_value == 7908.0


def test_get_profit_loss_percent_raises_exception_if_not_traded(test_values_call):
    _, call = test_values_call

    with pytest.raises(Exception, match="This option has not been traded."):
        call.get_profit_loss_percent()


@pytest.mark.parametrize("option_type, qty, test_price, expected_value", [
    (OptionType.CALL, 10, 12.0, 0.2),
    (OptionType.CALL, -10, 12.0, -0.2),
    (OptionType.PUT, 10, 12.0, 0.2),
    (OptionType.PUT, -10, 12.0, -0.2),
])
def test_get_profit_loss_percent_returns_unrealized_when_no_contracts_are_closed(test_values_call, test_values_put,
                                                                                 call_updates, put_updates, option_type,
                                                                                     qty, test_price, expected_value):
    if option_type == OptionType.CALL:
        _, test_option = test_values_call
        df, updates = call_updates
    else:
        _, test_option = test_values_put
        df, updates = put_updates

    df.loc[0, 'price'] = 10.0 # open price
    df.loc[1, 'price'] = test_price
    test_option.update_cache = df

    test_option.next_update(updates[0]['quote_datetime'])
    test_option.open_trade(quantity=qty)

    test_option.next_update(updates[1]['quote_datetime'])

    actual_value = test_option.get_profit_loss_percent()
    assert actual_value == expected_value


@pytest.mark.parametrize("option_type, qty, test_price, expected_value", [
    (OptionType.CALL, 10, 12, 0.2),
    (OptionType.CALL, -10, 12, -0.2),
    (OptionType.PUT, 10, 12, 0.2),
    (OptionType.PUT, -10, 12, -0.2),
])
def test_get_total_profit_loss_percent_returns_closed_pnl_when_all_contracts_are_closed(test_values_call, test_values_put,
                                                                                        call_updates, put_updates,
                                                                                        option_type, qty, test_price,
                                                                                        expected_value):
    if option_type == OptionType.CALL:
        _, test_option = test_values_call
        df, updates = call_updates
    else:
        _, test_option = test_values_put
        df, updates = put_updates

    df.loc[0, 'price'] = 10.0
    df.loc[1, 'price'] = test_price
    test_option.update_cache = df
    test_option.next_update(updates[0]['quote_datetime'])

    test_option.open_trade(quantity=qty)

    test_option.next_update(updates[1]['quote_datetime'])
    test_option.close_trade(quantity=qty)

    assert test_option.get_profit_loss_percent() == expected_value


@pytest.mark.parametrize(" qty, close_qty_1, close_qty_2, price1, price2, price3, expected_value", [
    (10, 4, 2, 9.0, 8.0, 6.0, -0.24),
    (-10, -4, -2, 9.0, 8.0, 6.0, 0.24),
    (10, 4, 2, 9.0, 8.0, 6.0, -0.24),
    (-10, -4, -2, 9.0, 8.0, 6.0, 0.24),
])
def test_get_total_profit_loss_percent_returns_unrealized_and_closed_pnl_when_multiple_close_trades(
        test_values_put,
        put_updates,
        qty,
        close_qty_1,
        close_qty_2,
        price1, price2,
        price3,
        expected_value):
    test_values, _ = test_values_put
    df, updates = put_updates

    test_option = Option(option_id=test_values['option_id'],
                         symbol=test_values['symbol'],
                         strike=test_values['strike'],
                         expiration=test_values['expiration'],
                         option_type=test_values['option_type'],
                         quote_datetime=test_values['quote_datetime'],
                         spot_price=test_values['spot_price'],
                         bid=test_values['bid'],
                         ask=test_values['ask'],
                         price=10.0) # starting price


    df.loc[0, 'price'] = price1
    df.loc[1, 'price'] = price2
    df.loc[2, 'price'] = price3
    test_option.update_cache = df
    test_option.open_trade(quantity=qty)

    test_option.next_update(updates[0]['quote_datetime'])
    test_option.close_trade(quantity=close_qty_1)

    test_option.next_update(updates[1]['quote_datetime'])
    test_option.close_trade(quantity=close_qty_2)  # 1050

    test_option.next_update(updates[2]['quote_datetime'])

    actual_value = test_option.get_profit_loss_percent()
    assert actual_value == expected_value


def test_option_properties_return_none_when_no_data(test_values_call):
    test_values, call = test_values_call
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

    assert test_option.delta is None
    assert test_option.gamma is None
    assert test_option.theta is None
    assert test_option.vega is None
    assert test_option.rho is None

    assert test_option.open_interest is None
    assert test_option.implied_volatility is None


def test_open_option_emits_open_transaction_completed_event(test_values_call):
    _, call= test_values_call
    test_open_info = None

    class MyPortfolio:

        @staticmethod
        def on_option_opened(trade_open_info):
            nonlocal test_open_info
            test_open_info = trade_open_info

    my_portfolio = MyPortfolio()
    call.bind(open_transaction_completed=my_portfolio.on_option_opened)

    call.open_trade(quantity=1)

    assert test_open_info is not None
    assert test_open_info.option_id == call.option_id
    assert test_open_info.date == call.quote_datetime
    assert test_open_info.quantity == 1


def test_close_option_emits_close_transaction_completed_event(test_values_call,
                                                              call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.update_cache = df
    test_close_info = None

    # create handler method
    class MyPortfolio:

        @staticmethod
        def on_option_closed(trade_close_info):
            nonlocal test_close_info
            test_close_info = trade_close_info

    my_portfolio = MyPortfolio()
    call.bind(close_transaction_completed=my_portfolio.on_option_closed)
    quote_date = updates[0]['quote_datetime']

    call.open_trade(quantity=10)

    call.next_update(quote_date)
    call.close_trade(quantity=5)

    assert test_close_info is not None
    assert test_close_info.option_id == call.option_id
    assert test_close_info.date == quote_date
    assert test_close_info.quantity == -5


def test_update_to_expired_date_emits_option_expired_event(test_values_call,
                                                           call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.update_cache = df

    expired_option_id = None

    # Create handler method
    class MyPortfolio:

        @staticmethod
        def on_option_expired(option_id):
            nonlocal expired_option_id
            expired_option_id = option_id

    my_portfolio = MyPortfolio()
    call.bind(option_expired=my_portfolio.on_option_expired)

    # update to last day of option
    last_quote_date = updates[-1]['quote_datetime']
    call.next_update(last_quote_date)

    # update to next day - which is expired
    expired_date = last_quote_date + datetime.timedelta(days=1)

    call.next_update(expired_date)
    assert expired_option_id == call.option_id


def test_fees_incurred_event_emitted_when_open_or_close_fees_are_incurred(test_values_call,
                                                                          call_updates):
    _, call = test_values_call
    df, updates = call_updates
    call.update_cache = df
    my_fees = None

    # create handler method
    class MyPortfolio:

        @staticmethod
        def on_fees_incurred(fees):
            nonlocal my_fees
            my_fees = fees

    my_portfolio = MyPortfolio()
    call.bind(fees_incurred=my_portfolio.on_fees_incurred)

    call.open_trade(quantity=10)
    assert my_fees == 5.0

    my_fees = 0

    call.next_update(updates[0]['quote_datetime'])
    assert my_fees == 0

    call.close_trade(quantity=5)
    assert my_fees == 2.5


def test_current_value_is_zero_if_no_trades(test_values_call):
    _, call = test_values_call

    assert call.current_value == 0.0


def test_current_value_is_same_as_open_premium_if_no_price_change(test_values_call):
    _, call = test_values_call
    open_info = call.open_trade(quantity=1)
    premium = open_info.premium

    assert call.current_value == premium


def test_current_value_is_updated_when_price_changes(test_values_call, call_updates):
    test_values, call = test_values_call
    df, updates = call_updates
    call.update_cache = df

    call.open_trade(quantity=1)
    call.next_update(updates[0]['quote_datetime'])

    new_premium = updates[0]['price'] * 100

    assert call.current_value == new_premium


def test_current_value_when_partially_closed_price_changes(test_values_put, put_updates):
    test_values, put = test_values_put
    df, updates = put_updates
    put.update_cache = df

    put.open_trade(quantity=10) # price 13.3
    put.next_update(updates[0]['quote_datetime'])
    assert put.current_value == 10_580.0

    put.close_trade(quantity=5)
    assert put.current_value == 5_290.0

    put.next_update(updates[1]['quote_datetime'])
    assert put.current_value == 2_750.0

    put.close_trade(quantity=3)
    assert put.current_value == 1_100.0

    put.next_update(updates[2]['quote_datetime'])
    assert put.current_value == 284.0

    put.close_trade(quantity=2)
    assert put.current_value == 0.0

# def test_get_closing_price_for_expiring_itm():
#     pass
#
# def test_open_option_with_slippage():
#     pass
#
# def test_close_option_with_slippage():
#     pass
#
