import datetime

from options_framework.option_types import OptionType, OptionPositionType
from options_framework.spreads.butterfly import Butterfly
def test_open_long_butterfly_position(spx_option_chain_puts):
    chain, _ = spx_option_chain_puts
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1990
    wing_width = 20
    quantity = 1

    position = Butterfly.get_balanced_butterfly(option_chain=chain.option_chain, expiration=expiration, option_type=OptionType.PUT,
                                                center_strike=center_strike, wing_width=wing_width, quantity=quantity)

    assert position.center_option.strike == center_strike
    assert position.lower_option.strike <= 1970
    assert position.upper_option.strike >= 2010
    assert position.option_position_type == OptionPositionType.LONG

def test_open_short_butterfly_position(spx_option_chain_puts):
    chain, _ = spx_option_chain_puts
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1990
    wing_width = 20
    quantity = -1
    position = Butterfly.get_balanced_butterfly(option_chain=chain.option_chain, expiration=expiration, option_type=OptionType.PUT,
                                                center_strike=center_strike, wing_width=wing_width, quantity=quantity)

    assert position.center_option.strike == center_strike
    assert position.lower_option.strike <= 1970
    assert position.upper_option.strike >= 2010
    assert position.option_position_type == OptionPositionType.SHORT

def test_long_butterfly_value_default_quantity(spx_option_chain_puts):
    chain, _ = spx_option_chain_puts
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1990
    wing_width = 20

    position = Butterfly.get_balanced_butterfly(option_chain=chain.option_chain, expiration=expiration,
                                                option_type=OptionType.PUT,
                                                center_strike=center_strike, wing_width=wing_width)
    position.open_trade()

    assert position.current_value == 155.0
    assert position.quantity == 1


def test_short_butterfly_value(spx_option_chain_puts):
    chain, _ = spx_option_chain_puts
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1990
    wing_width = 20
    position = Butterfly.get_balanced_butterfly(option_chain=chain.option_chain, expiration=expiration,
                                                option_type=OptionType.PUT,
                                                center_strike=center_strike, wing_width=wing_width, quantity = -1)
    position.open_trade(quantity=-10)
    assert position.current_value == -1550.0

def test_long_position_max_profit_max_loss_max_profit(spx_option_chain_calls):
    chain, _ = spx_option_chain_calls
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1950
    wing_width = 20
    quantity = 1
    position = Butterfly.get_balanced_butterfly(option_chain=chain.option_chain, expiration=expiration,
                                                option_type=OptionType.CALL,
                                                center_strike=center_strike, wing_width=wing_width)
    position.open_trade(quantity=quantity)

    assert position.max_profit == 18450.0
    assert position.max_loss == 1550.0
    assert position.risk_to_reward == 11.9

def test_long_position_with_unbalanced_wings(spx_option_chain_calls):
    chain, _ = spx_option_chain_calls
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1920
    lower_wing = 20
    upper_wing = 10
    quantity = 2


    position = Butterfly.get_unbalanced_butterfly(option_chain=chain.option_chain, expiration=expiration,
                                                  option_type=OptionType.CALL, center_strike=center_strike,
                                                  lower_wing_width=lower_wing, upper_wing_width=upper_wing,
                                                  quantity=5)

    position.open_trade(quantity=quantity)

    assert position.lower_option.quantity == 4
    assert position.center_option.quantity == -6
    assert position.upper_option.quantity == 2

    max_profit = position.max_profit


