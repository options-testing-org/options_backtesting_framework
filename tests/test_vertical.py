import datetime

import pytest

from options_framework.option_types import OptionType, OptionPositionType, SelectFilter
from options_framework.spreads.vertical import Vertical
from tests.mocks import MockPortfolio, MockSPXOptionChain, MockSPXDataLoader

def test_get_call_debit_spread():
    expiration = datetime.date(2016, 3, 2)
    long_strike = 1950
    short_strike = 1960
    option_chain = MockSPXOptionChain()
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.CALL,
                                            long_strike=long_strike, short_strike=short_strike)

    assert vertical_spread.option_type == OptionType.CALL
    assert vertical_spread.long_option.strike == 1950
    assert vertical_spread.long_option.option_type == OptionType.CALL
    assert vertical_spread.short_option.strike == 1960
    assert vertical_spread.short_option.option_type == OptionType.CALL
    assert vertical_spread.max_profit == 570.0
    assert vertical_spread.max_loss == 430.0

def test_get_put_debit_spread():
    expiration = datetime.date(2016, 3, 2)
    long_strike = 1945
    short_strike = 1925
    option_chain = MockSPXOptionChain()
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.PUT,
                                            long_strike=long_strike, short_strike=short_strike)

    assert vertical_spread.option_position_type == OptionPositionType.LONG
    assert vertical_spread.option_type == OptionType.PUT
    assert vertical_spread.long_option.strike == 1945
    assert vertical_spread.short_option.strike == 1925
    assert vertical_spread.max_profit == 1450.0
    assert vertical_spread.max_loss == 550.0

def test_get_call_credit_spread():
    expiration = datetime.date(2016, 3, 2)
    long_strike = 1960
    short_strike = 1950
    option_chain = MockSPXOptionChain()
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.CALL,
                                            long_strike=long_strike, short_strike=short_strike)

    assert vertical_spread.option_position_type == OptionPositionType.SHORT
    assert vertical_spread.long_option.strike == 1960
    assert vertical_spread.short_option.strike == 1950
    assert vertical_spread.max_profit == 430.0
    assert vertical_spread.max_loss == 570.0

def test_get_put_credit_spread():
    expiration = datetime.date(2016, 3, 2)
    long_strike = 1925
    short_strike = 1935
    option_chain = MockSPXOptionChain()
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.PUT,
                                            long_strike=long_strike, short_strike=short_strike)

    assert vertical_spread.option_position_type == OptionPositionType.SHORT
    assert vertical_spread.long_option.strike == 1925
    assert vertical_spread.short_option.strike == 1935
    assert vertical_spread.max_profit == 220.0
    assert vertical_spread.max_loss == 780.0

def test_vertical_spread_updates():
    expiration = datetime.date(2016, 3, 2)
    long_strike = 1940
    short_strike = 1970
    option_chain = MockSPXOptionChain()
    data_loader = MockSPXDataLoader(start=datetime.datetime(2016, 3, 1, 9, 31),
                                    end=datetime.datetime(2016, 3, 2, 16, 15),
                                    select_filter=SelectFilter(symbol='SPXW'),
                                    extended_option_attributes=[])
    spread_width = 30
    vertical_spread = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                            option_type=OptionType.CALL,
                                            long_strike=long_strike, short_strike=short_strike)

    # Open position and get updates
    portfolio = MockPortfolio()
    portfolio.bind(new_position_opened=data_loader.on_options_opened)
    portfolio.open_position(vertical_spread)

    # Advance a couple of date slots and get updates
    assert vertical_spread.current_value == 1262.0
    portfolio.next(data_loader.datetimes_list[1])
    assert vertical_spread.current_value == 1190.0
    portfolio.next(data_loader.datetimes_list[2])
    assert vertical_spread.current_value == 1270.0

def test_get_max_profit_after_closed():
    pass

def test_get_max_loss_after_closed():
    pass

def test_credit_spread_required_margin():
    expiration = datetime.date(2016, 3, 2)
    long_strike = 1985
    short_strike = 1955
    option_chain = MockSPXOptionChain()
    vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
                                                      option_type=OptionType.CALL,
                                                      long_strike=long_strike, short_strike=short_strike)

    quantity = -10
    expected_margin = 30_000

    vertical_spread.open_trade(quantity=quantity)

    assert vertical_spread.required_margin == expected_margin

def test_get_long_call_vertical_by_delta():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()
    long_delta = .26
    short_delta = .11

    call_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration, option_type=OptionType.CALL,
                                                 long_delta=long_delta, short_delta=short_delta)

    assert call_spread.option_position_type == OptionPositionType.LONG
    assert call_spread.max_loss == 160.0 # 2.65 - 1.68
    assert call_spread.max_profit == 840.0 # 5 (spread) - (2.65 - 1.68)

def test_get_short_call_vertical_by_delta():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()
    short_delta = .26 # 1965 strike, price 2.65 delta 21.65
    long_delta = .11 # 1970 strike, price 1.68 delta 15.22

    call_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration,
                                                 option_type=OptionType.CALL,
                                                 long_delta=long_delta, short_delta=short_delta)

    assert call_spread.option_position_type == OptionPositionType.SHORT
    assert call_spread.max_profit == 160.0 # 2.65 - 1.68
    assert call_spread.max_loss == 840.0 # 5 (spread) - (2.65 - 1.68)

def test_get_long_put_vertical_by_delta():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()
    long_delta = .26
    short_delta = .16

    put_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration,
                                                option_type=OptionType.PUT,
                                                long_delta=long_delta, short_delta=short_delta)

    assert put_spread.option_position_type == OptionPositionType.LONG

def test_get_short_put_vertical_by_delta():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()
    short_delta = .26
    long_delta = .16

    put_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration,
                                                option_type=OptionType.PUT,
                                                long_delta=long_delta, short_delta=short_delta)

    assert put_spread.option_position_type == OptionPositionType.SHORT

def test_long_call_spread_by_delta_and_strike():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()
    delta = .40

    debit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=option_chain, expiration=expiration,
                                                                    option_type=OptionType.CALL,
                                                                    option_position_type=OptionPositionType.LONG,
                                                                    delta=delta, spread_width=5)
    assert debit_spread.option_position_type == OptionPositionType.LONG
    assert debit_spread.long_option.strike < debit_spread.short_option.strike
    assert abs(debit_spread.long_option.strike - debit_spread.short_option.strike) == 5
    assert debit_spread.long_option.delta < delta

def test_SHORT_call_spread_by_delta_and_strike():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()
    delta = .40

    credit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=option_chain, expiration=expiration,
                                                                    option_type=OptionType.CALL,
                                                                    option_position_type=OptionPositionType.SHORT,
                                                                    delta=delta, spread_width=5)

    assert credit_spread.option_position_type == OptionPositionType.SHORT
    assert credit_spread.short_option.strike == 1955
    assert credit_spread.long_option.strike == 1960

def test_long_put_spread_by_delta_and_strike():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()
    delta = .40

    debit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=option_chain, expiration=expiration,
                                                                    option_type=OptionType.PUT,
                                                                    option_position_type=OptionPositionType.LONG,
                                                                    delta=delta, spread_width=5)

    assert debit_spread.option_position_type == OptionPositionType.LONG
    assert debit_spread.short_option.strike == 1935
    assert debit_spread.long_option.strike == 1940

def test_SHORT_put_spread_by_delta_and_strike():
    expiration = datetime.date(2016, 3, 2)
    option_chain = MockSPXOptionChain()
    delta = .40

    credit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=option_chain, expiration=expiration,
                                                                    option_type=OptionType.PUT,
                                                                    option_position_type=OptionPositionType.SHORT,
                                                                    delta=delta, spread_width=5)

    assert credit_spread.option_position_type == OptionPositionType.SHORT
    assert credit_spread.short_option.strike == 1940
    assert credit_spread.long_option.strike == 1935
