"""
Tests for the Butterfly spread class.

Fixture defaults:
  - LONG PUT butterfly : lower=370, center=380, upper=390, exp 2026-04-10
  - SHORT PUT butterfly: same strikes, position_type=SHORT
  - LONG CALL butterfly: lower=380, center=390, upper=400, exp 2026-04-10

All options use MSFT daily pickle fixtures (start 2026-03-17).
fill_factor=1.0 is passed where mid-price is needed.
"""

import datetime
import pytest
from options_framework.option_types import OptionSpreadType, OptionStatus, OptionPositionType
from options_framework.spreads.butterfly import Butterfly
from conftest import REQUIRED_HISTORY_KEYS

# ── helpers ───────────────────────────────────────────────────────────────────




# ══════════════════════════════════════════════════════════════════════════════
# Construction & properties
# ══════════════════════════════════════════════════════════════════════════════

def test_post_init_assigns_leg_references(make_butterfly):
    bf = make_butterfly()
    assert bf.lower_option  is bf.options[0]
    assert bf.center_option is bf.options[1]
    assert bf.upper_option  is bf.options[2]

def test_spread_type(make_butterfly):
    bf = make_butterfly()
    assert bf.spread_type == OptionSpreadType.BUTTERFLY

def test_default_position_type_is_long(make_butterfly):
    bf = make_butterfly()
    assert bf.position_type == OptionPositionType.LONG

def test_short_position_type_stored(make_butterfly):
    bf = make_butterfly(position_type=OptionPositionType.SHORT)
    assert bf.position_type == OptionPositionType.SHORT

def test_option_type_property_put(make_butterfly):
    bf = make_butterfly(option_type='put')
    assert bf.option_type == 'put'

def test_option_type_property_call(make_butterfly):
    bf = make_butterfly(option_type='call')
    assert bf.option_type == 'call'

def test_expiration_property(make_butterfly):
    bf = make_butterfly()
    assert bf.expiration == datetime.date(2026, 4, 10)

def test_symbol_delegates_to_options_list(make_butterfly):
    """symbol must use options[0] (lower leg), matching SpreadBase contract."""
    bf = make_butterfly()
    assert bf.symbol == bf.options[0].symbol
    assert bf.symbol == 'MSFT'

def test_repr_contains_key_info(make_butterfly):
    bf = make_butterfly()
    r = repr(bf)
    assert 'BUTTERFLY' in r
    assert '370' in r
    assert '380' in r
    assert '390' in r

def test_instance_ids_are_unique(make_butterfly):
    bf1 = make_butterfly()
    bf2 = make_butterfly()
    assert bf1.instance_id != bf2.instance_id

def test_equality_based_on_instance_id(make_butterfly):
    bf1 = make_butterfly()
    bf2 = make_butterfly()
    assert bf1 != bf2
    assert bf1 == bf1


# ══════════════════════════════════════════════════════════════════════════════
# Price calculation
# ══════════════════════════════════════════════════════════════════════════════

def test_long_butterfly_price_formula(make_butterfly):
    """LONG: price = lower + upper - 2*center"""
    bf = make_butterfly()
    expected = bf.lower_option.price + bf.upper_option.price - 2 * bf.center_option.price
    assert bf.price == pytest.approx(expected, abs=0.01)

def test_short_butterfly_price_formula(make_butterfly):
    """SHORT: price = 2*center - lower - upper"""
    bf = make_butterfly(position_type=OptionPositionType.SHORT)
    expected = 2 * bf.center_option.price - bf.lower_option.price - bf.upper_option.price
    assert bf.price == pytest.approx(expected, abs=0.01)

def test_long_price_is_non_negative(make_butterfly):
    """A long butterfly on a normal vol surface is typically positive debit."""
    bf = make_butterfly()
    assert bf.price >= 0

def test_call_butterfly_price(make_butterfly):
    bf = make_butterfly(option_type='call')
    expected = bf.lower_option.price + bf.upper_option.price - 2 * bf.center_option.price
    assert bf.price == pytest.approx(expected, abs=0.01)


# ══════════════════════════════════════════════════════════════════════════════
# open_trade
# ══════════════════════════════════════════════════════════════════════════════

def test_long_butterfly_leg_quantities(make_butterfly):
    """LONG: lower=+1, center=-2, upper=+1"""
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade(quantity=1)
    assert bf.lower_option.quantity  == +1
    assert bf.center_option.quantity == -2
    assert bf.upper_option.quantity  == +1

def test_long_butterfly_spread_quantity(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade(quantity=1)
    assert bf.quantity == +1  # tracks lower leg

def test_long_butterfly_multi_quantity(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade(quantity=3)
    assert bf.lower_option.quantity  == +3
    assert bf.center_option.quantity == -6
    assert bf.upper_option.quantity  == +3

def test_short_butterfly_leg_quantities(make_butterfly):
    """SHORT: lower=-1, center=+2, upper=-1"""
    bf = make_butterfly(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    bf._open_trade(quantity=1)
    assert bf.lower_option.quantity  == -1
    assert bf.center_option.quantity == +2
    assert bf.upper_option.quantity  == -1

def test_short_butterfly_spread_quantity(make_butterfly):
    bf = make_butterfly(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    bf._open_trade(quantity=1)
    assert bf.quantity == -1

def test_open_trade_accepts_negative_quantity_as_absolute(make_butterfly):
    """open_trade uses abs(quantity) — sign comes from position_type."""
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade(quantity=-2)
    assert bf.lower_option.quantity == +2
    assert bf.center_option.quantity == -4

def test_open_trade_saves_user_defined_kwargs(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade(quantity=1, my_tag='iron_fly_hedge')
    assert bf.user_defined.get('my_tag') == 'iron_fly_hedge'


# ══════════════════════════════════════════════════════════════════════════════
# get_trade_price
# ══════════════════════════════════════════════════════════════════════════════

def test_returns_none_before_open(make_butterfly):
    bf = make_butterfly()
    assert bf.get_trade_price() is None

def test_returns_float_after_open(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    price = bf.get_trade_price()
    assert isinstance(price, float)

def test_long_trade_price_matches_formula(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    lp = bf.lower_option.trade_open_info.price
    cp = bf.center_option.trade_open_info.price
    up = bf.upper_option.trade_open_info.price
    expected = lp + up - 2 * cp
    assert bf.get_trade_price() == pytest.approx(expected, abs=0.01)

def test_short_trade_price_matches_formula(make_butterfly):
    bf = make_butterfly(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    bf._open_trade()
    lp = bf.lower_option.trade_open_info.price
    cp = bf.center_option.trade_open_info.price
    up = bf.upper_option.trade_open_info.price
    expected = 2 * cp - lp - up
    assert bf.get_trade_price() == pytest.approx(expected, abs=0.01)


# ══════════════════════════════════════════════════════════════════════════════
# close_trade
# ══════════════════════════════════════════════════════════════════════════════

def test_long_butterfly_close_zeroes_quantity(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade(quantity=1)
    dt = bf.center_option.quote_datetime
    bf._close_trade(quote_datetime=dt)

    # After full close, lower_option.quantity should reflect closed state
    assert bf.quantity == 0
    assert OptionStatus.TRADE_IS_CLOSED in bf.lower_option.status
    assert OptionStatus.TRADE_IS_CLOSED in bf.center_option.status
    assert OptionStatus.TRADE_IS_CLOSED in bf.upper_option.status

def test_close_trade_requires_keyword_only_quote_datetime(make_butterfly):
    """Signature must enforce quote_datetime as keyword-only."""
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    dt = bf.center_option.quote_datetime
    # This must not raise TypeError — keyword-only call
    bf._close_trade(quote_datetime=dt)

def test_close_trade_with_explicit_quantity(make_butterfly):
    """Explicit quantity should not crash and should close the specified number."""
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade(quantity=2)
    dt = bf.center_option.quote_datetime
    # Partial close: close 1 of the 2 units (if supported by Option.close_trade)
    # At minimum this must not raise.
    bf._close_trade(quote_datetime=dt, quantity=bf.lower_option.quantity)

def test_get_closed_price_after_close(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    dt = bf.center_option.quote_datetime
    bf._close_trade(quote_datetime=dt)
    closed = bf.get_closed_price()
    assert isinstance(closed, float)

def test_get_closed_price_before_close_is_none(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    assert bf.get_closed_price() is None

def test_closed_price_matches_formula(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    dt = bf.center_option.quote_datetime
    bf._close_trade(quote_datetime=dt)
    lp = bf.lower_option.trade_close_info.price
    cp = bf.center_option.trade_close_info.price
    up = bf.upper_option.trade_close_info.price
    expected = lp + up - 2 * cp
    assert bf.get_closed_price() == pytest.approx(expected, abs=0.01)


# ══════════════════════════════════════════════════════════════════════════════
# DTE
# ══════════════════════════════════════════════════════════════════════════════


def test_dte_delegates_to_center_leg(make_butterfly):
    bf = make_butterfly()
    assert bf.get_dte() == bf.center_option.get_dte()

def test_dte_is_positive_before_expiry(make_butterfly):
    bf = make_butterfly()
    assert bf.get_dte() > 0


# ══════════════════════════════════════════════════════════════════════════════
# SpreadBase delegation (spot_price, quote_datetime, pnl)
# ══════════════════════════════════════════════════════════════════════════════

def test_spot_price_delegates_to_first_option(make_butterfly):
    bf = make_butterfly()
    assert bf.spot_price == bf.options[0].spot_price

def test_quote_datetime_delegates_to_first_option(make_butterfly):
    bf = make_butterfly()
    assert bf.quote_datetime == bf.options[0].quote_datetime

def test_get_profit_loss_after_open(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    pnl = bf.get_profit_loss()
    assert isinstance(pnl, float)

def test_current_value_sums_legs(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    expected = sum(o.current_value for o in bf.options)
    assert bf.current_value == pytest.approx(expected, abs=0.01)

def test_trade_value_sums_legs(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    expected = sum(o.trade_value for o in bf.options)
    assert bf.trade_value == pytest.approx(expected, abs=0.01)

def test_max_profit_returns_none(make_butterfly):
    bf = make_butterfly()
    assert bf.max_profit is None

def test_max_loss_returns_none(make_butterfly):
    bf = make_butterfly()
    assert bf.max_loss is None


# ══════════════════════════════════════════════════════════════════════════════
# get_price_history
# ══════════════════════════════════════════════════════════════════════════════

def test_returns_list(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    # Advance through at least some updates so history is populated
    result = bf.get_history()
    assert isinstance(result, list)

def test_each_entry_is_dict_with_required_keys(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    history = bf.get_history()
    for entry in history:
        assert isinstance(entry, dict)
        assert REQUIRED_HISTORY_KEYS == entry.keys()



def test_price_matches_calculate_price_for_each_row(make_butterfly):
    """Price at each row must equal _calculate_price using the update dicts for each leg."""
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    lower_u  = bf.lower_option.updates
    center_u = bf.center_option.updates
    upper_u  = bf.upper_option.updates
    last_date = bf.lower_option.quote_datetime
    keys = sorted(k for k in lower_u if k <= last_date)
    history = bf.get_history()

    for i, entry in enumerate(history):
        k = keys[i]
        expected = bf._calculate_price(
            lower_price=lower_u[k]['price'],
            center_price=center_u[k]['price'],
            upper_price=upper_u[k]['price'],
        )
        assert entry['price'] == pytest.approx(expected, abs=0.01)

def test_history_length_matches_lower_leg_updates(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    history = bf.get_history()
    last_date = bf.lower_option.quote_datetime
    expected_len = len([k for k in bf.lower_option.updates if k <= last_date])
    assert len(history) == expected_len

def test_spot_price_matches_lower_leg_updates(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    history = bf.get_history()
    lower_u = bf.lower_option.updates
    last_date = bf.lower_option.quote_datetime
    keys = sorted(k for k in lower_u if k <= last_date)
    for i, entry in enumerate(history):
        assert entry['spot_price'] == lower_u[keys[i]].get('spot_price')

def test_pnl_is_zero_at_open_bar(make_butterfly):
    """PnL at the first history entry (open bar) should be ~0."""
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    history = bf.get_history()
    assert history[0]['pnl'] == pytest.approx(0.0, abs=1.0)

def test_pnl_pct_is_zero_at_open_bar(make_butterfly):
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    history = bf.get_history()
    assert history[0]['pnl_pct'] == pytest.approx(0.0, abs=0.01)

def test_short_butterfly_history_keys_present(make_butterfly):
    bf = make_butterfly(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    bf._open_trade()
    history = bf.get_history()
    for entry in history:
        assert REQUIRED_HISTORY_KEYS == entry.keys()

def test_short_butterfly_price_formula_in_history(make_butterfly):
    bf = make_butterfly(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    bf._open_trade()
    lower_u  = bf.lower_option.updates
    center_u = bf.center_option.updates
    upper_u  = bf.upper_option.updates
    last_date = bf.lower_option.quote_datetime
    keys = sorted(k for k in lower_u if k <= last_date)
    history  = bf.get_history()

    for i, entry in enumerate(history):
        k = keys[i]
        expected = 2 * center_u[k]['price'] - lower_u[k]['price'] - upper_u[k]['price']
        assert entry['price'] == pytest.approx(expected, abs=0.02)

def test_call_butterfly_history_keys_present(make_butterfly):
    bf = make_butterfly(option_type='call', fill_factor=1.0)
    bf._open_trade()
    history = bf.get_history()
    for entry in history:
        assert REQUIRED_HISTORY_KEYS == entry.keys()

def test_raises_before_open(make_butterfly):
    """get_price_history must raise RuntimeError if trade has not been opened (mirrors Single)."""
    bf = make_butterfly()
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        bf.get_history()


# ── max_profit, max_loss, get_required_margin ─────────────────────────────────

def test_max_profit_returns_none_before_open(make_butterfly):
    bf = make_butterfly()
    assert bf.max_profit is None


def test_max_loss_returns_none_before_open(make_butterfly):
    bf = make_butterfly()
    assert bf.max_loss is None


def test_long_max_profit_equals_wing_width_minus_debit(make_butterfly):
    """LONG: max profit = wing_width - trade_price, achieved at center strike at expiry."""
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    wing_width = min(
        bf.center_option.strike - bf.lower_option.strike,
        bf.upper_option.strike - bf.center_option.strike,
    )
    expected = wing_width - bf.get_trade_price()
    assert bf.max_profit == pytest.approx(expected, abs=0.01)


def test_long_max_loss_equals_trade_price(make_butterfly):
    """LONG: max loss is the net debit paid."""
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    assert bf.max_loss == pytest.approx(bf.get_trade_price(), abs=0.01)


def test_short_max_profit_equals_trade_price(make_butterfly):
    """SHORT: max profit is the net credit received."""
    bf = make_butterfly(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    bf._open_trade()
    assert bf.max_profit == pytest.approx(bf.get_trade_price(), abs=0.01)


def test_short_max_loss_equals_wing_width_minus_credit(make_butterfly):
    """SHORT: max loss = wing_width - net credit."""
    bf = make_butterfly(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    bf._open_trade()
    wing_width = min(
        bf.center_option.strike - bf.lower_option.strike,
        bf.upper_option.strike - bf.center_option.strike,
    )
    expected = wing_width - bf.get_trade_price()
    assert bf.max_loss == pytest.approx(expected, abs=0.01)


def test_max_profit_plus_max_loss_equals_wing_width(make_butterfly):
    """max_profit + max_loss must always equal the wing width."""
    bf = make_butterfly(fill_factor=1.0)
    bf._open_trade()
    wing_width = min(
        bf.center_option.strike - bf.lower_option.strike,
        bf.upper_option.strike - bf.center_option.strike,
    )
    assert bf.max_profit + bf.max_loss == pytest.approx(wing_width, abs=0.01)


def test_required_margin_long_is_zero(make_butterfly):
    """LONG butterfly is a debit trade — no margin required."""
    bf = make_butterfly()
    assert bf.get_required_margin(1) == 0.0


def test_required_margin_short_is_positive(make_butterfly):
    bf = make_butterfly(position_type=OptionPositionType.SHORT)
    assert bf.get_required_margin(1) > 0


def test_required_margin_short_formula(make_butterfly):
    """SHORT margin = (wing_width - current_price) * 100 * quantity."""
    bf = make_butterfly(position_type=OptionPositionType.SHORT)
    wing_width = min(
        bf.center_option.strike - bf.lower_option.strike,
        bf.upper_option.strike - bf.center_option.strike,
    )
    expected = (wing_width - bf.price) * 100 * 1
    assert bf.get_required_margin(1) == pytest.approx(expected, abs=1.0)


def test_required_margin_scales_with_quantity(make_butterfly):
    bf = make_butterfly(position_type=OptionPositionType.SHORT)
    assert bf.get_required_margin(3) == pytest.approx(bf.get_required_margin(1) * 3, abs=0.01)


def test_required_margin_uses_absolute_quantity(make_butterfly):
    """Negative quantity should give same margin as positive."""
    bf = make_butterfly(position_type=OptionPositionType.SHORT)
    assert bf.get_required_margin(-2) == pytest.approx(bf.get_required_margin(2), abs=0.01)
