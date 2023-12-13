import datetime

import pytest

from options_framework.option_types import OptionType, OptionCombinationType, OptionStatus, SelectFilter, FilterRange
from options_framework.spreads.single import Single





@pytest.fixture
def option_values():
    expiration = datetime.date(2016, 3, 2)
    option_type = OptionType.PUT
    strike = 1950
    return expiration, option_type, strike


def test_get_single_option(option_chain, option_values):
    expiration, option_type, strike = option_values
    chain, _ = option_chain
    options = chain.option_chain
    single_option = Single.get_single_position(options=options, expiration=expiration, option_type=option_type,
                                               strike=strike)

    assert single_option.option_combination_type == OptionCombinationType.SINGLE
    assert single_option.expiration == expiration
    assert single_option.option_type == option_type
    assert single_option.strike == strike


def test_open_single_option(option_chain, option_values):
    expiration, option_type, strike = option_values
    chain, _ = option_chain
    options = chain.option_chain
    single_option = Single.get_single_position(options=options, expiration=expiration, option_type=option_type,
                                               strike=strike)

    single_option.open_trade(quantity=1)

    assert OptionStatus.TRADE_IS_OPEN in single_option.option.status
    assert single_option.option.quantity == 1


def test_open_single_option_loads_option_update_cache(option_chain, option_values):
    expiration, option_type, strike = option_values
    chain, loader = option_chain
    options = chain.option_chain
    single_option = Single.get_single_position(options=options, expiration=expiration, option_type=option_type,
                                               strike=strike)
    price = single_option.option.price
    from pydispatch import Dispatcher

    class MockPortfolio(Dispatcher):
        _events_ = ['new_position_opened', 'next']

        def open_position(self, position):
            position.open_trade(quantity=1)
            self.emit('new_position_opened', self, position.options)

    portfolio = MockPortfolio()

    portfolio.bind(new_position_opened=loader.on_options_opened)
    portfolio.open_position(single_option)

    assert single_option.option.update_cache is not None

    quote_datetime = datetime.datetime(2016, 3, 1, 9, 32)
    single_option.option.next_update(quote_datetime=quote_datetime)
    assert single_option.option.price != price

