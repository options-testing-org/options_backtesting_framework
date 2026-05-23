"""
Tests for the IronCondor spread class.

Fixture defaults (SHORT iron condor, net credit):
  lower_put  = MSFT 370P 2026-04-10
  upper_put  = MSFT 380P 2026-04-10
  lower_call = MSFT 390C 2026-04-10
  upper_call = MSFT 400C 2026-04-10

fill_factor=1.0 is passed where mid-price is needed.
"""

import datetime
import pytest
from options_framework.option_types import OptionSpreadType, OptionStatus, OptionPositionType
from options_framework.spreads.iron_condor import IronCondor
from conftest import REQUIRED_HISTORY_KEYS


# ── Construction & properties ─────────────────────────────────────────────────

def test_post_init_assigns_leg_references(make_iron_condor):
    ic = make_iron_condor()
    assert ic.lower_put is ic.options[0]
    assert ic.upper_put is ic.options[1]
    assert ic.lower_call is ic.options[2]
    assert ic.upper_call is ic.options[3]


def test_spread_type(make_iron_condor):
    assert make_iron_condor().spread_type == OptionSpreadType.IRON_CONDOR


def test_default_position_type_is_short(make_iron_condor):
    assert make_iron_condor().position_type == OptionPositionType.SHORT


def test_long_position_type_stored(make_iron_condor):
    assert make_iron_condor(position_type=OptionPositionType.LONG).position_type == OptionPositionType.LONG


def test_expiration_property(make_iron_condor):
    assert make_iron_condor().expiration == datetime.date(2026, 4, 10)


def test_symbol_delegates_to_options_list(make_iron_condor):
    ic = make_iron_condor()
    assert ic.symbol == ic.options[0].symbol
    assert ic.symbol == 'MSFT'


def test_repr_contains_key_info(make_iron_condor):
    r = repr(make_iron_condor())
    assert 'IRON_CONDOR' in r
    assert '370' in r
    assert '380' in r
    assert '390' in r
    assert '400' in r


def test_instance_ids_are_unique(make_iron_condor):
    assert make_iron_condor().instance_id != make_iron_condor().instance_id


def test_equality_based_on_instance_id(make_iron_condor):
    ic1 = make_iron_condor()
    ic2 = make_iron_condor()
    assert ic1 != ic2
    assert ic1 == ic1


# ── Price calculation ─────────────────────────────────────────────────────────

def test_short_iron_condor_price_formula(make_iron_condor):
    """SHORT: price = (upper_put + lower_call) - (lower_put + upper_call)"""
    ic = make_iron_condor()
    expected = (ic.upper_put.price + ic.lower_call.price) - (ic.lower_put.price + ic.upper_call.price)
    assert ic.price == pytest.approx(expected, abs=0.01)


def test_long_iron_condor_price_formula(make_iron_condor):
    """LONG: price = (lower_put + upper_call) - (upper_put + lower_call)"""
    ic = make_iron_condor(position_type=OptionPositionType.LONG)
    expected = (ic.lower_put.price + ic.upper_call.price) - (ic.upper_put.price + ic.lower_call.price)
    assert ic.price == pytest.approx(expected, abs=0.01)


# ── open_trade ────────────────────────────────────────────────────────────────

def test_short_iron_condor_leg_quantities(make_iron_condor):
    """SHORT: long wings (+1), short body (-1)"""
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade(quantity=1)
    assert ic.lower_put.quantity == +1
    assert ic.upper_put.quantity == -1
    assert ic.lower_call.quantity == -1
    assert ic.upper_call.quantity == +1


def test_short_iron_condor_spread_quantity(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade(quantity=1)
    assert ic.quantity == +1  # tracks lower_put leg


def test_short_iron_condor_multi_quantity(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade(quantity=3)
    assert ic.lower_put.quantity == +3
    assert ic.upper_put.quantity == -3
    assert ic.lower_call.quantity == -3
    assert ic.upper_call.quantity == +3


def test_long_iron_condor_leg_quantities(make_iron_condor):
    """LONG: short wings (-1), long body (+1)"""
    ic = make_iron_condor(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ic._open_trade(quantity=1)
    assert ic.lower_put.quantity == -1
    assert ic.upper_put.quantity == +1
    assert ic.lower_call.quantity == +1
    assert ic.upper_call.quantity == -1


def test_long_iron_condor_spread_quantity(make_iron_condor):
    ic = make_iron_condor(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ic._open_trade(quantity=1)
    assert ic.quantity == -1


def test_open_trade_accepts_negative_quantity_as_absolute(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade(quantity=-2)
    assert ic.lower_put.quantity == +2
    assert ic.upper_put.quantity == -2
    assert ic.lower_call.quantity == -2
    assert ic.upper_call.quantity == +2


def test_open_trade_saves_user_defined_kwargs(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade(quantity=1, strategy='income')
    assert ic.user_defined.get('strategy') == 'income'


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_none_before_open(make_iron_condor):
    assert make_iron_condor().get_trade_price() is None


def test_get_trade_price_returns_float_after_open(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    assert isinstance(ic.get_trade_price(), float)


def test_short_trade_price_matches_formula(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    lp = ic.lower_put.trade_open_info.price
    up = ic.upper_put.trade_open_info.price
    lc = ic.lower_call.trade_open_info.price
    uc = ic.upper_call.trade_open_info.price
    assert ic.get_trade_price() == pytest.approx((up + lc) - (lp + uc), abs=0.01)


def test_long_trade_price_matches_formula(make_iron_condor):
    ic = make_iron_condor(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ic._open_trade()
    lp = ic.lower_put.trade_open_info.price
    up = ic.upper_put.trade_open_info.price
    lc = ic.lower_call.trade_open_info.price
    uc = ic.upper_call.trade_open_info.price
    assert ic.get_trade_price() == pytest.approx((lp + uc) - (up + lc), abs=0.01)


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_all_legs(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    ic._close_trade(quote_datetime=ic.lower_put.quote_datetime)
    for leg in ic.options:
        assert OptionStatus.TRADE_IS_CLOSED in leg.status


def test_close_trade_requires_keyword_only_quote_datetime(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    ic._close_trade(quote_datetime=ic.lower_put.quote_datetime)  # must not raise


def test_close_trade_with_explicit_quantity_does_not_raise(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade(quantity=2)
    ic._close_trade(quote_datetime=ic.lower_put.quote_datetime,
                    quantity=ic.lower_put.quantity)


def test_get_closed_price_returns_none_before_close(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    assert ic.get_closed_price() is None


def test_get_closed_price_returns_float_after_close(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    ic._close_trade(quote_datetime=ic.lower_put.quote_datetime)
    assert isinstance(ic.get_closed_price(), float)


def test_closed_price_matches_formula(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    ic._close_trade(quote_datetime=ic.lower_put.quote_datetime)
    lp = ic.lower_put.trade_close_info.price
    up = ic.upper_put.trade_close_info.price
    lc = ic.lower_call.trade_close_info.price
    uc = ic.upper_call.trade_close_info.price
    assert ic.get_closed_price() == pytest.approx((up + lc) - (lp + uc), abs=0.01)


# ── DTE & SpreadBase delegation ───────────────────────────────────────────────

def test_dte_delegates_to_lower_put(make_iron_condor):
    ic = make_iron_condor()
    assert ic.get_dte() == ic.lower_put.get_dte()


def test_dte_is_positive_before_expiry(make_iron_condor):
    assert make_iron_condor().get_dte() > 0


def test_spot_price_delegates_to_first_option(make_iron_condor):
    ic = make_iron_condor()
    assert ic.spot_price == ic.options[0].spot_price


def test_quote_datetime_delegates_to_first_option(make_iron_condor):
    ic = make_iron_condor()
    assert ic.quote_datetime == ic.options[0].quote_datetime


def test_get_profit_loss_after_open(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    assert isinstance(ic.get_profit_loss(), float)


def test_current_value_sums_legs(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    assert ic.current_value == pytest.approx(sum(o.current_value for o in ic.options), abs=0.01)


def test_trade_value_sums_legs(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    assert ic.trade_value == pytest.approx(sum(o.trade_value for o in ic.options), abs=0.01)


# ── max_profit, max_loss, get_required_margin ─────────────────────────────────

def test_max_profit_returns_none_before_open(make_iron_condor):
    assert make_iron_condor().max_profit is None


def test_max_loss_returns_none_before_open(make_iron_condor):
    assert make_iron_condor().max_loss is None


def test_short_max_profit_equals_trade_price(make_iron_condor):
    """SHORT: max profit is the net credit received."""
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    assert ic.max_profit == pytest.approx(ic.get_trade_price(), abs=0.01)


def test_short_max_loss_equals_wing_width_minus_credit(make_iron_condor):
    """SHORT: max loss = min(put_spread_width, call_spread_width) - credit."""
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    wing_width = min(
        ic.upper_put.strike - ic.lower_put.strike,
        ic.upper_call.strike - ic.lower_call.strike,
    )
    assert ic.max_loss == pytest.approx(wing_width - ic.get_trade_price(), abs=0.01)


def test_long_max_profit_equals_wing_width_minus_debit(make_iron_condor):
    """LONG: max profit = min(put_spread_width, call_spread_width) - debit."""
    ic = make_iron_condor(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ic._open_trade()
    wing_width = min(
        ic.upper_put.strike - ic.lower_put.strike,
        ic.upper_call.strike - ic.lower_call.strike,
    )
    assert ic.max_profit == pytest.approx(wing_width - ic.get_trade_price(), abs=0.01)


def test_long_max_loss_equals_trade_price(make_iron_condor):
    """LONG: max loss is the net debit paid."""
    ic = make_iron_condor(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ic._open_trade()
    assert ic.max_loss == pytest.approx(ic.get_trade_price(), abs=0.01)


def test_max_profit_plus_max_loss_equals_wing_width(make_iron_condor):
    """max_profit + max_loss must always equal the wing width."""
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    wing_width = min(
        ic.upper_put.strike - ic.lower_put.strike,
        ic.upper_call.strike - ic.lower_call.strike,
    )
    assert ic.max_profit + ic.max_loss == pytest.approx(wing_width, abs=0.01)


def test_required_margin_long_is_zero(make_iron_condor):
    assert make_iron_condor(position_type=OptionPositionType.LONG).get_required_margin(1) == 0.0


def test_required_margin_short_is_positive(make_iron_condor):
    assert make_iron_condor().get_required_margin(1) > 0


def test_required_margin_short_formula(make_iron_condor):
    ic = make_iron_condor()
    wing_width = min(
        ic.upper_put.strike - ic.lower_put.strike,
        ic.upper_call.strike - ic.lower_call.strike,
    )
    expected = (wing_width - ic.price) * 100 * 1
    assert ic.get_required_margin(1) == pytest.approx(expected, abs=1.0)


def test_required_margin_scales_with_quantity(make_iron_condor):
    ic = make_iron_condor()
    assert ic.get_required_margin(3) == pytest.approx(ic.get_required_margin(1) * 3, abs=0.01)


def test_required_margin_uses_absolute_quantity(make_iron_condor):
    ic = make_iron_condor()
    assert ic.get_required_margin(-2) == pytest.approx(ic.get_required_margin(2), abs=0.01)


# ── get_price_history ─────────────────────────────────────────────────────────

def test_price_history_raises_before_open(make_iron_condor):
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        make_iron_condor().get_price_history()


def test_price_history_returns_list(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    assert isinstance(ic.get_price_history(), list)


def test_price_history_each_entry_has_required_keys(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    for entry in ic.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_length_matches_lower_put_updates(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    last_date = ic.lower_put.quote_datetime
    expected_len = sum(1 for k in ic.lower_put.updates if k <= last_date)
    assert len(ic.get_price_history()) == expected_len


def test_price_history_price_matches_calculate_price_each_row(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    lp_u = ic.lower_put.updates
    up_u = ic.upper_put.updates
    lc_u = ic.lower_call.updates
    uc_u = ic.upper_call.updates
    last_date = ic.lower_put.quote_datetime
    keys = sorted(k for k in lp_u if k <= last_date)

    for i, entry in enumerate(ic.get_price_history()):
        k = keys[i]
        expected = ic._calculate_price(
            lower_put_price=lp_u[k]['price'],
            upper_put_price=up_u[k]['price'],
            lower_call_price=lc_u[k]['price'],
            upper_call_price=uc_u[k]['price'],
        )
        assert entry['price'] == pytest.approx(expected, abs=0.01)


def test_price_history_spot_price_matches_lower_put_updates(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    lp_u = ic.lower_put.updates
    last_date = ic.lower_put.quote_datetime
    keys = sorted(k for k in lp_u if k <= last_date)
    for i, entry in enumerate(ic.get_price_history()):
        assert entry['spot_price'] == lp_u[keys[i]].get('spot_price')


def test_price_history_pnl_is_zero_at_open_bar(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    assert ic.get_price_history()[0]['pnl'] == pytest.approx(0.0, abs=1.0)


def test_price_history_pnl_pct_is_zero_at_open_bar(make_iron_condor):
    ic = make_iron_condor(fill_factor=1.0)
    ic._open_trade()
    assert ic.get_price_history()[0]['pnl_pct'] == pytest.approx(0.0, abs=0.01)


def test_price_history_long_iron_condor_has_required_keys(make_iron_condor):
    ic = make_iron_condor(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ic._open_trade()
    for entry in ic.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_long_iron_condor_price_formula(make_iron_condor):
    ic = make_iron_condor(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ic._open_trade()
    lp_u = ic.lower_put.updates
    up_u = ic.upper_put.updates
    lc_u = ic.lower_call.updates
    uc_u = ic.upper_call.updates
    last_date = ic.lower_put.quote_datetime
    keys = sorted(k for k in lp_u if k <= last_date)

    for i, entry in enumerate(ic.get_price_history()):
        k = keys[i]
        expected = (lp_u[k]['price'] + uc_u[k]['price']) - (up_u[k]['price'] + lc_u[k]['price'])
        assert entry['price'] == pytest.approx(expected, abs=0.01)