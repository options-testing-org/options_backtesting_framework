import datetime

import pytest

from options_framework.option_types import OptionType, OptionPositionType

from options_framework.spreads.vertical import Vertical
from tests.mocks import MockPortfolio, MockSPXOptionChain


@pytest.fixture
def option_values():
    expiration = datetime.date(2016, 3, 2)
    strike1 = 1940
    return expiration, strike1

def test_get_call_debit_spread(option_values, spx_option_chain_calls):
    expiration, strike1 = option_values
    option_chain, _ = spx_option_chain_calls
    spread_width = 30
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.CALL,
                                            long_strike=strike1, short_strike=strike1+spread_width)

    assert vertical_spread.long_option.strike == 1940
    assert vertical_spread.short_option.strike == 1970
    assert vertical_spread.max_profit == 1738.0
    assert vertical_spread.max_loss == 1262.0

def test_get_put_debit_spread(option_values, spx_option_chain_puts):
    expiration, strike1 = option_values
    option_chain, _ = spx_option_chain_puts
    spread_width = 30
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.PUT,
                                            long_strike=strike1, short_strike=strike1-spread_width)

    assert vertical_spread.long_option.strike == 1940
    assert vertical_spread.short_option.strike == 1910
    assert vertical_spread.max_profit == 2458.0
    assert vertical_spread.max_loss == 542.0

def test_get_call_credit_spread(option_values, spx_option_chain_calls):
    expiration, strike1 = option_values
    option_chain, _ = spx_option_chain_calls
    spread_width = 30
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.CALL,
                                            long_strike=strike1, short_strike=strike1 - spread_width)

    assert vertical_spread.long_option.strike == 1940
    assert vertical_spread.short_option.strike == 1910
    assert vertical_spread.max_profit == 2425.0
    assert vertical_spread.max_loss == 575.0

def test_get_put_credit_spread(option_values, spx_option_chain_puts):
    expiration, strike1 = option_values
    option_chain, _ = spx_option_chain_puts
    spread_width = 30
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.PUT,
                                            long_strike=strike1-spread_width, short_strike=strike1)

    assert vertical_spread.long_option.strike == 1910
    assert vertical_spread.short_option.strike == 1940
    assert vertical_spread.max_profit == 542.0
    assert vertical_spread.max_loss == 2458.0

def test_vertical_spread_updates(option_values, spx_option_chain_calls):
    expiration, strike1 = option_values
    option_chain, loader = spx_option_chain_calls
    spread_width = 30
    vertical_spread = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.CALL,
                                            long_strike=strike1, short_strike=strike1 + spread_width)

    # Open position and get updates
    portfolio = MockPortfolio()
    portfolio.bind(new_position_opened=loader.on_options_opened)
    portfolio.open_position(vertical_spread)

    # Advance a couple of date slots and get updates
    assert vertical_spread.current_value == 1262.0
    next_date = loader.datetimes_list.iloc[1].name
    portfolio.next(next_date)
    assert vertical_spread.current_value == 1190.0
    portfolio.next(loader.datetimes_list.iloc[2].name)
    assert vertical_spread.current_value == 1270.0

def test_get_max_profit_after_closed():
    pass

def test_get_max_loss_after_closed():
    pass

def test_credit_spread_required_margin(option_values, spx_option_chain_calls):
    expiration, strike1 = option_values
    option_chain, _ = spx_option_chain_calls
    spread_width = 30
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                                      option_type=OptionType.CALL,
                                                      long_strike=strike1, short_strike=strike1 - spread_width)

    quantity = -10
    expected_margin = 30_000

    vertical_spread.open_trade(quantity=quantity)

    assert vertical_spread.required_margin == expected_margin

def test_get_long_call_vertical_by_delta(option_values, spx_option_chain):
    expiration, strike1 = option_values
    option_chain, loader = spx_option_chain
    long_delta = .26
    short_delta = .16

    call_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration, option_type=OptionType.CALL,
                                                 long_delta=long_delta, short_delta=short_delta)

    assert call_spread.option_position_type == OptionPositionType.LONG
    assert call_spread.max_loss == 97.0 # 2.65 - 1.68
    assert call_spread.max_profit == 403.0 # 5 (spread) - (2.65 - 1.68)

def test_get_short_call_vertical_by_delta(option_values, spx_option_chain):
    expiration, strike1 = option_values
    option_chain, loader = spx_option_chain
    short_delta = .26 # 1965 strike, price 2.65 delta 21.65
    long_delta = .16 # 1970 strike, price 1.68 delta 15.22

    call_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration,
                                                 option_type=OptionType.CALL,
                                                 long_delta=long_delta, short_delta=short_delta)

    assert call_spread.option_position_type == OptionPositionType.SHORT
    assert call_spread.max_profit == 97.0 # 2.65 - 1.68
    assert call_spread.max_loss == 403.0 # 5 (spread) - (2.65 - 1.68)

def test_get_long_put_vertical_by_delta(option_values, spx_option_chain):
    expiration, strike1 = option_values
    option_chain, loader = spx_option_chain
    long_delta = .26
    short_delta = .16

    put_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration,
                                                option_type=OptionType.PUT,
                                                long_delta=long_delta, short_delta=short_delta)

    assert put_spread.option_position_type == OptionPositionType.LONG

def test_get_short_put_vertical_by_delta(option_values, spx_option_chain):
    expiration, strike1 = option_values
    option_chain, loader = spx_option_chain
    short_delta = .26
    long_delta = .16

    put_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration,
                                                option_type=OptionType.PUT,
                                                long_delta=long_delta, short_delta=short_delta)

    assert put_spread.option_position_type == OptionPositionType.SHORT

def test_long_call_spread_by_delta_and_strike(option_values, spx_option_chain):
    expiration, strike1 = option_values
    option_chain = MockSPXOptionChain()
    delta = .40


    credit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=option_chain, expiration=expiration,
                                                                    option_type=OptionType.CALL,
                                                                    option_position_type=OptionPositionType.LONG,
                                                                    delta=delta, spread_width=5)
    assert credit_spread.option_position_type == OptionPositionType.LONG
    assert credit_spread.long_option.strike < credit_spread.short_option.strike
    assert abs(credit_spread.long_option.strike - credit_spread.short_option.strike) == 5
    pass