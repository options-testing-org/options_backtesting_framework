import datetime

import pytest

from options_framework.option_types import OptionCombinationType, OptionStatus, OptionPositionType
from options_framework.spreads.single import Single
from tests.mocks import *

@pytest.fixture
def quote_date():
    return datetime.datetime.strptime('2014-02-05', '%Y-%m-%d')

def test_get_single_option_with_exact_values(option_chain_daily, quote_date):
    test_option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2014, 2, 7)
    strike = 515
    single_option = Single.get_single(option_chain=test_option_chain, expiration=expiration,
                                      option_type='call',
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)

    assert single_option.option_combination_type == OptionCombinationType.SINGLE
    assert single_option.expiration == expiration
    assert single_option.option_type == 'call'
    assert single_option.strike ==strike

def test_get_single_option_next_expiration(option_chain_daily, quote_date):
    test_option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2014, 2, 8)
    strike = 519
    single_option = Single.get_single(option_chain=test_option_chain,
                                      expiration=expiration,
                                      option_position_type=OptionPositionType.LONG,
                                      option_type='call',
                                      strike=strike,
                                      quantity=5)

    assert single_option.expiration == datetime.date(2014, 2, 14)
    assert single_option.quantity == 5
    assert single_option.strike == 520



def test_naked_put_margin_requirement_otm(option_chain_daily, quote_date):
    option_chain = option_chain_daily(quote_date)
    expiration = option_chain.expirations[0]
    strike = 510
    qty = -1

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='put',
                                      option_position_type=OptionPositionType.SHORT,
                                      strike=strike)
    single_option.open_trade(quantity=qty)

    assert single_option.required_margin ==  10_360.8

def test_naked_put_margin_requirement_itm(option_chain_daily):
    quote_date = datetime.datetime.strptime('2014-02-10','%Y-%m-%d')
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.datetime.strptime('2014-02-14','%Y-%m-%d').date()
    strike = 640
    qty = -1

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='put',
                                      option_position_type=OptionPositionType.SHORT,
                                      strike=strike)
    single_option.open_trade(quantity=qty)

    assert single_option.required_margin ==  21_686.8

def test_get_single_option_gets_next_expiration_when_expiration_is_not_in_chain(option_chain_daily):
    quote_date = datetime.datetime.strptime('2014-02-10','%Y-%m-%d')
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.datetime.strptime('2014-02-15','%Y-%m-%d').date()
    strike = 515
    qty = 1

    test_expiration = datetime.datetime.strptime('2014-02-22','%Y-%m-%d').date()

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='call',
                                      option_position_type=OptionPositionType.SHORT,
                                      strike=strike)
    single_option.open_trade(quantity=qty)

    assert single_option.expiration == test_expiration

def test_get_single_put_option_gets_next_lower_strike_when_strike_is_not_in_chain(option_chain_daily, quote_date):
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2014, 2, 8)
    strike = 530

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='put',
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)

    assert single_option.strike == 520

def test_get_single_call_option_gets_next_higher_strike_when_strike_is_not_in_chain(option_chain_daily, quote_date):
    option_chain = option_chain_daily(quote_date)
    expiration = datetime.date(2014, 2, 8)
    strike = 516

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type='call',
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)

    assert single_option.strike == 520
