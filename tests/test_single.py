import datetime

import pytest

from options_framework.option_types import OptionType, OptionCombinationType, OptionStatus, SelectFilter, FilterRange, \
    OptionPositionType
from options_framework.spreads.single import Single
from tests.mocks import MockPortfolio


@pytest.fixture
def option_values():
    expiration = datetime.date(2016, 3, 2)
    option_type = OptionType.PUT
    strike = 1950
    return expiration, option_type, strike


def test_get_single_option(spx_option_chain_puts, option_values):
    expiration, option_type, strike = option_values
    option_chain, _ = spx_option_chain_puts
    single_option = Single.get_single_position(option_chain=option_chain, expiration=expiration,
                                               option_type=option_type,
                                               option_position_type=OptionPositionType.LONG,
                                               strike=strike)

    assert single_option.option_combination_type == OptionCombinationType.SINGLE
    assert single_option.expiration == expiration
    assert single_option.option_type == option_type
    assert single_option.strike == strike


def test_open_single_option(spx_option_chain_puts, option_values):
    expiration, option_type, strike = option_values
    option_chain, _ = spx_option_chain_puts
    single_option = Single.get_single_position(option_chain=option_chain, expiration=expiration,
                                               option_type=option_type,
                                               option_position_type=OptionPositionType.LONG,
                                               strike=strike)

    single_option.open_trade(quantity=1)

    assert OptionStatus.TRADE_IS_OPEN in single_option.option.status
    assert single_option.option.quantity == 1


def test_open_single_option_loads_option_update_cache(spx_option_chain_puts, option_values):
    expiration, option_type, strike = option_values
    option_chain, loader = spx_option_chain_puts
    single_option = Single.get_single_position(option_chain=option_chain, expiration=expiration,
                                               option_type=option_type,
                                               option_position_type=OptionPositionType.LONG,
                                               strike=strike)
    price = single_option.option.price

    portfolio = MockPortfolio()

    portfolio.bind(new_position_opened=loader.on_options_opened)
    portfolio.open_position(single_option)

    assert single_option.option.update_cache is not None

    quote_datetime = datetime.datetime(2016, 3, 1, 9, 32)
    portfolio.next(quote_datetime)

    assert single_option.option.price != price

def test_naked_put_margin_requirement(spx_option_chain_puts, option_values):
    expiration, option_type, strike = option_values
    option_chain, loader = spx_option_chain_puts

    qty = -1

    single_option = Single.get_single_position(option_chain=option_chain, expiration=expiration,
                                               option_type=option_type,
                                               option_position_type=OptionPositionType.SHORT,
                                               strike=strike)
    single_option.open_trade(quantity=qty)

    margin_requirement = single_option.required_margin

    assert single_option.required_margin ==  38_473.2

def test_get_single_option_gets_next_expiration_when_expiration_is_not_in_chain(spx_option_chain_puts, option_values):
    expiration, option_type, strike = option_values
    option_chain, loader = spx_option_chain_puts

    test_expiration = expiration - datetime.timedelta(days=1)

    single_option = Single.get_single_position(option_chain=option_chain,
                                               expiration=test_expiration,
                                               option_type=option_type,
                                               option_position_type=OptionPositionType.LONG,
                                               strike=strike)

    assert single_option.expiration == expiration

def test_get_single_option_gets_next_strike_when_strike_is_not_in_chain(spx_option_chain_puts, option_values):
    expiration, option_type, strike = option_values
    option_chain, _ = spx_option_chain_puts

    test_strike = strike - 1

    single_option = Single.get_single_position(option_chain=option_chain, expiration=expiration,
                                               option_type=option_type,
                                               option_position_type=OptionPositionType.LONG,
                                               strike=test_strike)

    assert single_option.strike == strike
