import copy
import datetime
from dataclasses import dataclass
from typing import Self

import pytest

from options_framework.option import Option
from options_framework.option_types import OptionCombinationType, OptionPositionType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase

@dataclass(repr=False, slots=True)
class TestOption(SpreadBase):

    @classmethod
    def create(cls, options: list[Option], *args, **kwargs) -> Self:
        test_option = TestOption(options, OptionCombinationType.CUSTOM)
        super(TestOption, test_option)._save_user_defined_values(test_option, **kwargs)
        return test_option

    def __post_init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "test option"

    def _update_quantity(self, quantity: int):
        pass

    def open_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        super(TestOption, self)._save_user_defined_values(self, **kwargs)

    def close_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        super(TestOption, self)._save_user_defined_values(self, **kwargs)

    @property
    def max_profit(self) -> float | None:
        pass

    @property
    def max_loss(self) -> float | None:
        pass

    @property
    def required_margin(self) -> float:
        pass

    @property
    def status(self) -> OptionStatus:
        pass

    @property
    def price(self) -> float:
        pass

    def get_trade_price(self) -> float | None:
        pass


def test_create_option_base_fails():

    with pytest.raises(NotImplementedError):
        SpreadBase.create()

def test_instantiate_child_class_succeeds(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)

    test_spread = TestOption.create([option1, option2], 'a value', what='so what')
    assert test_spread.option_combination_type == OptionCombinationType.CUSTOM
    assert test_spread.quantity == 1 == 1 # default quantity
    assert test_spread.position_id is not None # position id is set

def test_current_value_is_sum_of_options_current_values(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option1.incur_fees = False
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)
    option2.incur_fees = False

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])

    expected_current_value = option1.current_value + option2.current_value
    assert test_spread.current_value == expected_current_value

    # advance date and update options
    quote_date = datetime.datetime(2014, 12, 31, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    expected_current_value = option1.current_value + option2.current_value
    assert test_spread.current_value == expected_current_value

def test_trade_value_after_advancing_date(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])

    options_current_value_on_open = option1.current_value + option2.current_value
    assert test_spread.trade_value == options_current_value_on_open
    assert test_spread.current_value == options_current_value_on_open

    # advance date and update options
    quote_date = datetime.datetime(2014, 12, 31, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)
    assert test_spread.trade_value == options_current_value_on_open
    assert test_spread.current_value != options_current_value_on_open

def test_sets_user_defined_values_on_open_trade():
    test_spread = TestOption.create([])
    test_spread.open_trade(1, what='what?', abc='xyz')

    assert test_spread.user_defined['what'] == 'what?'
    assert test_spread.user_defined['abc'] == 'xyz'

def test_sets_user_defined_values_on_close_trade():
    test_spread = TestOption.create([])
    test_spread.close_trade(1, what='what?', abc='xyz')

    assert test_spread.user_defined['what'] == 'what?'
    assert test_spread.user_defined['abc'] == 'xyz'

def test_sets_user_defined_values_on_create():
    test_spread = TestOption.create([], what='what?', abc='xyz')

    assert test_spread.user_defined['what'] == 'what?'
    assert test_spread.user_defined['abc'] == 'xyz'

def test_closed_value(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option1.incur_fees = False
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)
    option2.incur_fees = False

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])

    # advance date and update options
    quote_date = datetime.datetime(2014, 12, 31, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    # close part of one option
    option1.close_trade(quantity=5)
    assert test_spread.closed_value == option1.trade_close_info.premium

    # close part of other option
    option2.close_trade(quantity=-5)
    assert test_spread.closed_value == option1.trade_close_info.premium + option2.trade_close_info.premium

    # advance date and update options
    quote_date = datetime.datetime(2015, 1, 2, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    # close all
    option1.close_trade(quantity=5)
    option2.close_trade(quantity=-5)

    assert test_spread.closed_value == option1.trade_close_info.premium + option2.trade_close_info.premium

def test_symbol_property(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])
    assert test_spread.symbol == 'AAPL'

def test_quote_datetime_property(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])
    assert test_spread.quote_datetime == quote_date

def test_get_profit_loss(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option1.incur_fees = False
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)
    option2.incur_fees = False

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])

    # advance date and update options
    quote_date2 = datetime.datetime(2014, 12, 31, 0, 0)
    option_chain = option_chain_data('daily', quote_date2)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    option1.close_trade(quantity=10)

    assert test_spread.get_profit_loss() == option1.trade_close_info.profit_loss + option2.get_unrealized_profit_loss()


    # advance date and update options
    quote_date = datetime.datetime(2015, 1, 2, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    option2.close_trade(quantity=-10)

    assert test_spread.get_profit_loss() == option1.trade_close_info.profit_loss + option2.trade_close_info.profit_loss



def test_get_unrealized_profit_loss(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option1.incur_fees = False
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)
    option2.incur_fees = False

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])

    # advance date and update options
    quote_date2 = datetime.datetime(2014, 12, 31, 0, 0)
    option_chain = option_chain_data('daily', quote_date2)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    assert test_spread.get_unrealized_profit_loss() == option1.get_unrealized_profit_loss() + option2.get_unrealized_profit_loss()

def test_get_trade_premium(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])
    assert False

def test_get_open_datetime(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])

    # advance date and update options
    quote_date2 = datetime.datetime(2014, 12, 31, 0, 0)
    option_chain = option_chain_data('daily', quote_date2)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    assert test_spread.get_open_datetime() == quote_date

def test_get_close_datetime(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])
    assert False

def test_get_fees(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])
    assert False