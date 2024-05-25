import datetime

import pytest

from options_framework.option_types import OptionType, OptionPositionType, OptionCombinationType

from options_framework.spreads.iron_condor import IronCondor


def test_get_long_iron_condor_by_delta(spx_option_chain):
    expiration = datetime.date(2016, 3, 2)
    option_chain, _ = spx_option_chain

    long_delta = 0.16
    short_delta = 0.06

    long_condor = IronCondor.get_iron_condor_by_delta(option_chain=option_chain, expiration=expiration,
                                                       long_delta=long_delta, short_delta=short_delta)

    assert long_condor.option_combination_type == OptionCombinationType.IRON_CONDOR
    assert long_condor.option_position_type == OptionPositionType.LONG
    assert long_condor.long_call_option.delta <= long_delta
    assert long_condor.short_call_option.delta <= short_delta
    assert long_condor.long_put_option.delta >= -long_delta
    assert long_condor.short_put_option.delta >= -short_delta


def test_get_long_iron_condor_by_strike(spx_option_chain):
    expiration = datetime.date(2016, 3, 2)
    option_chain, _ = spx_option_chain

    long_call_strike = 1960.0
    short_call_strike = 1970.0
    long_put_strke = 1930.0
    short_put_strike = 1920.0

    long_condor = IronCondor.get_iron_condor_by_strike(option_chain=option_chain, expiration=expiration,
                                                       long_call_strike=long_call_strike,
                                                       short_call_strike=short_call_strike,
                                                       long_put_strike=long_put_strke,
                                                       short_put_strike=short_put_strike)

    assert long_condor.option_combination_type == OptionCombinationType.IRON_CONDOR
    assert long_condor.option_position_type == OptionPositionType.LONG
    assert long_condor.long_call_option.strike == long_call_strike
    assert long_condor.short_call_option.strike == short_call_strike
    assert long_condor.long_put_option.strike == long_put_strke
    assert long_condor.short_put_option.strike == short_put_strike

def test_get_iron_condor_by_strike_and_width(spx_option_chain):
    expiration = datetime.date(2016, 3, 2)
    option_chain, _ = spx_option_chain

    call_strike = 1960
    put_strike = 1930
    width = 5
    long_call_price = 2.65
    short_call_price = 4.1
    call_price = -1.45
    call_max_loss = 5 - 1.45 # 3.55
    long_put_price = 2.75
    short_put_price = 3.7
    put_price = -0.95
    put_max_loss = 5 - 0.95 # 4.05

    price = (long_call_price - short_call_price) + (long_put_price - short_put_price) # -2.4

    lc_option = [o for o in option_chain.option_chain if o.expiration == expiration and o.strike == call_strike + 5
                and o.option_type == OptionType.CALL][0]
    sc_option = [o for o in option_chain.option_chain if o.expiration == expiration and o.strike == call_strike
                and o.option_type == OptionType.CALL][0]
    lp_option = [o for o in option_chain.option_chain if o.expiration == expiration and o.strike == put_strike - 5
                and o.option_type == OptionType.PUT][0]
    sp_option = [o for o in option_chain.option_chain if o.expiration == expiration and o.strike == put_strike
                and o.option_type == OptionType.PUT][0]

    iron_condor = IronCondor.get_iron_condor_by_strike_and_width(option_chain=option_chain, expiration=expiration,
                                                                 option_position_type=OptionPositionType.SHORT,
                                                                 inner_call_strike=call_strike,
                                                                 inner_put_strike=put_strike,
                                                                 spread_width=width)

    assert iron_condor.option_combination_type == OptionCombinationType.IRON_CONDOR
    assert iron_condor.option_position_type == OptionPositionType.SHORT
    assert iron_condor.expiration == expiration
    assert iron_condor.long_call_option == lc_option
    assert iron_condor.short_call_option == sc_option
    assert iron_condor.long_put_option == lp_option
    assert iron_condor.short_put_option == sp_option
    assert iron_condor.price == price
    assert iron_condor.get_trade_price() == price  # option is not traded yet
    assert iron_condor.max_loss == 405.0
    assert iron_condor.max_profit == 240.0

def test_get_open_iron_condor_with_kwargs(spx_option_chain):
    expiration = datetime.date(2016, 3, 2)
    option_chain, _ = spx_option_chain

    long_delta = 0.06
    short_delta = 0.16
    user_value = 'what'

    long_condor = IronCondor.get_iron_condor_by_delta(option_chain=option_chain, expiration=expiration,
                                                      long_delta=long_delta, short_delta=short_delta)

    long_condor.open_trade(quantity=2, user_value='what', something='important')

    assert long_condor.user_defined['user_value'] == 'what'
    assert long_condor.user_defined['something'] == 'important'
