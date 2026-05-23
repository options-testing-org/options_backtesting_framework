"""
Tests for the Ratio spread class.

Fixture defaults (put ratio, ratio=2):
  long_option  = MSFT 380P 2026-04-10  (buy 1x)
  short_option = MSFT 370P 2026-04-10  (sell 2x)

fill_factor=1.0 is passed where mid-price is needed.
"""

import datetime
import pytest
from options_framework.option_types import OptionSpreadType, OptionStatus
from options_framework.spreads.ratio import Ratio

from conftest import REQUIRED_HISTORY_KEYS


# ── Construction & properties ─────────────────────────────────────────────────

def test_post_init_assigns_leg_references(make_ratio):
    r = make_ratio()
    assert r.long_option is r.options[0]
    assert r.short_option is r.options[1]


def test_spread_type(make_ratio):
    assert make_ratio().spread_type == OptionSpreadType.RATIO


def test_ratio_stored(make_ratio):
    assert make_ratio(ratio=2).ratio == 2


def test_ratio_3_stored(make_ratio):
    assert make_ratio(ratio=3).ratio == 3


def test_expiration_property(make_ratio):
    assert make_ratio().expiration == datetime.date(2026, 4, 10)


def test_option_type_property_put(make_ratio):
    assert make_ratio(option_type='put').option_type == 'put'


def test_option_type_property_call(make_ratio):
    assert make_ratio(option_type='call').option_type == 'call'


def test_symbol_delegates_to_options_list(make_ratio):
    r = make_ratio()
    assert r.symbol == r.options[0].symbol
    assert r.symbol == 'MSFT'


def test_repr_contains_key_info(make_ratio):
    r = repr(make_ratio())
    assert 'RATIO' in r
    assert '1x' in r
    assert '2x' in r
    assert '380' in r
    assert '370' in r


def test_repr_reflects_ratio(make_ratio):
    r = repr(make_ratio(ratio=3))
    assert '3x' in r


def test_instance_ids_are_unique(make_ratio):
    assert make_ratio().instance_id != make_ratio().instance_id


def test_equality_based_on_instance_id(make_ratio):
    r1 = make_ratio()
    r2 = make_ratio()
    assert r1 != r2
    assert r1 == r1


# ── Price calculation ─────────────────────────────────────────────────────────

def test_price_formula(make_ratio):
    """price = long_price - ratio * short_price"""
    r = make_ratio()
    expected = r.long_option.price - 2 * r.short_option.price
    assert r.price == pytest.approx(expected, abs=0.01)


def test_price_formula_ratio_3(make_ratio):
    r = make_ratio(ratio=3)
    expected = r.long_option.price - 3 * r.short_option.price
    assert r.price == pytest.approx(expected, abs=0.01)


# ── open_trade ────────────────────────────────────────────────────────────────

def test_open_trade_long_leg_quantity(make_ratio):
    """Long leg is always +qty."""
    r = make_ratio(fill_factor=1.0)
    r._open_trade(quantity=1)
    assert r.long_option.quantity == +1


def test_open_trade_short_leg_quantity(make_ratio):
    """Short leg is -ratio * qty."""
    r = make_ratio(fill_factor=1.0)
    r._open_trade(quantity=1)
    assert r.short_option.quantity == -2


def test_open_trade_ratio_3_short_leg_quantity(make_ratio):
    r = make_ratio(ratio=3, fill_factor=1.0)
    r._open_trade(quantity=1)
    assert r.short_option.quantity == -3


def test_open_trade_multi_quantity(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade(quantity=3)
    assert r.long_option.quantity == +3
    assert r.short_option.quantity == -6


def test_open_trade_spread_quantity_tracks_long_leg(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade(quantity=2)
    assert r.quantity == +2


def test_open_trade_accepts_negative_quantity_as_absolute(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade(quantity=-2)
    assert r.long_option.quantity == +2
    assert r.short_option.quantity == -4


def test_open_trade_saves_user_defined_kwargs(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade(quantity=1, tag='backspread')
    assert r.user_defined.get('tag') == 'backspread'


def test_open_trade_status_is_open(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    assert OptionStatus.TRADE_IS_OPEN in r.long_option.status
    assert OptionStatus.TRADE_IS_OPEN in r.short_option.status


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_none_before_open(make_ratio):
    assert make_ratio().get_trade_price() is None


def test_get_trade_price_returns_float_after_open(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    assert isinstance(r.get_trade_price(), float)


def test_trade_price_matches_formula(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    lp = r.long_option.trade_open_info.price
    sp = r.short_option.trade_open_info.price
    assert r.get_trade_price() == pytest.approx(lp - 2 * sp, abs=0.01)


def test_trade_price_ratio_3_matches_formula(make_ratio):
    r = make_ratio(ratio=3, fill_factor=1.0)
    r._open_trade()
    lp = r.long_option.trade_open_info.price
    sp = r.short_option.trade_open_info.price
    assert r.get_trade_price() == pytest.approx(lp - 3 * sp, abs=0.01)


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_both_legs(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    r._close_trade(quote_datetime=r.long_option.quote_datetime)
    assert OptionStatus.TRADE_IS_CLOSED in r.long_option.status
    assert OptionStatus.TRADE_IS_CLOSED in r.short_option.status


def test_close_trade_requires_keyword_only_quote_datetime(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    r._close_trade(quote_datetime=r.long_option.quote_datetime)


def test_close_trade_with_explicit_quantity_does_not_raise(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade(quantity=2)
    r._close_trade(quote_datetime=r.long_option.quote_datetime,
                   quantity=r.long_option.quantity)


def test_get_closed_price_returns_none_before_close(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    assert r.get_closed_price() is None


def test_get_closed_price_returns_float_after_close(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    r._close_trade(quote_datetime=r.long_option.quote_datetime)
    assert isinstance(r.get_closed_price(), float)


def test_closed_price_matches_formula(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    r._close_trade(quote_datetime=r.long_option.quote_datetime)
    lp = r.long_option.trade_close_info.price
    sp = r.short_option.trade_close_info.price
    assert r.get_closed_price() == pytest.approx(lp - 2 * sp, abs=0.01)


# ── DTE & SpreadBase delegation ───────────────────────────────────────────────

def test_dte_delegates_to_long_leg(make_ratio):
    r = make_ratio()
    assert r.get_dte() == r.long_option.get_dte()


def test_dte_is_positive_before_expiry(make_ratio):
    assert make_ratio().get_dte() > 0


def test_spot_price_delegates_to_first_option(make_ratio):
    r = make_ratio()
    assert r.spot_price == r.options[0].spot_price


def test_quote_datetime_delegates_to_first_option(make_ratio):
    r = make_ratio()
    assert r.quote_datetime == r.options[0].quote_datetime


def test_get_profit_loss_after_open(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    assert isinstance(r.get_profit_loss(), float)


def test_current_value_sums_legs(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    assert r.current_value == pytest.approx(sum(o.current_value for o in r.options), abs=0.01)


def test_trade_value_sums_legs(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    assert r.trade_value == pytest.approx(sum(o.trade_value for o in r.options), abs=0.01)


def test_max_profit_returns_none(make_ratio):
    assert make_ratio().max_profit is None


def test_max_loss_returns_none(make_ratio):
    assert make_ratio().max_loss is None


def test_get_required_margin_returns_none(make_ratio):
    assert make_ratio().get_required_margin(1) is None


# ── get_price_history ─────────────────────────────────────────────────────────

def test_price_history_raises_before_open(make_ratio):
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        make_ratio().get_price_history()


def test_price_history_returns_list(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    assert isinstance(r.get_price_history(), list)


def test_price_history_each_entry_has_required_keys(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    for entry in r.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_length_matches_long_leg_updates(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    last_date = r.long_option.quote_datetime
    expected_len = sum(1 for k in r.long_option.updates if k <= last_date)
    assert len(r.get_price_history()) == expected_len


def test_price_history_price_matches_calculate_price_each_row(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    long_u = r.long_option.updates
    short_u = r.short_option.updates
    last_date = r.long_option.quote_datetime
    keys = sorted(k for k in long_u if k <= last_date)

    for i, entry in enumerate(r.get_price_history()):
        k = keys[i]
        expected = r._calculate_price(
            long_price=long_u[k]['price'],
            short_price=short_u[k]['price'],
        )
        assert entry['price'] == pytest.approx(expected, abs=0.01)


def test_price_history_spot_price_matches_long_leg_updates(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    long_u = r.long_option.updates
    last_date = r.long_option.quote_datetime
    keys = sorted(k for k in long_u if k <= last_date)
    for i, entry in enumerate(r.get_price_history()):
        assert entry['spot_price'] == long_u[keys[i]].get('spot_price')


def test_price_history_pnl_is_zero_at_open_bar(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    assert r.get_price_history()[0]['pnl'] == pytest.approx(0.0, abs=1.0)


def test_price_history_pnl_pct_is_zero_at_open_bar(make_ratio):
    r = make_ratio(fill_factor=1.0)
    r._open_trade()
    assert r.get_price_history()[0]['pnl_pct'] == pytest.approx(0.0, abs=0.01)


def test_price_history_ratio_3_has_required_keys(make_ratio):
    r = make_ratio(ratio=3, fill_factor=1.0)
    r._open_trade()
    for entry in r.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_ratio_3_price_formula(make_ratio):
    r = make_ratio(ratio=3, fill_factor=1.0)
    r._open_trade()
    long_u = r.long_option.updates
    short_u = r.short_option.updates
    last_date = r.long_option.quote_datetime
    keys = sorted(k for k in long_u if k <= last_date)

    for i, entry in enumerate(r.get_price_history()):
        k = keys[i]
        expected = long_u[k]['price'] - 3 * short_u[k]['price']
        assert entry['price'] == pytest.approx(expected, abs=0.01)


def test_price_history_call_ratio_has_required_keys(make_ratio):
    r = make_ratio(option_type='call', fill_factor=1.0)
    r._open_trade()
    for entry in r.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS
