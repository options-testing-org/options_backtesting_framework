import copy
import datetime
from dataclasses import dataclass
from typing import Self

import pytest

from options_framework.option import Option
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase

@dataclass(repr=False, slots=True)
class TestOption(SpreadBase):

    @classmethod
    def create(cls, options: list[Option], *args, **kwargs) -> Self:
        test_option = TestOption(options, OptionSpreadType.CUSTOM)
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

    def get_dte(self) -> int | None:
        pass


def test_create_option_base_fails(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    with pytest.raises(NotImplementedError):
        SpreadBase.create(option_chain=option_chain)

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
    assert test_spread.spread_type == OptionSpreadType.CUSTOM
    assert test_spread.quantity == 0 # default quantity
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
    call_price = option_data['price']
    option1 = Option(**option_data)
    option1.incur_fees = False
    option_data = copy.deepcopy(option_2)
    put_price = option_data['price']
    option2 = Option(**option_data)
    option2.incur_fees = False

    test_spread = TestOption.create([option1, option2])

    # premium should be none if no position was ever opened
    assert test_spread.get_trade_premium() is None

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    premium = (call_price * 10 * 100) + (put_price * -10 * 100)
    assert test_spread.get_trade_premium() == premium

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

    assert test_spread.get_trade_premium() == premium

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

    # Nothing has been closed yet
    assert test_spread.get_close_datetime() is None

    option1.close_trade(quantity=5)

    # partial close - both options still have open quantity
    assert test_spread.get_close_datetime() is None

    # close all of one option
    option1.close_trade(quantity=5)
    assert test_spread.get_close_datetime() == quote_date

    # advance date and update options
    quote_date2 = datetime.datetime(2014, 12, 31, 0, 0)
    option_chain = option_chain_data('daily', quote_date2)

    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option2.next(option_2)

    # close other option
    option2.close_trade(quantity=-10)

    assert test_spread.get_close_datetime() == quote_date2


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
    option1.incur_fees = True
    option1.fee_per_contract = 0.55
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)
    option2.incur_fees = True
    option2.fee_per_contract = 0.55

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    test_spread = TestOption.create([option1, option2])

    assert test_spread.get_fees() == 0.55 * 20

def test_get_profit_loss_percent(option_chain_data):
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

    # no updates to options since open
    assert test_spread.get_profit_loss_percent() == 0.0

    # advance date and update options
    quote_date2 = datetime.datetime(2015, 1, 5, 0, 0)
    option_chain = option_chain_data('daily', quote_date2)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    returns = round(option1.get_profit_loss_percent() + option2.get_profit_loss_percent(), 4)

    assert test_spread.get_profit_loss_percent() == returns

    # closing one options should not change returns
    option1.close_trade(quantity=10)

    assert test_spread.get_profit_loss_percent() == returns


def test_get_unrealized_profit_loss_percent(option_chain_data):
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

    # no price changes
    assert test_spread.get_unrealized_profit_loss_percent() == 0.0

    # advance date and update options
    quote_date2 = datetime.datetime(2015, 1, 5, 0, 0)
    option_chain = option_chain_data('daily', quote_date2)

    option_1 = next(x for x in option_chain.options if
                    x['strike'] == 110.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_2 = next(x for x in option_chain.options if
                    x['strike'] == 120.0 and x['expiration'] == expiration and x['option_type'] == 'call')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    # all returns are unrealized
    returns = round(option1.get_profit_loss_percent() + option2.get_profit_loss_percent(), 4)

    assert test_spread.get_unrealized_profit_loss_percent() == returns

    # close one option
    option1.close_trade(quantity=10)

    returns = option2.get_profit_loss_percent()
    assert test_spread.get_unrealized_profit_loss_percent() == returns


def test_get_days_in_trade(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)

    option_1 = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150117C00010000')
    option_2 = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150117P00010000')

    option_data = copy.deepcopy(option_1)
    option1 = Option(**option_data)
    option_data = copy.deepcopy(option_2)
    option2 = Option(**option_data)

    test_spread = TestOption.create([option1, option2])

    # No options have been opened, so this cannot be calculated
    assert test_spread.get_days_in_trade() is None

    option1.open_trade(quantity=10)
    option2.open_trade(quantity=-10)

    # open trade, but date hasn't advanced
    assert test_spread.get_days_in_trade() is 0

    # advance date and update options
    quote_date = datetime.datetime(2014, 12, 31, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    option_1 = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150117C00010000')
    option_2 = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150117P00010000')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    # open trade, advance one day
    assert test_spread.get_days_in_trade() == 1

    # advance date and update options
    quote_date = datetime.datetime(2015, 1, 2, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    option_1 = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150117C00010000')
    option_2 = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150117P00010000')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    # days in trade increases
    assert test_spread.get_days_in_trade() == 3

    # close trade
    option1.close_trade(quantity=10)
    option2.close_trade(quantity=-10)

    # days in trade should still be the same when closed
    assert test_spread.get_days_in_trade() == 3

    # advance next date and update options
    quote_date = datetime.datetime(2015, 1, 6, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    option_1 = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150117C00010000')
    option_2 = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150117P00010000')
    option_data = copy.deepcopy(option_1)
    option1.next(option_data)
    option_data = copy.deepcopy(option_2)
    option2.next(option_data)

    # closed trade never advances, so days in trade never changes
    assert test_spread.get_days_in_trade() == 3

