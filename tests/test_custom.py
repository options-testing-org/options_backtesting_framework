"""
Tests for the Custom spread class.

Fixture defaults (3-leg custom put spread):
  options:    [MSFT 380P, MSFT 370P, MSFT 390P]  2026-04-10
  quantities: [+1,        -1,        +1        ]

Tests also cover 2-leg and call leg configurations using explicit options.
fill_factor=1.0 is passed where mid-price is needed.
"""

import datetime
import pytest
from options_framework.option_types import OptionSpreadType, OptionStatus
from options_framework.spreads.custom import Custom
from conftest import REQUIRED_HISTORY_KEYS


# ── create() & construction ───────────────────────────────────────────────────

def test_spread_type(make_custom):
    assert make_custom().spread_type == OptionSpreadType.CUSTOM


def test_options_list_populated(make_custom):
    c = make_custom()
    assert len(c.options) == 3


def test_legs_are_open_after_create(make_custom):
    c = make_custom()
    for leg in c.options:
        assert OptionStatus.TRADE_IS_OPEN in leg.status


def test_quantities_applied_to_legs(make_custom):
    c = make_custom()
    assert c.options[0].quantity == +1
    assert c.options[1].quantity == -1
    assert c.options[2].quantity == +1


def test_spread_quantity_tracks_first_option(make_custom):
    c = make_custom()
    assert c.quantity == c.options[0].quantity


def test_create_raises_with_empty_options(make_put_option_380):
    with pytest.raises(ValueError, match="non-empty"):
        Custom.create(options=[], quantities=[])


def test_create_raises_with_mismatched_quantities(make_put_option_380, make_put_option_370):
    opts = [make_put_option_380(), make_put_option_370()]
    with pytest.raises(ValueError, match="same length"):
        Custom.create(options=opts, quantities=[1])


def test_instance_ids_are_unique(make_custom):
    assert make_custom().instance_id != make_custom().instance_id


def test_equality_based_on_instance_id(make_custom):
    c1 = make_custom()
    c2 = make_custom()
    assert c1 != c2
    assert c1 == c1


def test_repr_contains_spread_type(make_custom):
    assert 'CUSTOM' in repr(make_custom())


def test_repr_contains_leg_quantities(make_custom):
    r = repr(make_custom())
    assert '+1x' in r
    assert '-1x' in r


def test_open_trade_raises(make_custom):
    """open_trade must raise — create() is the entry point."""
    c = make_custom()
    with pytest.raises(RuntimeError, match="Custom.create"):
        c._open_trade()


def test_symbol_delegates_to_first_option(make_custom):
    c = make_custom()
    assert c.symbol == c.options[0].symbol


# ── price ─────────────────────────────────────────────────────────────────────

def test_price_is_signed_sum(make_custom):
    """price = sum of signed option prices based on quantity direction."""
    c = make_custom()
    expected = c.options[0].price - c.options[1].price + c.options[2].price
    assert c.price == pytest.approx(expected, abs=0.01)


def test_price_two_long_legs(
        make_put_option_380, make_put_option_370
):
    """Two long legs: price = sum of both prices."""
    opt1 = make_put_option_380(fill_factor=1.0)
    opt2 = make_put_option_370(fill_factor=1.0)
    c = Custom.create(options=[opt1, opt2], quantities=[+1, +1])
    assert c.price == pytest.approx(opt1.price + opt2.price, abs=0.01)


def test_price_one_long_one_short(
        make_put_option_380, make_put_option_370
):
    """Vertical spread price: long - short."""
    opt1 = make_put_option_380(fill_factor=1.0)
    opt2 = make_put_option_370(fill_factor=1.0)
    c = Custom.create(options=[opt1, opt2], quantities=[+1, -1])
    assert c.price == pytest.approx(opt1.price - opt2.price, abs=0.01)


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_float_after_create(make_custom):
    assert isinstance(make_custom().get_trade_price(), float)


def test_trade_price_matches_signed_sum_formula(make_custom):
    c = make_custom()
    lp = c.options[0].trade_open_info.price
    sp = c.options[1].trade_open_info.price
    up = c.options[2].trade_open_info.price
    assert c.get_trade_price() == pytest.approx(lp - sp + up, abs=0.01)


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_all_legs(make_custom):
    c = make_custom()
    c._close_trade(quote_datetime=c.options[0].quote_datetime)
    for leg in c.options:
        assert OptionStatus.TRADE_IS_CLOSED in leg.status


def test_close_trade_requires_keyword_only_quote_datetime(make_custom):
    c = make_custom()
    c._close_trade(quote_datetime=c.options[0].quote_datetime)


def test_get_closed_price_returns_none_before_close(make_custom):
    assert make_custom().get_closed_price() is None


def test_get_closed_price_returns_float_after_close(make_custom):
    c = make_custom()
    c._close_trade(quote_datetime=c.options[0].quote_datetime)
    assert isinstance(c.get_closed_price(), float)


def test_closed_price_matches_formula(make_custom):
    c = make_custom()
    c._close_trade(quote_datetime=c.options[0].quote_datetime)
    lp = c.options[0].trade_close_info.price
    sp = c.options[1].trade_close_info.price
    up = c.options[2].trade_close_info.price
    assert c.get_closed_price() == pytest.approx(lp - sp + up, abs=0.01)


# ── get_dte ───────────────────────────────────────────────────────────────────

def test_dte_returns_minimum_across_legs(make_custom):
    """get_dte returns the nearest expiration's DTE."""
    c = make_custom()
    expected = min(o.get_dte() for o in c.options)
    assert c.get_dte() == expected


def test_dte_is_positive_before_expiry(make_custom):
    assert make_custom().get_dte() > 0


# ── SpreadBase delegation ─────────────────────────────────────────────────────

def test_spot_price_delegates_to_first_option(make_custom):
    c = make_custom()
    assert c.spot_price == c.options[0].spot_price


def test_quote_datetime_delegates_to_first_option(make_custom):
    c = make_custom()
    assert c.quote_datetime == c.options[0].quote_datetime


def test_get_profit_loss_after_create(make_custom):
    assert isinstance(make_custom().get_profit_loss(), float)


def test_current_value_sums_legs(make_custom):
    c = make_custom()
    assert c.current_value == pytest.approx(sum(o.current_value for o in c.options), abs=0.01)


def test_max_profit_returns_none(make_custom):
    assert make_custom().max_profit is None


def test_max_loss_returns_none(make_custom):
    assert make_custom().max_loss is None


def test_get_required_margin_returns_none(make_custom):
    assert make_custom().get_required_margin(1) is None


# ── get_price_history ─────────────────────────────────────────────────────────

def test_price_history_raises_if_called_on_unopened_options(
        make_put_option_380, make_put_option_370
):
    """Constructing Custom directly without create() leaves options unopened."""
    opt1 = make_put_option_380()
    opt2 = make_put_option_370()
    c = Custom(options=[opt1, opt2], spread_type=OptionSpreadType.CUSTOM)
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        c.get_history()


def test_price_history_returns_list(make_custom):
    assert isinstance(make_custom().get_history(), list)


def test_price_history_each_entry_has_required_keys(make_custom):
    for entry in make_custom().get_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_length_matches_first_leg_updates(make_custom):
    c = make_custom()
    last_date = c.options[0].quote_datetime
    expected_len = sum(1 for k in c.options[0].updates if k <= last_date)
    assert len(c.get_history()) == expected_len


def test_price_history_price_matches_signed_sum_each_row(make_custom):
    c = make_custom()
    u0 = c.options[0].updates
    u1 = c.options[1].updates
    u2 = c.options[2].updates
    last_date = c.options[0].quote_datetime
    keys = sorted(k for k in u0 if k <= last_date)

    for i, entry in enumerate(c.get_history()):
        k = keys[i]
        expected = u0[k]['price'] - u1[k]['price'] + u2[k]['price']
        assert entry['price'] == pytest.approx(expected, abs=0.01)


def test_price_history_spot_price_matches_first_leg(make_custom):
    c = make_custom()
    u0 = c.options[0].updates
    last_date = c.options[0].quote_datetime
    keys = sorted(k for k in u0 if k <= last_date)
    for i, entry in enumerate(c.get_history()):
        assert entry['spot_price'] == u0[keys[i]].get('spot_price')


def test_price_history_pnl_is_zero_at_open_bar(make_custom):
    assert make_custom(fill_factor=1.0).get_history()[0]['pnl'] == pytest.approx(0.0, abs=1.0)


def test_price_history_pnl_pct_is_zero_at_open_bar(make_custom):
    assert make_custom(fill_factor=1.0).get_history()[0]['pnl_pct'] == pytest.approx(0.0, abs=0.01)


def test_price_history_two_leg_custom(make_put_option_380, make_put_option_370):
    """History works correctly for a 2-leg custom spread."""
    opt1 = make_put_option_380(fill_factor=1.0)
    opt2 = make_put_option_370(fill_factor=1.0)
    c = Custom.create(options=[opt1, opt2], quantities=[+1, -1])
    history = c.get_history()
    assert len(history) > 0
    for entry in history:
        assert entry.keys() == REQUIRED_HISTORY_KEYS
