from options_framework.spreads.option_combo import OptionCombination
from options_test_helper import *

def test_kwargs_are_set_as_attributes():
    tx_id = 1
    user_defined='my value'

    long_option = get_long_4100_put_option()

    combo = OptionCombination([long_option], transaction_id=tx_id, user_defined=user_defined)
    assert combo.transaction_id == tx_id
    assert combo.user_defined == user_defined

def test_premium_for_debit_type_spread():
    long_option = get_4310_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4320_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    options_debit_spread = OptionCombination([long_option, short_option])

    expected_premium = 5.55
    actual_premium = options_debit_spread.premium()

    assert actual_premium == expected_premium

def test_premium_for_credit_type_spread():
    long_option = get_4320_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4310_call_option()
    short_option.open_trade(-10)  # trade price 25.30
    options_credit_spread = OptionCombination([long_option, short_option])

    expected_premium = -5.55
    actual_premium = options_credit_spread.premium()

    assert actual_premium == expected_premium


def test_trade_cost_is_sum_of_long_and_short_option_trade_cost():
    long_option = get_4310_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4320_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    options_spread = OptionCombination([long_option, short_option])

    expected_trade_cost = 5_550

    assert options_spread.trade_cost() == expected_trade_cost

def test_trade_current_gain_loss():
    long_option = get_4310_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4320_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    options_spread = OptionCombination([long_option, short_option])

    expected_value = 0 # There is no unrealized gain or loss when first opened

    assert options_spread.current_gain_loss() == expected_value

    update_4310_call_option(long_option)  # 41.70
    update_4320_call_option(short_option)   # 34.70

    expected_value = 1_450

    assert options_spread.current_gain_loss() == expected_value

def test_profit_loss_percent():
    long_option = get_4310_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4320_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    options_spread = OptionCombination([long_option, short_option])

    expected_value = 0 # There is no unrealized gain or loss when first opened

    assert options_spread.profit_loss_percent() == expected_value

    update_4310_call_option(long_option)  # 41.70 - 2.82%
    update_4320_call_option(short_option)   # 34.70

    expected_value = 0.2613
    actual_value = options_spread.profit_loss_percent()
    assert actual_value == expected_value
    pass

