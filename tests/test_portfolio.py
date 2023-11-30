import pytest

from options_framework.option_portfolio import OptionPortfolio
from options_framework.spreads.single import Single
from options_framework.config import settings

settings.incur_fees = False

@pytest.fixture
def test_option_1(get_test_call_option):
    return Single([get_test_call_option])

@pytest.fixture
def test_option_2(get_test_put_option):
    return Single([get_test_put_option])

def test_new_portfolio_cash_balance():
    pf = OptionPortfolio(100_000)

    assert pf.cash == 100_000
    assert pf.portfolio_value == 100_000

def test_open_long_option_position(test_option_1):
    pf = OptionPortfolio(100_000.0)
    pf.open_position(option_position=test_option_1, quantity=1)

    assert pf.cash == 99_850
    assert pf.portfolio_value == 100_000

def test_get_portfolio_value_with_open_positions(test_option_1, test_option_2):
    pf = OptionPortfolio(100_000.0)
    pf.open_position(option_position=test_option_1, quantity=1)
    pf.open_position(option_position=test_option_2, quantity=1)

    assert pf.cash == 99_700.0
    assert pf.portfolio_value == 100_000
