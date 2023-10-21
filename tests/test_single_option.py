import pytest

from options_framework.option_types import OptionCombinationType, OptionTradeType
from options_framework.spreads.option_combo import OptionCombination
from options_framework.spreads.single import Single
from options_test_helper import *

def test_has_correct_option_combination_type():
    option = get_4310_call_option()
    option.open_trade(10)

    call_position = Single(option)

    assert call_position.option_combination_type == OptionCombinationType.SINGLE

def test_has_correct_option_trade_type():
    long_option = get_4310_call_option()
    long_option.open_trade(10)
    short_option = get_4320_call_option()
    short_option.open_trade(-10)

    long_call_position = Single(long_option)
    short_call_position = Single(short_option)

    assert long_call_position.option_trade_type == OptionTradeType.DEBIT
    assert short_call_position.option_trade_type == OptionTradeType.CREDIT

def test_has_none_max_loss_and_max_profit():
    option = get_4310_call_option()
    option.open_trade(10)
    call_position = Single(option)

    assert call_position.max_profit() is None
    assert call_position.max_loss() is None

def test_long_call_breakeven():
    option = get_4310_call_option()
    option.open_trade(10)
    call_position = Single(option)
    expected_breakeven = 4_340.85

    assert call_position.breakeven_price() == expected_breakeven

def test_short_call_breakeven():
    option = get_4310_call_option()
    option.open_trade(-10)
    call_position = Single(option)
    expected_breakeven = 4_340.85

    assert call_position.breakeven_price() == expected_breakeven

def test_long_put_breakeven():
    long_option = get_4210_put_option()
    long_option.open_trade(10)
    put_position = Single(long_option)
    expected_breakeven = 4_196.05

    assert put_position.breakeven_price() == expected_breakeven

def test_short_put_breakeven():
    short_option = get_4210_put_option()
    short_option.open_trade(10)
    put_position = Single(short_option)
    expected_breakeven = 4_196.05

    assert put_position.breakeven_price() == expected_breakeven
