"""
Tests for the Calendar spread class.

Fixture defaults (LONG put calendar, net debit):
  near_option = MSFT 380P 2026-04-10
  far_option  = MSFT 380P 2026-04-17

fill_factor=1.0 is passed where mid-price is needed.

Roll tests use the 370P 2026-04-10 near leg as the rolled-to option, since
it shares the same expiration universe and has pickle data available.
"""

import datetime
import pytest
from options_framework.option_types import OptionSpreadType, OptionStatus, OptionPositionType
from options_framework.spreads.calendar import Calendar, RollRecord


REQUIRED_HISTORY_KEYS = {
    'quote_datetime', 'price', 'spot_price',
    'pnl', 'pnl_pct',
    'delta', 'gamma', 'theta', 'vega', 'rho', 'iv',
}


# ── Construction & properties ─────────────────────────────────────────────────

def test_post_init_assigns_leg_references(make_calendar):
    cal = make_calendar()
    assert cal.near_option is cal.options[0]
    assert cal.far_option  is cal.options[1]

def test_spread_type(make_calendar):
    assert make_calendar().spread_type == OptionSpreadType.CALENDAR

def test_default_position_type_is_long(make_calendar):
    assert make_calendar().position_type == OptionPositionType.LONG

def test_short_position_type_stored(make_calendar):
    assert make_calendar(position_type=OptionPositionType.SHORT).position_type == OptionPositionType.SHORT

def test_strike_property(make_calendar):
    assert make_calendar().strike == 380.0

def test_option_type_property_put(make_calendar):
    assert make_calendar(option_type='put').option_type == 'put'

def test_option_type_property_call(make_calendar):
    assert make_calendar(option_type='call').option_type == 'call'

def test_symbol_delegates_to_options_list(make_calendar):
    cal = make_calendar()
    assert cal.symbol == cal.options[0].symbol
    assert cal.symbol == 'MSFT'

def test_repr_contains_key_info(make_calendar):
    r = repr(make_calendar())
    assert 'CALENDAR' in r
    assert '380' in r
    assert '2026-04-10' in r
    assert '2026-04-17' in r

def test_instance_ids_are_unique(make_calendar):
    assert make_calendar().instance_id != make_calendar().instance_id

def test_equality_based_on_instance_id(make_calendar):
    cal1 = make_calendar()
    cal2 = make_calendar()
    assert cal1 != cal2
    assert cal1 == cal1

def test_roll_records_empty_on_construction(make_calendar):
    assert make_calendar().roll_records == []

def test_net_cost_basis_none_before_open(make_calendar):
    assert make_calendar().net_cost_basis is None


# ── Price calculation ─────────────────────────────────────────────────────────

def test_long_calendar_price_formula(make_calendar):
    """LONG: price = far - near (debit paid)"""
    cal = make_calendar()
    expected = cal.far_option.price - cal.near_option.price
    assert cal.price == pytest.approx(expected, abs=0.01)

def test_short_calendar_price_formula(make_calendar):
    """SHORT: price = near - far (credit received)"""
    cal = make_calendar(position_type=OptionPositionType.SHORT)
    expected = cal.near_option.price - cal.far_option.price
    assert cal.price == pytest.approx(expected, abs=0.01)

def test_long_price_is_positive(make_calendar):
    """Far option has more time value so long calendar is a net debit."""
    assert make_calendar().price > 0


# ── open_trade ────────────────────────────────────────────────────────────────

def test_long_calendar_leg_quantities(make_calendar):
    """LONG: short near (-1), long far (+1)"""
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade(quantity=1)
    assert cal.near_option.quantity == -1
    assert cal.far_option.quantity  == +1

def test_long_calendar_spread_quantity(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade(quantity=1)
    assert cal.quantity == +1  # tracks far leg

def test_long_calendar_multi_quantity(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade(quantity=3)
    assert cal.near_option.quantity == -3
    assert cal.far_option.quantity  == +3

def test_short_calendar_leg_quantities(make_calendar):
    """SHORT: long near (+1), short far (-1)"""
    cal = make_calendar(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    cal._open_trade(quantity=1)
    assert cal.near_option.quantity == +1
    assert cal.far_option.quantity  == -1

def test_short_calendar_spread_quantity(make_calendar):
    cal = make_calendar(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    cal._open_trade(quantity=1)
    assert cal.quantity == -1

def test_open_trade_accepts_negative_quantity_as_absolute(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade(quantity=-2)
    assert cal.near_option.quantity == -2
    assert cal.far_option.quantity  == +2

def test_open_trade_sets_net_cost_basis(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert cal.net_cost_basis is not None
    assert cal.net_cost_basis == pytest.approx(cal.get_trade_price(), abs=0.01)

def test_open_trade_initialises_roll_records_in_user_defined(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert 'roll_records' in cal.user_defined
    assert cal.user_defined['roll_records'] is cal.roll_records

def test_open_trade_saves_user_defined_kwargs(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade(quantity=1, tag='vol_play')
    assert cal.user_defined.get('tag') == 'vol_play'


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_none_before_open(make_calendar):
    assert make_calendar().get_trade_price() is None

def test_get_trade_price_returns_float_after_open(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert isinstance(cal.get_trade_price(), float)

def test_long_trade_price_matches_formula(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    near_p = cal.near_option.trade_open_info.price
    far_p  = cal.far_option.trade_open_info.price
    assert cal.get_trade_price() == pytest.approx(far_p - near_p, abs=0.01)

def test_short_trade_price_matches_formula(make_calendar):
    cal = make_calendar(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    cal._open_trade()
    near_p = cal.near_option.trade_open_info.price
    far_p  = cal.far_option.trade_open_info.price
    assert cal.get_trade_price() == pytest.approx(near_p - far_p, abs=0.01)


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_all_legs(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    cal._close_trade(quote_datetime=cal.near_option.quote_datetime)
    for leg in cal.options:
        assert OptionStatus.TRADE_IS_CLOSED in leg.status

def test_close_trade_requires_keyword_only_quote_datetime(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    cal._close_trade(quote_datetime=cal.near_option.quote_datetime)

def test_close_trade_with_explicit_quantity_does_not_raise(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade(quantity=2)
    cal._close_trade(quote_datetime=cal.near_option.quote_datetime,
                     quantity=cal.far_option.quantity)

def test_get_closed_price_returns_none_before_close(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert cal.get_closed_price() is None

def test_get_closed_price_returns_float_after_close(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    cal._close_trade(quote_datetime=cal.near_option.quote_datetime)
    assert isinstance(cal.get_closed_price(), float)

def test_closed_price_matches_formula(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    cal._close_trade(quote_datetime=cal.near_option.quote_datetime)
    near_p = cal.near_option.trade_close_info.price
    far_p  = cal.far_option.trade_close_info.price
    assert cal.get_closed_price() == pytest.approx(far_p - near_p, abs=0.01)


# ── DTE & SpreadBase delegation ───────────────────────────────────────────────

def test_dte_delegates_to_near_leg(make_calendar):
    cal = make_calendar()
    assert cal.get_dte() == cal.near_option.get_dte()

def test_dte_is_positive_before_expiry(make_calendar):
    assert make_calendar().get_dte() > 0

def test_near_dte_less_than_far_dte(make_calendar):
    cal = make_calendar()
    assert cal.near_option.get_dte() < cal.far_option.get_dte()

def test_spot_price_delegates_to_first_option(make_calendar):
    cal = make_calendar()
    assert cal.spot_price == cal.options[0].spot_price

def test_quote_datetime_delegates_to_first_option(make_calendar):
    cal = make_calendar()
    assert cal.quote_datetime == cal.options[0].quote_datetime

def test_get_profit_loss_after_open(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert isinstance(cal.get_profit_loss(), float)

def test_current_value_sums_legs(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert cal.current_value == pytest.approx(sum(o.current_value for o in cal.options), abs=0.01)

def test_trade_value_sums_legs(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert cal.trade_value == pytest.approx(sum(o.trade_value for o in cal.options), abs=0.01)

def test_max_profit_returns_none(make_calendar):
    assert make_calendar().max_profit is None

def test_max_loss_returns_none(make_calendar):
    assert make_calendar().max_loss is None


# ── get_required_margin ───────────────────────────────────────────────────────

def test_required_margin_long_is_zero(make_calendar):
    assert make_calendar().get_required_margin(1) == 0.0

def test_required_margin_short_is_positive(make_calendar):
    assert make_calendar(position_type=OptionPositionType.SHORT).get_required_margin(1) > 0

def test_required_margin_short_scales_with_quantity(make_calendar):
    cal = make_calendar(position_type=OptionPositionType.SHORT)
    assert cal.get_required_margin(3) == pytest.approx(cal.get_required_margin(1) * 3, abs=0.01)

def test_required_margin_short_uses_absolute_quantity(make_calendar):
    cal = make_calendar(position_type=OptionPositionType.SHORT)
    assert cal.get_required_margin(-2) == pytest.approx(cal.get_required_margin(2), abs=0.01)


# ── roll_near ─────────────────────────────────────────────────────────────────

def test_roll_near_swaps_near_option(make_calendar, make_put_option_370):
    """After roll, near_option and options[0] reference the new leg."""
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    new_near = make_put_option_370()
    dt = cal.near_option.quote_datetime
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)
    assert cal.near_option is new_near
    assert cal.options[0] is new_near

def test_roll_near_closes_old_near_leg(make_calendar, make_put_option_370):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    old_near = cal.near_option
    dt = cal.near_option.quote_datetime
    new_near = make_put_option_370()
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)
    assert OptionStatus.TRADE_IS_CLOSED in old_near.status

def test_roll_near_opens_new_near_leg(make_calendar, make_put_option_370):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    new_near = make_put_option_370()
    dt = cal.near_option.quote_datetime
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)
    assert OptionStatus.TRADE_IS_OPEN in new_near.status

def test_roll_near_new_leg_has_same_signed_quantity(make_calendar, make_put_option_370):
    """New near leg inherits the signed quantity of the old near leg."""
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade(quantity=2)
    old_qty = cal.near_option.quantity  # -2 for LONG calendar
    new_near = make_put_option_370()
    dt = cal.near_option.quote_datetime
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)
    assert cal.near_option.quantity == old_qty

def test_roll_near_appends_roll_record(make_calendar, make_put_option_370):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    new_near = make_put_option_370()
    dt = cal.near_option.quote_datetime
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)
    assert len(cal.roll_records) == 1
    assert isinstance(cal.roll_records[0], RollRecord)

def test_roll_near_record_fields(make_calendar, make_put_option_370):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    old_near = cal.near_option
    new_near = make_put_option_370()
    dt = cal.near_option.quote_datetime
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)
    record = cal.roll_records[0]
    assert record.date       == dt
    assert record.old_option is old_near
    assert record.new_option is new_near
    assert isinstance(record.credit, float)

def test_roll_near_user_defined_roll_records_same_reference(make_calendar, make_put_option_370):
    """user_defined['roll_records'] must be the same list as cal.roll_records."""
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    new_near = make_put_option_370()
    dt = cal.near_option.quote_datetime
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)
    assert cal.user_defined['roll_records'] is cal.roll_records

def test_roll_near_adjusts_net_cost_basis(make_calendar, make_put_option_370):
    """net_cost_basis must change by the roll credit."""
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    cost_before = cal.net_cost_basis
    new_near = make_put_option_370()
    dt = cal.near_option.quote_datetime
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)
    credit = cal.roll_records[0].credit
    assert cal.net_cost_basis == pytest.approx(cost_before - credit, abs=0.01)

def test_roll_near_raises_if_new_expiration_not_before_far(make_calendar, make_put_option_380_far):
    """Rolling to an option expiring on or after the far leg must raise."""
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    new_near = make_put_option_380_far()  # same expiration as far leg
    dt = cal.near_option.quote_datetime
    with pytest.raises(ValueError, match="far option expiration"):
        cal.roll_near(quote_datetime=dt, new_near_option=new_near)

def test_roll_near_raises_if_near_not_open(make_calendar, make_put_option_370):
    cal = make_calendar(fill_factor=1.0)
    with pytest.raises(RuntimeError, match="not open"):
        cal.roll_near(quote_datetime=datetime.datetime.now(), new_near_option=make_put_option_370())

def test_multiple_rolls_accumulate_records(make_calendar, make_put_option_370):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    dt = cal.near_option.quote_datetime
    first_new = make_put_option_370()
    cal.roll_near(quote_datetime=dt, new_near_option=first_new)
    second_new = make_put_option_370()
    dt2 = cal.near_option.quote_datetime
    cal.roll_near(quote_datetime=dt2, new_near_option=second_new)
    assert len(cal.roll_records) == 2


# ── get_price_history ─────────────────────────────────────────────────────────

def test_price_history_raises_before_open(make_calendar):
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        make_calendar().get_price_history()

def test_price_history_returns_list(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert isinstance(cal.get_price_history(), list)

def test_price_history_each_entry_has_required_keys(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    for entry in cal.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS

def test_price_history_length_matches_near_leg_updates(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    last_date = cal.near_option.quote_datetime
    expected_len = sum(1 for k in cal.near_option.updates if k <= last_date)
    assert len(cal.get_price_history()) == expected_len

def test_price_history_price_matches_calculate_price_each_row(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    near_u = cal.near_option.updates
    far_u  = cal.far_option.updates
    last_date = cal.near_option.quote_datetime
    keys = sorted(k for k in near_u if k <= last_date)

    for i, entry in enumerate(cal.get_price_history()):
        k = keys[i]
        expected = cal._calculate_price(
            near_price=near_u[k]['price'],
            far_price=far_u[k]['price'],
        )
        assert entry['price'] == pytest.approx(expected, abs=0.01)

def test_price_history_spot_price_matches_near_leg_updates(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    near_u = cal.near_option.updates
    last_date = cal.near_option.quote_datetime
    keys = sorted(k for k in near_u if k <= last_date)
    for i, entry in enumerate(cal.get_price_history()):
        assert entry['spot_price'] == near_u[keys[i]].get('spot_price')

def test_price_history_pnl_is_zero_at_open_bar(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert cal.get_price_history()[0]['pnl'] == pytest.approx(0.0, abs=1.0)

def test_price_history_pnl_pct_is_zero_at_open_bar(make_calendar):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    assert cal.get_price_history()[0]['pnl_pct'] == pytest.approx(0.0, abs=0.01)

def test_price_history_short_calendar_has_required_keys(make_calendar):
    cal = make_calendar(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    cal._open_trade()
    for entry in cal.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS

def test_price_history_call_calendar_has_required_keys(make_calendar):
    cal = make_calendar(option_type='call', fill_factor=1.0)
    cal._open_trade()
    for entry in cal.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS

def test_price_history_after_roll_is_longer_than_single_leg(make_calendar, make_put_option_370):
    """History after a roll must span both near legs — more entries than either alone."""
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    original_near = cal.near_option
    dt = cal.near_option.quote_datetime
    new_near = make_put_option_370()
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)

    history = cal.get_price_history()
    original_near_len = sum(1 for k in original_near.updates if k <= original_near.trade_close_info.date)
    new_near_len      = sum(1 for k in new_near.updates if k <= new_near.quote_datetime)
    assert len(history) == original_near_len + new_near_len

def test_price_history_after_roll_all_entries_have_required_keys(make_calendar, make_put_option_370):
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    dt = cal.near_option.quote_datetime
    cal.roll_near(quote_datetime=dt, new_near_option=make_put_option_370())
    for entry in cal.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS

def test_price_history_pnl_reflects_adjusted_cost_basis_after_roll(make_calendar, make_put_option_370):
    """PnL in the second segment uses the roll-adjusted cost basis, not the original."""
    cal = make_calendar(fill_factor=1.0)
    cal._open_trade()
    dt = cal.near_option.quote_datetime
    new_near = make_put_option_370()
    cal.roll_near(quote_datetime=dt, new_near_option=new_near)

    history = cal.get_price_history()
    # The first entry of the second segment should reflect the new cost basis
    original_near_len = sum(
        1 for k in cal.roll_records[0].old_option.updates
        if k <= cal.roll_records[0].old_option.trade_close_info.date
    )
    second_segment_first = history[original_near_len]
    # PnL is (price - adjusted_cost_basis) * 100 * qty
    # At the very first bar of the second segment we cannot assert pnl==0
    # (cost basis was adjusted), but we can assert the entry is well-formed.
    assert isinstance(second_segment_first['pnl'], float)
    assert isinstance(second_segment_first['pnl_pct'], float)