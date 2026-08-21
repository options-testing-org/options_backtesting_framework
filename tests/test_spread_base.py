"""
Tests for the concrete methods SpreadBase provides directly (not the abstract
ones each subclass implements, and not the ones some subclasses override).

Hosted on Single, which keeps the base implementations of all the accounting/
aggregation methods intact: current_value, trade_value, closed_value, symbol,
spot_price, quote_datetime, get_profit_loss, get_unrealized_profit_loss,
get_trade_premium, get_profit_loss_percent, get_unrealized_profit_loss_percent,
get_days_in_trade, get_close_datetime, get_fees, and __eq__.

Single delegates to a single Option, so each base method's result should equal
the corresponding single-leg quantity. Only the DuckDB updates lookup is mocked
(see conftest.make_option). Dates are derived from the fixture's update keys at
runtime rather than hardcoded.

Fee paths are exercised both off (conftest default) and on (incur_fees=True),
since get_fees and the premium-based methods touch fee state.
"""
import datetime

import pytest

from options_framework.option_types import OptionSpreadType, OptionStatus
from options_framework.spreads.single import Single


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_single(option):
    return Single(options=[option], spread_type=OptionSpreadType.SINGLE)


def _sorted_update_keys(option):
    return sorted(option.updates.keys())


def _open(single, option, quantity=-1):
    """Open the single at its current quote; returns the open datetime."""
    open_dt = option.quote_datetime
    single._open_trade(quantity=quantity)
    return open_dt


def _advance_to_next_key(option, after_dt):
    keys = [k for k in _sorted_update_keys(option) if k > after_dt]
    assert keys, "fixture must contain a quote after the given date"
    nxt = keys[0]
    option._next(nxt)
    return nxt


# ── pass-through properties ───────────────────────────────────────────────────

def test_symbol_returns_first_option_symbol(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    assert single.symbol == option.symbol


def test_spot_price_returns_first_option_spot_price(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    assert single.spot_price == option.spot_price


def test_quote_datetime_returns_first_option_quote_datetime(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    assert single.quote_datetime == option.quote_datetime


# ── current_value / trade_value ───────────────────────────────────────────────

def test_current_value_matches_option_current_value(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    _open(single, option, quantity=-1)
    assert single.current_value == option.current_value


def test_trade_value_matches_option_trade_value(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    _open(single, option, quantity=-1)
    assert single.trade_value == option.trade_value


# ── get_trade_premium ─────────────────────────────────────────────────────────

def test_get_trade_premium_raises_before_open(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    with pytest.raises(RuntimeError):
        single.get_trade_premium()


def test_get_trade_premium_short_is_negative(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    _open(single, option, quantity=-1)
    # Short premium is a credit (cash inflow) -> negative.
    assert single.get_trade_premium() == option.trade_open_info.premium
    assert single.get_trade_premium() < 0


def test_get_trade_premium_long_is_positive(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    _open(single, option, quantity=1)
    assert single.get_trade_premium() == option.trade_open_info.premium
    assert single.get_trade_premium() > 0


# ── get_profit_loss / unrealized ──────────────────────────────────────────────

def test_get_profit_loss_matches_option(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    open_dt = _open(single, option, quantity=-1)
    _advance_to_next_key(option, open_dt)
    assert single.get_profit_loss() == option.get_profit_loss()


def test_get_unrealized_profit_loss_matches_option(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    open_dt = _open(single, option, quantity=-1)
    _advance_to_next_key(option, open_dt)
    assert single.get_unrealized_profit_loss() == option.get_unrealized_profit_loss()


def test_get_profit_loss_percent_is_pnl_over_abs_premium(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    open_dt = _open(single, option, quantity=-1)
    _advance_to_next_key(option, open_dt)

    premium = abs(single.get_trade_premium())
    expected = round(single.get_profit_loss() / premium, 4)
    assert single.get_profit_loss_percent() == expected


def test_get_unrealized_profit_loss_percent_matches_option(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    open_dt = _open(single, option, quantity=-1)
    _advance_to_next_key(option, open_dt)
    expected = round(option.get_unrealized_profit_loss_percent(), 4)
    assert single.get_unrealized_profit_loss_percent() == expected


# ── get_days_in_trade ─────────────────────────────────────────────────────────

def test_get_days_in_trade_none_before_open(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    # No leg has been opened: every leg is still INITIALIZED -> None.
    assert single.get_days_in_trade() is None


def test_get_days_in_trade_counts_days_from_open(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    open_dt = _open(single, option, quantity=-1)
    later = _advance_to_next_key(option, open_dt)

    expected_days = (later.date() - open_dt.date()).days
    assert single.get_days_in_trade() == expected_days


# ── get_close_datetime ────────────────────────────────────────────────────────

def test_get_close_datetime_none_before_close(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    _open(single, option, quantity=-1)
    assert single.get_close_datetime() is None


def test_get_close_datetime_returns_close_date(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    open_dt = _open(single, option, quantity=-1)
    close_dt = _advance_to_next_key(option, open_dt)
    single._close_trade(quote_datetime=close_dt)
    assert single.get_close_datetime() == close_dt


# ── closed_value ──────────────────────────────────────────────────────────────

@pytest.mark.xfail(
    reason="closed_value guard `all(o for o in options if o.trade_close_info is not None)` "
           "checks option truthiness over a filtered generator, not that all legs are closed. "
           "With no legs closed it evaluates all([]) -> True and returns 0.0 instead of None.",
    strict=True,
)
def test_closed_value_none_before_close(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    _open(single, option, quantity=-1)
    # Intended behavior: nothing closed yet -> None.
    assert single.closed_value is None


def test_closed_value_after_full_close(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    open_dt = _open(single, option, quantity=-1)
    close_dt = _advance_to_next_key(option, open_dt)
    single._close_trade(quote_datetime=close_dt)
    # Single leg fully closed: closed_value equals that leg's close premium.
    assert single.closed_value == option.trade_close_info.premium


# ── get_fees (both fee modes) ─────────────────────────────────────────────────

def test_get_fees_zero_when_fees_disabled(make_put_option_380):
    option = make_put_option_380(incur_fees=False)
    single = _make_single(option)
    open_dt = _open(single, option, quantity=-1)
    close_dt = _advance_to_next_key(option, open_dt)
    single._close_trade(quote_datetime=close_dt)
    assert single.get_fees() == 0


def test_get_fees_accumulates_when_enabled(make_put_option_380):
    # standard_fee 0.65/contract, 1 contract, open + close = 2 transactions.
    option = make_put_option_380(incur_fees=True, standard_fee=0.65)
    single = _make_single(option)
    open_dt = _open(single, option, quantity=-1)

    # After open only: one fee charge of 0.65.
    open_only_fees = single.get_fees()
    assert open_only_fees == pytest.approx(0.65)

    close_dt = _advance_to_next_key(option, open_dt)
    single._close_trade(quote_datetime=close_dt)

    # After full close: open + close fees = 1.30.
    assert single.get_fees() == pytest.approx(1.30)


# ── __eq__ ────────────────────────────────────────────────────────────────────

def test_eq_matches_on_instance_id(make_put_option_380):
    option = make_put_option_380()
    single = _make_single(option)
    # Same object compares equal to itself (instance_id identity).
    assert single == single


def test_eq_different_instances_not_equal(make_put_option_380, make_put_option_390):
    s1 = _make_single(make_put_option_380())
    s2 = _make_single(make_put_option_390())
    assert s1 != s2


def test_eq_non_spread_returns_notimplemented(make_put_option_380):
    single = _make_single(make_put_option_380())
    # Comparing to a non-SpreadBase should not raise and should be unequal.
    assert (single == 42) is False