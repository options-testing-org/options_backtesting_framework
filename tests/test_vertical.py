import datetime

import pytest

from options_framework.option import Option
from options_framework.option_types import OptionPositionType
from options_framework.spreads.vertical import Vertical

from tests.test_data.test_option_data import *
from test_data.test_options_intraday import *
from mocks import MockEventDispatcher, MockOptionChain

def test_get_call_debit_spread(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    long_strike = 100.0
    short_strike = 110.0

    vertical = Vertical.create(option_chain, expiration, option_type='call', long_strike=long_strike, short_strike=short_strike)

    repr = str(vertical)
    assert repr.startswith('<VERTICAL')
    assert repr[repr.index(')'):] == ") CALL LONG AAPL 100.0/110.0 2015-01-17>" # skip position id bc it can change when tests run
    assert vertical.long_option.strike == long_strike
    assert vertical.short_option.strike == short_strike
    assert vertical.option_position_type == OptionPositionType.LONG

def test_get_call_credit_spread(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    long_strike = 110.0
    short_strike = 100.0

    vertical = Vertical.create(option_chain, expiration, option_type='call', long_strike=long_strike,
                               short_strike=short_strike)

    repr = str(vertical)
    assert repr.startswith('<VERTICAL')
    assert repr[repr.index(
        ')'):] == ") CALL SHORT AAPL 110.0/100.0 2015-01-17>"  # skip position id bc it can change when tests run
    assert vertical.long_option.strike == long_strike
    assert vertical.short_option.strike == short_strike
    assert vertical.option_position_type == OptionPositionType.SHORT

def test_get_put_debit_spread(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    long_strike = 110.0
    short_strike = 100.0

    vertical = Vertical.create(option_chain, expiration, option_type='put', long_strike=long_strike,
                               short_strike=short_strike)

    repr = str(vertical)
    assert repr.startswith('<VERTICAL')
    assert repr[repr.index(
        ')'):] == ") PUT LONG AAPL 110.0/100.0 2015-01-17>"  # skip position id bc it can change when tests run
    assert vertical.long_option.strike == long_strike
    assert vertical.short_option.strike == short_strike
    assert vertical.option_position_type == OptionPositionType.LONG

def test_get_put_credit_spread(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    long_strike = 100.0
    short_strike = 110.0

    vertical = Vertical.create(option_chain, expiration, option_type='put', long_strike=long_strike,
                               short_strike=short_strike)

    repr = str(vertical)
    assert repr.startswith('<VERTICAL')
    assert repr[repr.index(
        ')'):] == ") PUT SHORT AAPL 100.0/110.0 2015-01-17>"  # skip position id bc it can change when tests run
    assert vertical.long_option.strike == long_strike
    assert vertical.short_option.strike == short_strike
    assert vertical.option_position_type == OptionPositionType.SHORT

