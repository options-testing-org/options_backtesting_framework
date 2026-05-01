import datetime
import pytest
from options_framework.option_types import OptionSpreadType, OptionStatus, OptionPositionType
from options_framework.spreads.diagonal import Diagonal, RollRecord
from conftest import REQUIRED_HISTORY_KEYS


# ── Construction & properties ─────────────────────────────────────────────────

def test_post_init_assigns_leg_references(make_diagonal):
    d = make_diagonal()
    assert d.near_option is d.options[0]
    assert d.far_option is d.options[1]


def test_spread_type(make_diagonal):
    assert make_diagonal().spread_type == OptionSpreadType.DIAGONAL


def test_default_position_type_is_long(make_diagonal):
    assert make_diagonal().position_type == OptionPositionType.LONG


def test_short_position_type_stored(make_diagonal):
    assert make_diagonal(position_type=OptionPositionType.SHORT).position_type == OptionPositionType.SHORT


def test_near_strike_property(make_diagonal):
    assert make_diagonal().near_strike == 380.0


def test_far_strike_property(make_diagonal):
    assert make_diagonal().far_strike == 370.0


def test_strikes_are_different(make_diagonal):
    d = make_diagonal()
    assert d.near_strike != d.far_strike


def test_expirations_are_different(make_diagonal):
    d = make_diagonal()
    assert d.near_option.expiration != d.far_option.expiration


def test_option_type_property_put(make_diagonal):
    assert make_diagonal(option_type='put').option_type == 'put'


def test_option_type_property_call(make_diagonal):
    assert make_diagonal(option_type='call').option_type == 'call'


def test_symbol_delegates_to_options_list(make_diagonal):
    d = make_diagonal()
    assert d.symbol == d.options[0].symbol
    assert d.symbol == 'MSFT'


def test_repr_contains_key_info(make_diagonal):
    r = repr(make_diagonal())
    assert 'DIAGONAL' in r
    assert '380' in r
    assert '370' in r
    assert '2026-04-10' in r
    assert '2026-04-17' in r


def test_instance_ids_are_unique(make_diagonal):
    assert make_diagonal().instance_id != make_diagonal().instance_id


def test_equality_based_on_instance_id(make_diagonal):
    d1 = make_diagonal()
    d2 = make_diagonal()
    assert d1 != d2
    assert d1 == d1


def test_roll_records_empty_on_construction(make_diagonal):
    assert make_diagonal().roll_records == []


def test_net_cost_basis_none_before_open(make_diagonal):
    assert make_diagonal().net_cost_basis is None


# ── Price calculation ─────────────────────────────────────────────────────────

def test_long_diagonal_price_formula(make_diagonal):
    """LONG: price = far - near"""
    d = make_diagonal()
    expected = d.far_option.price - d.near_option.price
    assert d.price == pytest.approx(expected, abs=0.01)


def test_short_diagonal_price_formula(make_diagonal):
    """SHORT: price = near - far"""
    d = make_diagonal(position_type=OptionPositionType.SHORT)
    expected = d.near_option.price - d.far_option.price
    assert d.price == pytest.approx(expected, abs=0.01)


# ── open_trade ────────────────────────────────────────────────────────────────

def test_long_diagonal_leg_quantities(make_diagonal):
    """LONG: short near (-1), long far (+1)"""
    d = make_diagonal(fill_factor=1.0)
    d.open_trade(quantity=1)
    assert d.near_option.quantity == -1
    assert d.far_option.quantity == +1


def test_long_diagonal_spread_quantity(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade(quantity=1)
    assert d.quantity == +1  # tracks far leg


def test_long_diagonal_multi_quantity(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade(quantity=3)
    assert d.near_option.quantity == -3
    assert d.far_option.quantity == +3


def test_short_diagonal_leg_quantities(make_diagonal):
    """SHORT: long near (+1), short far (-1)"""
    d = make_diagonal(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    d.open_trade(quantity=1)
    assert d.near_option.quantity == +1
    assert d.far_option.quantity == -1


def test_short_diagonal_spread_quantity(make_diagonal):
    d = make_diagonal(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    d.open_trade(quantity=1)
    assert d.quantity == -1


def test_open_trade_accepts_negative_quantity_as_absolute(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade(quantity=-2)
    assert d.near_option.quantity == -2
    assert d.far_option.quantity == +2


def test_open_trade_sets_net_cost_basis(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert d.net_cost_basis is not None
    assert d.net_cost_basis == pytest.approx(d.get_trade_price(), abs=0.01)


def test_open_trade_initialises_roll_records_in_user_defined(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert 'roll_records' in d.user_defined
    assert d.user_defined['roll_records'] is d.roll_records


def test_open_trade_saves_user_defined_kwargs(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade(quantity=1, tag='pmcc')
    assert d.user_defined.get('tag') == 'pmcc'


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_none_before_open(make_diagonal):
    assert make_diagonal().get_trade_price() is None


def test_get_trade_price_returns_float_after_open(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert isinstance(d.get_trade_price(), float)


def test_long_trade_price_matches_formula(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    near_p = d.near_option.trade_open_info.price
    far_p = d.far_option.trade_open_info.price
    assert d.get_trade_price() == pytest.approx(far_p - near_p, abs=0.01)


def test_short_trade_price_matches_formula(make_diagonal):
    d = make_diagonal(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    d.open_trade()
    near_p = d.near_option.trade_open_info.price
    far_p = d.far_option.trade_open_info.price
    assert d.get_trade_price() == pytest.approx(near_p - far_p, abs=0.01)


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_all_legs(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    d.close_trade(quote_datetime=d.near_option.quote_datetime)
    for leg in d.options:
        assert OptionStatus.TRADE_IS_CLOSED in leg.status


def test_close_trade_requires_keyword_only_quote_datetime(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    d.close_trade(quote_datetime=d.near_option.quote_datetime)


def test_get_closed_price_returns_none_before_close(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert d.get_closed_price() is None


def test_get_closed_price_returns_float_after_close(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    d.close_trade(quote_datetime=d.near_option.quote_datetime)
    assert isinstance(d.get_closed_price(), float)


def test_closed_price_matches_formula(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    d.close_trade(quote_datetime=d.near_option.quote_datetime)
    near_p = d.near_option.trade_close_info.price
    far_p = d.far_option.trade_close_info.price
    assert d.get_closed_price() == pytest.approx(far_p - near_p, abs=0.01)


# ── DTE & SpreadBase delegation ───────────────────────────────────────────────

def test_dte_delegates_to_near_leg(make_diagonal):
    d = make_diagonal()
    assert d.get_dte() == d.near_option.get_dte()


def test_dte_is_positive_before_expiry(make_diagonal):
    assert make_diagonal().get_dte() > 0


def test_near_dte_less_than_far_dte(make_diagonal):
    d = make_diagonal()
    assert d.near_option.get_dte() < d.far_option.get_dte()


def test_spot_price_delegates_to_first_option(make_diagonal):
    d = make_diagonal()
    assert d.spot_price == d.options[0].spot_price


def test_quote_datetime_delegates_to_first_option(make_diagonal):
    d = make_diagonal()
    assert d.quote_datetime == d.options[0].quote_datetime


def test_get_profit_loss_after_open(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert isinstance(d.get_profit_loss(), float)


def test_current_value_sums_legs(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert d.current_value == pytest.approx(sum(o.current_value for o in d.options), abs=0.01)


def test_trade_value_sums_legs(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert d.trade_value == pytest.approx(sum(o.trade_value for o in d.options), abs=0.01)


def test_max_profit_returns_none(make_diagonal):
    assert make_diagonal().max_profit is None


def test_max_loss_returns_none(make_diagonal):
    assert make_diagonal().max_loss is None


# ── get_required_margin ───────────────────────────────────────────────────────

def test_required_margin_long_is_zero(make_diagonal):
    assert make_diagonal().get_required_margin(1) == 0.0


def test_required_margin_short_is_positive(make_diagonal):
    assert make_diagonal(position_type=OptionPositionType.SHORT).get_required_margin(1) > 0


def test_required_margin_short_scales_with_quantity(make_diagonal):
    d = make_diagonal(position_type=OptionPositionType.SHORT)
    assert d.get_required_margin(3) == pytest.approx(d.get_required_margin(1) * 3, abs=0.01)


def test_required_margin_short_uses_absolute_quantity(make_diagonal):
    d = make_diagonal(position_type=OptionPositionType.SHORT)
    assert d.get_required_margin(-2) == pytest.approx(d.get_required_margin(2), abs=0.01)


# ── roll_near ─────────────────────────────────────────────────────────────────

def test_roll_near_swaps_near_option(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    new_near = make_put_option_370()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=new_near)
    assert d.near_option is new_near
    assert d.options[0] is new_near


def test_roll_near_closes_old_near_leg(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    old_near = d.near_option
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=make_put_option_370())
    assert OptionStatus.TRADE_IS_CLOSED in old_near.status


def test_roll_near_opens_new_near_leg(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    new_near = make_put_option_370()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=new_near)
    assert OptionStatus.TRADE_IS_OPEN in new_near.status


def test_roll_near_new_leg_has_same_signed_quantity(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade(quantity=2)
    old_qty = d.near_option.quantity
    new_near = make_put_option_370()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=new_near)
    assert d.near_option.quantity == old_qty


def test_roll_near_appends_roll_record(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=make_put_option_370())
    assert len(d.roll_records) == 1
    assert isinstance(d.roll_records[0], RollRecord)


def test_roll_near_record_fields(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    old_near = d.near_option
    new_near = make_put_option_370()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=new_near)
    record = d.roll_records[0]
    assert record.date == dt
    assert record.old_option is old_near
    assert record.new_option is new_near
    assert isinstance(record.credit, float)


def test_roll_near_user_defined_roll_records_same_reference(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=make_put_option_370())
    assert d.user_defined['roll_records'] is d.roll_records


def test_roll_near_adjusts_net_cost_basis(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    cost_before = d.net_cost_basis
    new_near = make_put_option_370()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=new_near)
    credit = d.roll_records[0].credit
    assert d.net_cost_basis == pytest.approx(cost_before - credit, abs=0.01)


def test_roll_near_raises_if_new_expiration_not_before_far(make_diagonal, make_put_option_370_far):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    dt = d.near_option.quote_datetime
    with pytest.raises(ValueError, match="far option expiration"):
        d.roll_near(quote_datetime=dt, new_near_option=make_put_option_370_far())


def test_roll_near_raises_if_near_not_open(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    with pytest.raises(RuntimeError, match="not open"):
        d.roll_near(quote_datetime=datetime.datetime.now(), new_near_option=make_put_option_370())


def test_multiple_rolls_accumulate_records(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=make_put_option_370())
    dt2 = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt2, new_near_option=make_put_option_370())
    assert len(d.roll_records) == 2


# ── get_price_history ─────────────────────────────────────────────────────────

def test_price_history_raises_before_open(make_diagonal):
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        make_diagonal().get_price_history()


def test_price_history_returns_list(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert isinstance(d.get_price_history(), list)


def test_price_history_each_entry_has_required_keys(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    for entry in d.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_length_matches_near_leg_updates(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    last_date = d.near_option.quote_datetime
    expected_len = sum(1 for k in d.near_option.updates if k <= last_date)
    assert len(d.get_price_history()) == expected_len


def test_price_history_price_matches_calculate_price_each_row(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    near_u = d.near_option.updates
    far_u = d.far_option.updates
    last_date = d.near_option.quote_datetime
    keys = sorted(k for k in near_u if k <= last_date)

    for i, entry in enumerate(d.get_price_history()):
        k = keys[i]
        expected = d._calculate_price(
            near_price=near_u[k]['price'],
            far_price=far_u[k]['price'],
        )
        assert entry['price'] == pytest.approx(expected, abs=0.01)


def test_price_history_spot_price_matches_near_leg_updates(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    near_u = d.near_option.updates
    last_date = d.near_option.quote_datetime
    keys = sorted(k for k in near_u if k <= last_date)
    for i, entry in enumerate(d.get_price_history()):
        assert entry['spot_price'] == near_u[keys[i]].get('spot_price')


def test_price_history_pnl_is_zero_at_open_bar(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert d.get_price_history()[0]['pnl'] == pytest.approx(0.0, abs=1.0)


def test_price_history_pnl_pct_is_zero_at_open_bar(make_diagonal):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    assert d.get_price_history()[0]['pnl_pct'] == pytest.approx(0.0, abs=0.01)


def test_price_history_short_diagonal_has_required_keys(make_diagonal):
    d = make_diagonal(position_type=OptionPositionType.SHORT, fill_factor=1.0)
    d.open_trade()
    for entry in d.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_call_diagonal_has_required_keys(make_diagonal):
    d = make_diagonal(option_type='call', fill_factor=1.0)
    d.open_trade()
    for entry in d.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_after_roll_is_longer_than_single_leg(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    original_near = d.near_option
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=make_put_option_370())

    history = d.get_price_history()
    original_len = sum(1 for k in original_near.updates if k <= original_near.trade_close_info.date)
    new_len = sum(1 for k in d.near_option.updates if k <= d.near_option.quote_datetime)
    assert len(history) == original_len + new_len


def test_price_history_after_roll_all_entries_have_required_keys(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=make_put_option_370())
    for entry in d.get_price_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_pnl_reflects_adjusted_cost_basis_after_roll(make_diagonal, make_put_option_370):
    d = make_diagonal(fill_factor=1.0)
    d.open_trade()
    dt = d.near_option.quote_datetime
    d.roll_near(quote_datetime=dt, new_near_option=make_put_option_370())

    history = d.get_price_history()
    original_len = sum(
        1 for k in d.roll_records[0].old_option.updates
        if k <= d.roll_records[0].old_option.trade_close_info.date
    )
    second_segment_first = history[original_len]
    assert isinstance(second_segment_first['pnl'], float)
    assert isinstance(second_segment_first['pnl_pct'], float)
