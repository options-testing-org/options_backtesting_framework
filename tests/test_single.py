import datetime

import pytest

from options_framework.option_types import OptionType, OptionCombinationType, OptionStatus, SelectFilter, FilterRange, \
    OptionPositionType
from options_framework.spreads.single import Single
from tests.mocks import MockPortfolio, MockSPXOptionChain, MockSPXDataLoader


def test_get_single_option():
    expiration = datetime.date(2016, 3, 2)
    strike = 1920
    option_chain = MockSPXOptionChain()
    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type=OptionType.PUT,
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)

    assert single_option.option_combination_type == OptionCombinationType.SINGLE
    assert single_option.expiration == expiration
    assert single_option.option_type == OptionType.PUT
    assert single_option.strike == 1920


def test_open_single_option():
    expiration = datetime.date(2016, 3, 2)
    strike = 1995
    option_chain = MockSPXOptionChain()
    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type=OptionType.PUT,
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)

    single_option.open_trade(quantity=1)

    assert OptionStatus.TRADE_IS_OPEN in single_option.option.status
    assert single_option.option.quantity == 1


def test_open_single_option_loads_option_update_cache():
    expiration = datetime.date(2016, 3, 2)
    strike = 1950
    option_chain = MockSPXOptionChain()
    data_loader = MockSPXDataLoader(start=datetime.datetime(2016, 3, 1, 9, 31),
                                    end=datetime.datetime(2016, 3, 2, 16, 15),
                                    select_filter=SelectFilter(),
                                    extended_option_attributes=[])
    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type=OptionType.PUT,
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)
    portfolio = MockPortfolio()

    portfolio.bind(new_position_opened=data_loader.on_options_opened)
    portfolio.open_position(single_option)

    assert single_option.current_value == 1050.0
    portfolio.next(data_loader.datetimes_list[1])
    assert single_option.current_value == 1100.0
    portfolio.next(data_loader.datetimes_list[2])
    assert single_option.current_value == 1060.0

def test_naked_put_margin_requirement():
    expiration = datetime.date(2016, 3, 2)
    strike = 1930
    option_chain = MockSPXOptionChain()

    qty = -1

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type=OptionType.PUT,
                                      option_position_type=OptionPositionType.SHORT,
                                      strike=strike)
    single_option.open_trade(quantity=qty)

    assert single_option.required_margin ==  40_473.2

def test_get_single_option_gets_next_expiration_when_expiration_is_not_in_chain():
    expiration = datetime.date(2016, 3, 2)
    strike = 1930
    option_chain = MockSPXOptionChain()

    test_expiration = expiration - datetime.timedelta(days=1)

    single_option = Single.get_single(option_chain=option_chain,
                                      expiration=test_expiration,
                                      option_type=OptionType.PUT,
                                      option_position_type=OptionPositionType.LONG,
                                      strike=strike)

    assert single_option.expiration == expiration

def test_get_single_put_option_gets_next_lower_strike_when_strike_is_not_in_chain():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()

    test_strike = 1938

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type=OptionType.PUT,
                                      option_position_type=OptionPositionType.LONG,
                                      strike=test_strike)

    assert single_option.strike == 1935

def test_get_single_call_option_gets_next_higher_strike_when_strike_is_not_in_chain():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()

    test_strike = 1941

    single_option = Single.get_single(option_chain=option_chain, expiration=expiration,
                                      option_type=OptionType.CALL,
                                      option_position_type=OptionPositionType.LONG,
                                      strike=test_strike)

    assert single_option.strike == 1945
