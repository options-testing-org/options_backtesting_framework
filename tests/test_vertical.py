import datetime

import pytest

from options_framework.option_types import OptionType

from options_framework.spreads.vertical import Vertical
from tests.mock_portfolio import MockPortfolio


@pytest.fixture
def option_values():
    expiration = datetime.date(2016, 3, 2)
    strike1 = 1940
    return expiration, strike1

def test_get_call_debit_spread(option_values, spx_option_chain_calls):
    expiration, strike1 = option_values
    chain, _ = spx_option_chain_calls
    spread_width = 30
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=chain.option_chain, expiration=expiration,
                                            option_type=OptionType.CALL,
                                            long_strike=strike1, short_strike=strike1+spread_width)

    assert vertical_spread.long_option.strike == 1940
    assert vertical_spread.short_option.strike == 1970
    assert vertical_spread.max_profit == 1738.0
    assert vertical_spread.max_loss == 1262.0

def test_get_put_debit_spread(option_values, spx_option_chain_puts):
    expiration, strike1 = option_values
    chain, _ = spx_option_chain_puts
    spread_width = 30
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=chain.option_chain, expiration=expiration,
                                            option_type=OptionType.PUT,
                                            long_strike=strike1, short_strike=strike1-spread_width)

    assert vertical_spread.long_option.strike == 1940
    assert vertical_spread.short_option.strike == 1910
    assert vertical_spread.max_profit == 2458.0
    assert vertical_spread.max_loss == 542.0

def test_get_call_credit_spread(option_values, spx_option_chain_calls):
    expiration, strike1 = option_values
    chain, _ = spx_option_chain_calls
    spread_width = 30
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=chain.option_chain, expiration=expiration,
                                            option_type=OptionType.CALL,
                                            long_strike=strike1, short_strike=strike1 - spread_width)

    assert vertical_spread.long_option.strike == 1940
    assert vertical_spread.short_option.strike == 1910
    assert vertical_spread.max_profit == 2425.0
    assert vertical_spread.max_loss == 575.0

def test_get_put_credit_spread(option_values, spx_option_chain_puts):
    expiration, strike1 = option_values
    chain, _ = spx_option_chain_puts
    spread_width = 30
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=chain.option_chain, expiration=expiration,
                                            option_type=OptionType.PUT,
                                            long_strike=strike1-spread_width, short_strike=strike1)

    assert vertical_spread.long_option.strike == 1910
    assert vertical_spread.short_option.strike == 1940
    assert vertical_spread.max_profit == 542.0
    assert vertical_spread.max_loss == 2458.0

def test_vertical_spread_updates(option_values, spx_option_chain_calls):
    expiration, strike1 = option_values
    chain, loader = spx_option_chain_calls
    spread_width = 30
    vertical_spread = Vertical.get_vertical(option_chain=chain.option_chain, expiration=expiration,
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
