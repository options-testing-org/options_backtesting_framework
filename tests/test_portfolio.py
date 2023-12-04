import pytest

from options_framework.option_portfolio import OptionPortfolio
from options_framework.spreads.single import Single
from options_framework.config import settings

@pytest.fixture
def incur_fees_true():
    original_setting = settings.INCUR_FEES
    settings.INCUR_FEES = True
    yield
    settings.INCUR_FEES = original_setting

@pytest.fixture
def incur_fees_false():
    original_setting = settings.INCUR_FEES
    settings.INCUR_FEES = False
    yield
    settings.INCUR_FEES = original_setting

@pytest.fixture
def test_position_1(get_test_call_option):
    return Single([get_test_call_option])

@pytest.fixture
def test_position_2(get_test_put_option):
    return Single([get_test_put_option])

def test_new_portfolio_cash_balance():
    pf = OptionPortfolio(100_000.0)

    assert pf.cash == 100_000.0
    assert pf.portfolio_value == 100_000.0

def test_open_long_option_position(incur_fees_false, test_position_1):
    pf = OptionPortfolio(100_000.0)
    pf.open_position(option_position=test_position_1, quantity=1)

    assert pf.cash == 99_850.0
    assert pf.portfolio_value == 100_000.0

def test_get_portfolio_value_with_open_positions(incur_fees_false, test_position_1, test_position_2):
    pf = OptionPortfolio(100_000.0)
    pf.open_position(option_position=test_position_1, quantity=1)
    pf.open_position(option_position=test_position_2, quantity=1)

    assert pf.cash == 99_700.0
    assert pf.portfolio_value == 100_000.0

def test_portfolio_updates_when_option_values_are_updated(incur_fees_false, test_position_1, test_position_2,
                                                          get_test_call_option_update_values_1,
                                                          get_test_put_option_update_values_1):
    pf = OptionPortfolio(100_000.0)
    pf.open_position(option_position=test_position_1, quantity=1)
    pf.open_position(option_position=test_position_2, quantity=1)

    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_position_1.option.update(quote_datetime=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    assert pf.portfolio_value == 100_850.0

    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_1
    test_position_2.option.update(quote_datetime=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    assert pf.portfolio_value == 101_700.0

    assert pf.cash == 99_700.0

def test_portfolio_values_when_position_is_closed(incur_fees_false, test_position_1,
                                                  get_test_call_option_update_values_1):
    pf = OptionPortfolio(100_000.0)

    # spend $300.00 to open options worth $300
    pf.open_position(option_position=test_position_1, quantity=2)
    assert pf.cash == 99_700.0
    assert pf.portfolio_value == 100_000.0

    # options now worth $2,000.00. Cash remains unchanged
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_position_1.option.update(quote_datetime=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    assert pf.portfolio_value == 101_700.0
    assert pf.cash == 99_700.0

    # close options. No open options, so worth $0.00. Cash added $2000.00 for selling options
    pf.close_position(test_position_1, quantity=2)
    assert pf.cash == 101_700.0
    assert pf.portfolio_value == 101_700.0


def test_portfolio_values_with_multiple_positions(incur_fees_false, test_position_1, test_position_2,
                                                  get_test_call_option_update_values_1,
                                                  get_test_put_option_update_values_1):
    # open two positions
    pf = OptionPortfolio(100_000.0)
    pf.open_position(option_position=test_position_1, quantity=1)
    pf.open_position(option_position=test_position_2, quantity=1)

    assert pf.cash == 99_700.0
    assert pf.portfolio_value == 100_000.0

    # update both positions
    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_position_1.option.update(quote_datetime=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    assert pf.portfolio_value == 100_850.0
    assert pf.cash == 99_700.0

    quote_date, spot_price, bid, ask, price = get_test_put_option_update_values_1
    test_position_2.option.update(quote_datetime=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)
    assert pf.portfolio_value == 101_700.0
    assert pf.cash == 99_700.0

    # close one position
    pf.close_position(test_position_1, quantity=1)
    assert pf.cash == 100_700.0
    assert pf.portfolio_value == 101_700.0 # portfolio value should not change

def test_expired_position_closes_position(incur_fees_false, test_position_1, get_test_call_option_update_values_1,
                                          at_expiration_quote_date):
    # open position
    pf = OptionPortfolio(100_000.0)
    pf.open_position(option_position=test_position_1, quantity=1)

    # position expires
    quote_date = at_expiration_quote_date
    _, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_position_1.option.update(quote_datetime=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    assert len(pf.positions) == 0
    assert len(pf.closed_positions) == 1

def test_closed_positions_do_not_update_portfolio_value_when_updated(incur_fees_false, test_position_1,
                                                                     get_test_call_option_update_values_1,
                                                                     get_test_call_option_update_values_2):
    pf = OptionPortfolio(100_000.0)
    pf.open_position(option_position=test_position_1, quantity=2)

    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_1
    test_position_1.option.update(quote_datetime=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    pf.close_position(test_position_1, quantity=2)
    assert pf.cash == 101_700.0
    assert pf.portfolio_value == 101_700.0

    quote_date, spot_price, bid, ask, price = get_test_call_option_update_values_2
    test_position_1.option.update(quote_datetime=quote_date, spot_price=spot_price, bid=bid, ask=ask, price=price)

    # portfolio is no longer updated when option value changes
    assert pf.portfolio_value == 101_700.0


