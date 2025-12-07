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
