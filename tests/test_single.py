import datetime
import pickle
from pathlib import Path

import pytest

from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionCombinationType, OptionStatus, OptionPositionType
from options_framework.spreads.single import Single
from options_framework.config import settings


@pytest.fixture
def option():
    timeslots_folder = Path(settings['options_directory'], 'daily', 'AAPL', 'timeslots', '2014_12')
    data_file = timeslots_folder.joinpath('2014_12_31_00_00.pkl')
    with open(data_file, 'rb') as f:
        data = pickle.load(f)

    option_data = data[3]
    option = Option(**option_data)
    return option

@pytest.fixture
def option_chain():
    symbol = 'AAPL'
    start_date = datetime.datetime.strptime('2014-12-30', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2014-12-31', '%Y-%m-%d')
    option_chain = OptionChain(symbol, start_date, end_date)
    option_chain.on_next(start_date)
    return option_chain


def test_what(option_chain_daily, option):
    quote_date = datetime.datetime.strptime('2015-01-06', '%Y-%m-%d')
    option_chain = option_chain_daily(quote_date)
    pass

@pytest.mark.parametrize("option_type, strike, quantity, expected_repr", [('call', 110.0, 5, '<SINGLE(0) AAPL call 110.0 2015-01-17 5>'),
                                                                          ('call', 120.0, -5, '<SINGLE(1) AAPL call 120.0 2015-01-17 -5>'),
                                                                          ('put', 130.0, 5, '<SINGLE(2) AAPL put 130.0 2015-01-17 5>'),
                                                                          ('put', 100.0, -5, '<SINGLE(3) AAPL put 100.0 2015-01-17 -5>')
                                                                          ])
def test_repr(option_chain_daily, option_type, strike, quantity, expected_repr):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = strike
    quantity = quantity

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type=option_type,
                                      option_position_type=OptionPositionType.SHORT,
                                      strike=strike)
    single_option.quantity = quantity
    repr = str(single_option)
    assert repr == expected_repr

def test_get_single_option_with_exact_values(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)

    expiration = datetime.date(2015, 1, 2)
    strike = 100
    option_type = 'call'
    quantity = 1

    single: Single = Single.get_single(option_chain, expiration, strike, option_type,
                                       option_position_type=OptionPositionType.LONG)

    assert single.option_combination_type == OptionCombinationType.SINGLE
    assert single.expiration == expiration
    assert single.option_type == 'call'
    assert single.strike == strike

def test_get_single_option_next_expiration(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)

    expiration = datetime.date(2015, 1, 15)
    strike = 110
    option_type = 'call'
    quantity = 1

    single: Single = Single.get_single(option_chain, expiration, strike, option_type,
                                       option_position_type=OptionPositionType.LONG)

    assert single.expiration == datetime.date(2015, 1, 17)
    assert single.quantity == quantity


def test_naked_put_margin_requirement_otm(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 100

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='put',
                                      option_position_type=OptionPositionType.SHORT,
                                      strike=strike)
    single_option.open_trade(quantity=-1)

    assert single_option.required_margin ==  1_142.2

def test_naked_put_margin_requirement_itm(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 120
    qty = -1

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='put',
                                      option_position_type=OptionPositionType.SHORT,
                                      strike=strike)
    single_option.open_trade(quantity=qty)

    assert single_option.required_margin ==  3_015.4

def test_get_single_option_gets_next_expiration_when_expiration_is_not_in_chain(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 15)
    strike = 100
    qty = 1

    test_expiration = datetime.date(2015, 1, 17)

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='call',
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)
    single_option.open_trade(quantity=qty)

    assert single_option.expiration == test_expiration

def test_get_single_put_option_gets_next_lower_strike_when_strike_is_not_in_chain(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 115.0

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='put',
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)

    assert single_option.strike == 110.0

def test_get_single_call_option_gets_next_higher_strike_when_strike_is_not_in_chain(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 115.0

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='call',
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)

    assert single_option.strike == 120.0

def test_update_quantity_sets_quantity(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 100.0

    single = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='call',
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)
    assert single.quantity == 1

    single.update_quantity(10)

    assert single.quantity == 10

def test_update_long_position_to_negative_quantity_raises_error(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 100.0

    single = Single.get_single(option_chain=option_chain, expiration=expiration,
                               option_type='call',
                               option_position_type=OptionPositionType.LONG,
                               strike=strike)
    assert single.quantity == 1

    with pytest.raises(ValueError, match='Cannot set a negative quantity on a long position.'):
        single.update_quantity(-10)

def test_update_short_position_to_positive_quantity_raises_error(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 100.0

    single = Single.get_single(option_chain=option_chain, expiration=expiration,
                               option_type='call',
                               option_position_type=OptionPositionType.SHORT,
                               strike=strike)
    assert single.quantity == -1

    with pytest.raises(ValueError, match='Cannot set a positive quantity on a short position.'):
        single.update_quantity(10)

def test_open_trade_sets_quantity_and_status(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 110.0
    quantity = 10

    single = Single.get_single(option_chain=option_chain, expiration=expiration,
                               option_type='call',
                               option_position_type=OptionPositionType.LONG,
                               strike=strike)

    assert OptionStatus.TRADE_IS_OPEN not in single.status

    single.open_trade(quantity=quantity)

    assert single.quantity == quantity
    assert single.options[0].quantity == quantity
    assert OptionStatus.TRADE_IS_OPEN in single.status

def test_close_trade_sets_quantity_and_status(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 110.0
    quantity = 10

    single = Single.get_single(option_chain=option_chain, expiration=expiration,
                               option_type='call',
                               option_position_type=OptionPositionType.LONG,
                               strike=strike)

    single.open_trade(quantity=quantity)

    single.close_trade(quantity=10)

    assert single.quantity == 0
    assert single.option.quantity == 0
    assert OptionStatus.TRADE_IS_CLOSED in single.status

def test_get_trade_price_returns_none_when_no_trade_opened(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 110.0

    single = Single.get_single(option_chain=option_chain, expiration=expiration,
                               option_type='call',
                               option_position_type=OptionPositionType.LONG,
                               strike=strike)

    assert single.get_trade_price() is None

def test_get_trade_price_returns_open_price_after_option_is_updated(option_chain_daily):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = 110.0

    single = Single.get_single(option_chain=option_chain, expiration=expiration,
                               option_type='call',
                               option_position_type=OptionPositionType.LONG,
                               strike=strike)

    # open trade
    single.open_trade(10)
    open_price = single.price

    # update price on option
    single.option.price = single.option.price + 0.10

    assert single.price != open_price
    assert single.get_trade_price() == open_price