import datetime

from options_framework.option_types import OptionType
from options_framework.spreads.butterfly import Butterfly
def test_open_long_butterfly_position(option_chain):
    chain, _ = option_chain
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1990
    wing_width = 20
    position = Butterfly.get_balanced_butterfly(options=chain.option_chain, expiration=expiration, option_type=OptionType.PUT,
                                                center_strike=center_strike, wing_width=wing_width)

    assert position.quantity == 1
    assert position.center_option.strike == center_strike
    assert position.center_option.quantity == -2
    assert position.lower_option.strike <= 1970
    assert position.lower_option.quantity == 1
    assert position.upper_option.strike >= 2010
    assert position.upper_option.quantity == 1

def test_open_short_butterfly_position(option_chain):
    chain, _ = option_chain
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1990
    wing_width = 20
    position = Butterfly.get_balanced_butterfly(options=chain.option_chain, expiration=expiration, option_type=OptionType.PUT,
                                                center_strike=center_strike, wing_width=wing_width, quantity=-1)

    assert position.quantity == -1
    assert position.center_option.strike == center_strike
    assert position.center_option.quantity == 2
    assert position.lower_option.strike <= 1970
    assert position.lower_option.quantity == -1
    assert position.upper_option.strike >= 2010
    assert position.upper_option.quantity == -1

def test_long_butterfly_value(option_chain):
    chain, _ = option_chain
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1990
    wing_width = 20
    position = Butterfly.get_balanced_butterfly(options=chain.option_chain, expiration=expiration,
                                                option_type=OptionType.PUT,
                                                center_strike=center_strike, wing_width=wing_width)
    assert position.current_value == 155.0


def test_short_butterfly_value(option_chain):
    chain, _ = option_chain
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1990
    wing_width = 20
    position = Butterfly.get_balanced_butterfly(options=chain.option_chain, expiration=expiration,
                                                option_type=OptionType.PUT,
                                                center_strike=center_strike, wing_width=wing_width, quantity=-1)
    assert position.current_value == -155.0

def test_long_position_max_profit_max_loss_max_profit(option_chain):
    chain, _ = option_chain
    expiration = datetime.datetime(2016, 3, 2)
    center_strike = 1990
    wing_width = 20
    quantity = 1
    position = Butterfly.get_balanced_butterfly(options=chain.option_chain, expiration=expiration,
                                                option_type=OptionType.PUT,
                                                center_strike=center_strike, wing_width=wing_width,
                                                quantity=quantity)
    assert position.max_profit == 1845.0
    assert position.max_loss == 155.0
    assert position.risk_to_reward == 11.9
