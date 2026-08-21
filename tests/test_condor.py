"""
Tests for the Condor spread class.

Fixture defaults (LONG PUT condor, net debit):
  lower        = MSFT 370P 2026-04-10
  lower_middle = MSFT 380P 2026-04-10
  upper_middle = MSFT 390P 2026-04-10
  upper        = MSFT 400P 2026-04-10

fill_factor=1.0 is passed where mid-price is needed.
"""

import datetime
import pytest
from options_framework.option_types import OptionSpreadType, OptionStatus, OptionPositionType
from options_framework.spreads.condor import Condor
from conftest import REQUIRED_HISTORY_KEYS

# ── Construction & properties ─────────────────────────────────────────────────

def test_post_init_assigns_leg_references(make_condor):
    c = make_condor()
    assert c.lower_option        is c.options[0]
    assert c.lower_middle_option is c.options[1]
    assert c.upper_middle_option is c.options[2]
    assert c.upper_option        is c.options[3]

def test_spread_type(make_condor):
    assert make_condor().spread_type == OptionSpreadType.CONDOR

def test_default_position_type_is_long(make_condor):
    assert make_condor().position_type == OptionPositionType.LONG

def test_short_position_type_stored(make_condor):
    assert make_condor(position_type=OptionPositionType.SHORT).position_type == OptionPositionType.SHORT

def test_option_type_property(make_condor):
    assert make_condor().option_type == 'put'

def test_expiration_property(make_condor):
    assert make_condor().expiration == datetime.date(2026, 4, 10)

def test_symbol_delegates_to_options_list(make_condor):
    c = make_condor()
    assert c.symbol == c.options[0].symbol
    assert c.symbol == 'MSFT'

def test_repr_contains_all_strikes(make_condor):
    r = repr(make_condor())
    assert 'CONDOR' in r
    assert '370' in r
    assert '380' in r
    assert '390' in r
    assert '400' in r

def test_instance_ids_are_unique(make_condor):
    assert make_condor().instance_id != make_condor().instance_id

def test_equality_based_on_instance_id(make_condor):
    c1 = make_condor()
    c2 = make_condor()
    assert c1 != c2
    assert c1 == c1


# ── Price calculation ─────────────────────────────────────────────────────────

def test_long_condor_price_formula(make_condor):
    """LONG: price = (lower + upper) - (lower_middle + upper_middle)"""
    c = make_condor()
    expected = (c.lower_option.price + c.upper_option.price) - (c.lower_middle_option.price + c.upper_middle_option.price)
    assert c.price == pytest.approx(expected, abs=0.01)

def test_short_condor_price_formula(make_condor):
    """SHORT: price = (lower_middle + upper_middle) - (lower + upper)"""
    c = make_condor(position_type=OptionPositionType.SHORT)
    expected = (c.lower_middle_option.price + c.upper_middle_option.price) - (c.lower_option.price + c.upper_option.price)
    assert c.price == pytest.approx(expected, abs=0.01)

# ── open_trade ────────────────────────────────────────────────────────────────

def test_long_condor_leg_quantities(make_condor):
    """LONG: buy wings (+1), sell body (-1)"""
    c = make_condor(fill_factor=1.0)
    c._open_trade(quantity=1)
    assert c.lower_option.quantity        == +1
    assert c.lower_middle_option.quantity == -1
    assert c.upper_middle_option.quantity == -1
    assert c.upper_option.quantity        == +1

def test_long_condor_spread_quantity(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade(quantity=1)
    assert c.quantity == +1  # tracks lower leg

def test_long_condor_multi_quantity(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade(quantity=3)
    assert c.lower_option.quantity        == +3
    assert c.lower_middle_option.quantity == -3
    assert c.upper_middle_option.quantity == -3
    assert c.upper_option.quantity        == +3

def test_short_condor_leg_quantities(make_condor):
    """SHORT: sell wings (-1), buy body (+1)"""
    c = make_condor(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    c._open_trade(quantity=1)
    assert c.lower_option.quantity        == -1
    assert c.lower_middle_option.quantity == +1
    assert c.upper_middle_option.quantity == +1
    assert c.upper_option.quantity        == -1

def test_short_condor_spread_quantity(make_condor):
    c = make_condor(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    c._open_trade(quantity=1)
    assert c.quantity == -1

def test_open_trade_accepts_negative_quantity_as_absolute(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade(quantity=-2)
    assert c.lower_option.quantity        == +2
    assert c.lower_middle_option.quantity == -2

def test_open_trade_saves_user_defined_kwargs(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade(quantity=1, tag='test')
    assert c.user_defined.get('tag') == 'test'


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_none_before_open(make_condor):
    assert make_condor().get_trade_price() is None

def test_get_trade_price_returns_float_after_open(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    assert isinstance(c.get_trade_price(), float)

def test_long_trade_price_matches_formula(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    lp  = c.lower_option.trade_open_info.price
    lmp = c.lower_middle_option.trade_open_info.price
    ump = c.upper_middle_option.trade_open_info.price
    up  = c.upper_option.trade_open_info.price
    assert c.get_trade_price() == pytest.approx((lp + up) - (lmp + ump), abs=0.01)

def test_short_trade_price_matches_formula(make_condor):
    c = make_condor(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    c._open_trade()
    lp  = c.lower_option.trade_open_info.price
    lmp = c.lower_middle_option.trade_open_info.price
    ump = c.upper_middle_option.trade_open_info.price
    up  = c.upper_option.trade_open_info.price
    assert c.get_trade_price() == pytest.approx((lmp + ump) - (lp + up), abs=0.01)


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_all_legs(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    c._close_trade(quote_datetime=c.lower_option.quote_datetime)
    for leg in c.options:
        assert OptionStatus.TRADE_IS_CLOSED in leg.status

def test_close_trade_requires_keyword_only_quote_datetime(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    c._close_trade(quote_datetime=c.lower_option.quote_datetime)  # must not raise

def test_close_trade_with_explicit_quantity_does_not_raise(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade(quantity=2)
    c._close_trade(quote_datetime=c.lower_option.quote_datetime,
                   quantity=c.lower_option.quantity)

def test_get_closed_price_returns_none_before_close(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    assert c.get_closed_price() is None

def test_get_closed_price_returns_float_after_close(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    c._close_trade(quote_datetime=c.lower_option.quote_datetime)
    assert isinstance(c.get_closed_price(), float)

def test_closed_price_matches_formula(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    c._close_trade(quote_datetime=c.lower_option.quote_datetime)
    lp  = c.lower_option.trade_close_info.price
    lmp = c.lower_middle_option.trade_close_info.price
    ump = c.upper_middle_option.trade_close_info.price
    up  = c.upper_option.trade_close_info.price
    assert c.get_closed_price() == pytest.approx((lp + up) - (lmp + ump), abs=0.01)


# ── DTE & SpreadBase delegation ───────────────────────────────────────────────

def test_dte_delegates_to_lower_leg(make_condor):
    c = make_condor()
    assert c.get_dte() == c.lower_option.get_dte()

def test_dte_is_positive_before_expiry(make_condor):
    assert make_condor().get_dte() > 0

def test_spot_price_delegates_to_first_option(make_condor):
    c = make_condor()
    assert c.spot_price == c.options[0].spot_price

def test_quote_datetime_delegates_to_first_option(make_condor):
    c = make_condor()
    assert c.quote_datetime == c.options[0].quote_datetime

def test_get_profit_loss_after_open(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    assert isinstance(c.get_profit_loss(), float)

def test_current_value_sums_legs(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    assert c.current_value == pytest.approx(sum(o.current_value for o in c.options), abs=0.01)

def test_trade_value_sums_legs(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    assert c.trade_value == pytest.approx(sum(o.trade_value for o in c.options), abs=0.01)


# ── max_profit, max_loss, get_required_margin ─────────────────────────────────

def test_max_profit_returns_none_before_open(make_condor):
    assert make_condor().max_profit is None

def test_max_loss_returns_none_before_open(make_condor):
    assert make_condor().max_loss is None

def test_long_max_profit_equals_wing_width_minus_debit(make_condor):
    """LONG: max profit = wing_width - trade_price"""
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    wing_width = min(
        c.lower_middle_option.strike - c.lower_option.strike,
        c.upper_option.strike - c.upper_middle_option.strike,
    )
    assert c.max_profit == pytest.approx(wing_width - c.get_trade_price(), abs=0.01)

def test_long_max_loss_equals_trade_price(make_condor):
    """LONG: max loss is the net debit paid."""
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    assert c.max_loss == pytest.approx(c.get_trade_price(), abs=0.01)

def test_short_max_profit_equals_trade_price(make_condor):
    """SHORT: max profit is the net credit received."""
    c = make_condor(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    c._open_trade()
    assert c.max_profit == pytest.approx(c.get_trade_price(), abs=0.01)

def test_short_max_loss_equals_wing_width_minus_credit(make_condor):
    """SHORT: max loss = wing_width - net credit."""
    c = make_condor(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    c._open_trade()
    wing_width = min(
        c.lower_middle_option.strike - c.lower_option.strike,
        c.upper_option.strike - c.upper_middle_option.strike,
    )
    assert c.max_loss == pytest.approx(wing_width - c.get_trade_price(), abs=0.01)

def test_max_profit_plus_max_loss_equals_wing_width(make_condor):
    """max_profit + max_loss must always equal the wing width."""
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    wing_width = min(
        c.lower_middle_option.strike - c.lower_option.strike,
        c.upper_option.strike - c.upper_middle_option.strike,
    )
    assert c.max_profit + c.max_loss == pytest.approx(wing_width, abs=0.01)

def test_required_margin_long_is_zero(make_condor):
    assert make_condor().get_required_margin(1) == 0.0

def test_required_margin_short_is_positive(make_condor):
    assert make_condor(position_type=OptionPositionType.SHORT).get_required_margin(1) > 0

def test_required_margin_short_formula(make_condor):
    c = make_condor(position_type=OptionPositionType.SHORT)
    wing_width = min(
        c.lower_middle_option.strike - c.lower_option.strike,
        c.upper_option.strike - c.upper_middle_option.strike,
    )
    expected = (wing_width - c.price) * 100 * 1
    assert c.get_required_margin(1) == pytest.approx(expected, abs=1.0)

def test_required_margin_scales_with_quantity(make_condor):
    c = make_condor(position_type=OptionPositionType.SHORT)
    assert c.get_required_margin(3) == pytest.approx(c.get_required_margin(1) * 3, abs=0.01)

def test_required_margin_uses_absolute_quantity(make_condor):
    c = make_condor(position_type=OptionPositionType.SHORT)
    assert c.get_required_margin(-2) == pytest.approx(c.get_required_margin(2), abs=0.01)


# ── get_price_history ─────────────────────────────────────────────────────────

def test_price_history_raises_before_open(make_condor):
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        make_condor().get_history()

def test_price_history_returns_list(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    assert isinstance(c.get_history(), list)

def test_price_history_each_entry_has_required_keys(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    for entry in c.get_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS

def test_price_history_length_matches_lower_leg_updates(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    last_date = c.lower_option.quote_datetime
    expected_len = sum(1 for k in c.lower_option.updates if k <= last_date)
    assert len(c.get_history()) == expected_len

def test_price_history_price_matches_calculate_price_each_row(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    l_u  = c.lower_option.updates
    lm_u = c.lower_middle_option.updates
    um_u = c.upper_middle_option.updates
    u_u  = c.upper_option.updates
    last_date = c.lower_option.quote_datetime
    keys = sorted(k for k in l_u if k <= last_date)

    for i, entry in enumerate(c.get_history()):
        k = keys[i]
        expected = c._calculate_price(
            lower_price=l_u[k]['price'],
            lower_middle_price=lm_u[k]['price'],
            upper_middle_price=um_u[k]['price'],
            upper_price=u_u[k]['price'],
        )
        assert entry['price'] == pytest.approx(expected, abs=0.01)

def test_price_history_spot_price_matches_lower_leg_updates(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    l_u = c.lower_option.updates
    last_date = c.lower_option.quote_datetime
    keys = sorted(k for k in l_u if k <= last_date)
    for i, entry in enumerate(c.get_history()):
        assert entry['spot_price'] == l_u[keys[i]].get('spot_price')

def test_price_history_pnl_is_zero_at_open_bar(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    assert c.get_history()[0]['pnl'] == pytest.approx(0.0, abs=1.0)

def test_price_history_pnl_pct_is_zero_at_open_bar(make_condor):
    c = make_condor(fill_factor=1.0)
    c._open_trade()
    assert c.get_history()[0]['pnl_pct'] == pytest.approx(0.0, abs=0.01)

def test_price_history_short_condor_has_required_keys(make_condor):
    c = make_condor(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    c._open_trade()
    for entry in c.get_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS

def test_price_history_short_condor_price_formula(make_condor):
    c = make_condor(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    c._open_trade()
    l_u  = c.lower_option.updates
    lm_u = c.lower_middle_option.updates
    um_u = c.upper_middle_option.updates
    u_u  = c.upper_option.updates
    last_date = c.lower_option.quote_datetime
    keys = sorted(k for k in l_u if k <= last_date)

    for i, entry in enumerate(c.get_history()):
        k = keys[i]
        expected = (lm_u[k]['price'] + um_u[k]['price']) - (l_u[k]['price'] + u_u[k]['price'])
        assert entry['price'] == pytest.approx(expected, abs=0.01)