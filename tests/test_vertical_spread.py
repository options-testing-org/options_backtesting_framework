import pytest

from options_framework.option_types import OptionCombinationType, OptionTradeType
from options_framework.spreads.vertical import Vertical
from options_test_helper import *

@pytest.mark.xfail(raises=NameError)
def test_has_correct_option_combination_type():
    long_option = get_4310_call_option()
    long_option.open_trade(10)
    short_option = get_4320_call_option()
    short_option.open_trade(-10)

    call_debit_spread = Vertical(long_option, short_option)

    assert call_debit_spread.option_combination_type == OptionCombinationType.VERTICAL

@pytest.mark.xfail(raises=NameError)
def test_call_debit_has_debit_option_trade_type():
    long_option = get_4310_call_option()
    long_option.open_trade(10)
    short_option = get_4320_call_option()
    short_option.open_trade(-10)

    call_debit_spread = Vertical(long_option, short_option)

    assert call_debit_spread.option_trade_type == OptionTradeType.DEBIT

@pytest.mark.xfail(raises=NameError)
def test_call_credit_has_credit_option_trade_type():
    long_option = get_4320_call_option()
    long_option.open_trade(10)
    short_option = get_4310_call_option()
    short_option.open_trade(-10)

    call_credit_spread = Vertical(long_option, short_option)

    assert call_credit_spread.option_trade_type == OptionTradeType.CREDIT

@pytest.mark.xfail(raises=NameError)
def test_put_debit_has_debit_option_trade_type():
    long_option = get_4220_put_option()
    long_option.open_trade(10)
    short_option = get_4210_put_option()
    short_option.open_trade(-10)

    put_debit_spread = Vertical(long_option, short_option)

    assert put_debit_spread.option_trade_type == OptionTradeType.DEBIT

@pytest.mark.xfail(raises=NameError)
def test_put_credit_has_credit_option_trade_type():
    long_option = get_4210_put_option()
    long_option.open_trade(10)
    short_option = get_4220_put_option()
    short_option.open_trade(-10)

    put_credit_spread = Vertical(long_option, short_option)

    assert put_credit_spread.option_trade_type == OptionTradeType.CREDIT

@pytest.mark.xfail(raises=NameError)
def test_raises_error_if_options_not_of_same_option_type():
    long_option = get_4310_call_option()
    long_option.open_trade(10)
    short_option = get_4100_put_option()
    short_option.open_trade(-10)

    with pytest.raises(ValueError,
                       match="A vertical spread must contain options of the same type. Both must be calls or puts."):
        Vertical(long_option, short_option)

@pytest.mark.xfail(raises=NameError)
def test_raises_error_if_expirations_are_not_the_same():
    long_option = get_long_4100_put_option()

    test_expiration_2 = (
        datetime.datetime.strptime("2021-07-18 09:45:00.000000", "%Y-%m-%d %H:%M:%S.%f"))
    _id = 2
    strike = 4220
    spot_price, bid, ask, price = (4308, 14.8, 15.2, 15.00)
    short_option = Option(_id, ticker, strike, test_expiration_2, OptionType.PUT,
                    quote_date=test_quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    short_option.open_trade(-1)

    with pytest.raises(ValueError, match="All options in the spread must have the same expiration"):
        Vertical(long_option, short_option)

@pytest.mark.xfail(raises=NameError)
def test_quantity_of_both_options_are_the_same():
    long_option = get_4320_call_option()
    long_option.open_trade(10)
    short_option = get_4310_call_option()
    short_option.open_trade(-9)
    with pytest.raises(ValueError,
                       match="Both options must have the same absolute quantity for both long and short legs"):
        Vertical(long_option, short_option)

@pytest.mark.xfail(raises=NameError)
def test_raises_exception_when_long_option_parameter_is_not_long():
    long_option = get_4320_call_option()
    long_option.open_trade(-10) # open short position
    short_option = get_4310_call_option()
    short_option.open_trade(-10)

    with pytest.raises(ValueError, match="The long_option parameter must be a long option."):
        Vertical(long_option, short_option)

@pytest.mark.xfail(raises=NameError)
def test_raises_exception_when_short_option_parameter_is_not_short():
    long_option = get_4320_call_option()
    long_option.open_trade(10)
    short_option = get_4310_call_option()
    short_option.open_trade(10) # open long position

    with pytest.raises(ValueError, match="The short_option parameter must be a short option."):
        Vertical(long_option, short_option)

@pytest.mark.xfail(raises=NameError)
def test_width_is_difference_between_short_and_long_strikes():
    long_option = get_4210_put_option()
    long_option.open_trade(15)
    short_option = get_4220_put_option()
    short_option.open_trade(-15)

    vertical_spread = Vertical(long_option, short_option)

    assert vertical_spread.spread_width() == 10

@pytest.mark.xfail(raises=NameError)
def test_call_debit_total_premium():
    long_option = get_4310_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4320_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    call_debit_spread = Vertical(long_option, short_option)

    assert call_debit_spread.total_premium() == 5_550

@pytest.mark.xfail(raises=NameError)
def test_call_credit_total_premium():
    long_option = get_4320_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4310_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    call_credit_spread = Vertical(long_option, short_option)

    expected_premium = -5_550

    assert call_credit_spread.total_premium() == expected_premium

@pytest.mark.xfail(raises=NameError)
def test_put_debit_total_premium():
    long_option = get_4220_put_option()  # trade price = 15.0
    long_option.open_trade(10)
    short_option = get_4210_put_option()  # trade price = 13.95
    short_option.open_trade(-10)

    put_debit_spread = Vertical(long_option, short_option)
    expected_premium = 1_050

    assert put_debit_spread.total_premium() == expected_premium

@pytest.mark.xfail(raises=NameError)
def test_put_credit_total_premium():
    long_option = get_4210_put_option()  # trade price = 15.0
    long_option.open_trade(10)
    short_option = get_4220_put_option()  # trade price = 13.95
    short_option.open_trade(-10)

    put_credit_spread = Vertical(long_option, short_option)

    expected_premium = -1_050

    assert put_credit_spread.total_premium() == expected_premium

@pytest.mark.xfail(raises=NameError)
def test_call_debit_max_profit():
    # Max profit = the spread between the strike prices - net premium paid.
    long_option = get_4310_call_option()
    long_option.open_trade(10) # trade price 30.85
    short_option = get_4320_call_option()
    short_option.open_trade(-10) # trade price 25.30

    call_debit_spread = Vertical(long_option, short_option)

    expected_max_profit = 4_450.0

    assert call_debit_spread.max_profit() == expected_max_profit

@pytest.mark.xfail(raises=NameError)
def test_call_credit_max_profit():
    # Max profit = net premium received.
    long_option = get_4320_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4310_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    call_credit_spread = Vertical(long_option, short_option)

    expected_max_profit = 5_550

    assert call_credit_spread.max_profit() == expected_max_profit

@pytest.mark.xfail(raises=NameError)
def test_put_debit_max_profit():
    # Max profit = the spread between the strike prices - net premium paid
    long_option = get_4220_put_option() # trade price = 15.0
    long_option.open_trade(10)
    short_option = get_4210_put_option() # trade price = 13.95
    short_option.open_trade(-10)

    put_debit_spread = Vertical(long_option, short_option)

    max_profit = 8_950

    assert put_debit_spread.max_profit() == max_profit

@pytest.mark.xfail(raises=NameError)
def test_put_credit_max_profit():
    # Max profit = net premium received.
    long_option = get_4210_put_option()  # trade price = 15.0
    long_option.open_trade(10)
    short_option = get_4220_put_option()  # trade price = 13.95
    short_option.open_trade(-10)

    put_credit_spread = Vertical(long_option, short_option)

    expected_max_profit = 1_050

    assert put_credit_spread.max_profit() == expected_max_profit

@pytest.mark.xfail(raises=NameError)
def test_call_debit_max_loss():
    # Max loss = net premium paid.
    long_option = get_4310_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4320_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    call_debit_spread = Vertical(long_option, short_option)

    expected_max_loss = 5_550

    assert call_debit_spread.max_loss() == expected_max_loss

@pytest.mark.xfail(raises=NameError)
def test_call_credit_max_loss():
    # Max loss = the spread between the strike prices - net premium received.
    long_option = get_4320_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4310_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    call_credit_spread = Vertical(long_option, short_option)

    expected_max_loss = 4_450

    assert call_credit_spread.max_loss() == expected_max_loss

@pytest.mark.xfail(raises=NameError)
def test_put_debit_max_loss():
    # Max loss = net premium paid.
    long_option = get_4220_put_option()  # trade price = 15.0
    long_option.open_trade(10)
    short_option = get_4210_put_option()  # trade price = 13.95
    short_option.open_trade(-10)

    put_debit_spread = Vertical(long_option, short_option)

    max_loss = 1_050

    assert put_debit_spread.max_loss() == max_loss

@pytest.mark.xfail(raises=NameError)
def test_put_credit_max_loss():
    # Max loss = the spread between the strike prices - net premium received.
    long_option = get_4210_put_option()  # trade price = 15.0
    long_option.open_trade(10)
    short_option = get_4220_put_option()  # trade price = 13.95
    short_option.open_trade(-10)

    put_credit_spread = Vertical(long_option, short_option)

    max_loss = 8_950

    assert put_credit_spread.max_loss() == max_loss

@pytest.mark.xfail(raises=NameError)
def test_call_debit_breakeven_price():
    # Breakeven point = long call's strike price + net premium paid.
    long_option = get_4310_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4320_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    call_debit_spread = Vertical(long_option, short_option)

    expected_breakeven = 4_315.55

    assert call_debit_spread.breakeven_price() == expected_breakeven

@pytest.mark.xfail(raises=NameError)
def test_call_credit_breakeven_price():
    # Breakeven point = short call's strike price + net premium received.
    long_option = get_4320_call_option()
    long_option.open_trade(10)  # trade price 30.85
    short_option = get_4310_call_option()
    short_option.open_trade(-10)  # trade price 25.30

    call_credit_spread = Vertical(long_option, short_option)

    expected_breakeven = 4_315.55

    assert call_credit_spread.breakeven_price() == expected_breakeven

@pytest.mark.xfail(raises=NameError)
def test_put_debit_breakeven_price():
    # Breakeven point = long put's strike price - net premium paid
    long_option = get_4220_put_option()  # trade price = 15.0
    long_option.open_trade(10)
    short_option = get_4210_put_option()  # trade price = 13.95
    short_option.open_trade(-10)

    put_debit_spread = Vertical(long_option, short_option)

    breakeven = 4218.95

    assert put_debit_spread.breakeven_price() == breakeven

@pytest.mark.xfail(raises=NameError)
def test_put_credit_breakeven_price():
    # Breakeven point = short put's strike price - net premium received.
    long_option = get_4210_put_option()  # trade price = 15.0
    long_option.open_trade(10)
    short_option = get_4220_put_option()  # trade price = 13.95
    short_option.open_trade(-10)
    put_credit_spread = Vertical(long_option, short_option)
    expected_breakeven = 4_218.95

    assert put_credit_spread.breakeven_price() == expected_breakeven

