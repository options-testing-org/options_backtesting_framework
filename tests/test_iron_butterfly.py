import datetime
import pytest
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from conftest import REQUIRED_HISTORY_KEYS

# ── Construction & properties ─────────────────────────────────────────────────

def test_post_init_assigns_leg_references(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.lower_put is ib.options[0]
    assert ib.center_put is ib.options[1]
    assert ib.center_call is ib.options[2]
    assert ib.upper_call is ib.options[3]


def test_spread_type(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.spread_type == OptionSpreadType.IRON_BUTTERFLY


def test_default_position_type_is_short(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.position_type == OptionPositionType.SHORT


def test_long_position_type_stored(make_iron_butterfly):
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG)
    assert ib.position_type == OptionPositionType.LONG


def test_expiration_property(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.expiration == datetime.date(2026, 4, 10)


def test_center_strike_property(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.center_strike == 380.0


def test_symbol_delegates_to_options_list(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.symbol == ib.options[0].symbol
    assert ib.symbol == 'MSFT'


def test_repr_contains_key_info(make_iron_butterfly):
    ib = make_iron_butterfly()
    r = repr(ib)
    assert 'IRON_BUTTERFLY' in r
    assert '370' in r
    assert '380' in r
    assert '390' in r


def test_instance_ids_are_unique(make_iron_butterfly):
    ib1 = make_iron_butterfly()
    ib2 = make_iron_butterfly()
    assert ib1.instance_id != ib2.instance_id


def test_equality_based_on_instance_id(make_iron_butterfly):
    ib1 = make_iron_butterfly()
    ib2 = make_iron_butterfly()
    assert ib1 != ib2
    assert ib1 == ib1


# ── Price calculation ─────────────────────────────────────────────────────────

def test_short_iron_butterfly_price_formula(make_iron_butterfly):
    """SHORT: price = (center_put + center_call) - (lower_put + upper_call)"""
    ib = make_iron_butterfly()
    expected = (ib.center_put.price + ib.center_call.price) - (ib.lower_put.price + ib.upper_call.price)
    assert ib.price == pytest.approx(expected, abs=0.01)


def test_long_iron_butterfly_price_formula(make_iron_butterfly):
    """LONG: price = (lower_put + upper_call) - (center_put + center_call)"""
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG)
    expected = (ib.lower_put.price + ib.upper_call.price) - (ib.center_put.price + ib.center_call.price)
    assert ib.price == pytest.approx(expected, abs=0.01)


def test_short_price_is_non_negative(make_iron_butterfly):
    """A short iron butterfly on a normal vol surface collects net credit (positive price)."""
    ib = make_iron_butterfly()
    assert ib.price >= 0


# ── open_trade ────────────────────────────────────────────────────────────────

def test_short_iron_butterfly_leg_quantities(make_iron_butterfly):
    """SHORT: long wings (+1), short center legs (-1)"""
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade(quantity=1)
    assert ib.lower_put.quantity == +1
    assert ib.center_put.quantity == -1
    assert ib.center_call.quantity == -1
    assert ib.upper_call.quantity == +1


def test_short_iron_butterfly_spread_quantity(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade(quantity=1)
    assert ib.quantity == +1  # tracks lower_put leg


def test_short_iron_butterfly_multi_quantity(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade(quantity=3)
    assert ib.lower_put.quantity == +3
    assert ib.center_put.quantity == -3
    assert ib.center_call.quantity == -3
    assert ib.upper_call.quantity == +3


def test_long_iron_butterfly_leg_quantities(make_iron_butterfly):
    """LONG: short wings (-1), long center legs (+1)"""
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ib._open_trade(quantity=1)
    assert ib.lower_put.quantity == -1
    assert ib.center_put.quantity == +1
    assert ib.center_call.quantity == +1
    assert ib.upper_call.quantity == -1


def test_long_iron_butterfly_spread_quantity(make_iron_butterfly):
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ib._open_trade(quantity=1)
    assert ib.quantity == -1  # tracks lower_put leg


def test_open_trade_accepts_negative_quantity_as_absolute(make_iron_butterfly):
    """open_trade uses abs(quantity) — sign comes from position_type."""
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade(quantity=-2)
    assert ib.lower_put.quantity == +2
    assert ib.center_put.quantity == -2
    assert ib.center_call.quantity == -2
    assert ib.upper_call.quantity == +2


def test_open_trade_saves_user_defined_kwargs(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade(quantity=1, strategy='income')
    assert ib.user_defined.get('strategy') == 'income'


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_none_before_open(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.get_trade_price() is None


def test_get_trade_price_returns_float_after_open(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    assert isinstance(ib.get_trade_price(), float)


def test_short_trade_price_matches_formula(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    lp = ib.lower_put.trade_open_info.price
    cp = ib.center_put.trade_open_info.price
    cc = ib.center_call.trade_open_info.price
    uc = ib.upper_call.trade_open_info.price
    assert ib.get_trade_price() == pytest.approx((cp + cc) - (lp + uc), abs=0.01)


def test_long_trade_price_matches_formula(make_iron_butterfly):
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ib._open_trade()
    lp = ib.lower_put.trade_open_info.price
    cp = ib.center_put.trade_open_info.price
    cc = ib.center_call.trade_open_info.price
    uc = ib.upper_call.trade_open_info.price
    assert ib.get_trade_price() == pytest.approx((lp + uc) - (cp + cc), abs=0.01)


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_all_legs(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    ib._close_trade(quote_datetime=ib.center_put.quote_datetime)
    for leg in ib.options:
        assert OptionStatus.TRADE_IS_CLOSED in leg.status


def test_close_trade_requires_keyword_only_quote_datetime(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    ib._close_trade(quote_datetime=ib.center_put.quote_datetime)  # must not raise


def test_close_trade_with_explicit_quantity_does_not_raise(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade(quantity=2)
    ib._close_trade(quote_datetime=ib.center_put.quote_datetime,
                    quantity=ib.lower_put.quantity)


def test_get_closed_price_returns_none_before_close(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    assert ib.get_closed_price() is None


def test_get_closed_price_returns_float_after_close(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    ib._close_trade(quote_datetime=ib.center_put.quote_datetime)
    assert isinstance(ib.get_closed_price(), float)


def test_closed_price_matches_formula(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    ib._close_trade(quote_datetime=ib.center_put.quote_datetime)
    lp = ib.lower_put.trade_close_info.price
    cp = ib.center_put.trade_close_info.price
    cc = ib.center_call.trade_close_info.price
    uc = ib.upper_call.trade_close_info.price
    assert ib.get_closed_price() == pytest.approx((cp + cc) - (lp + uc), abs=0.01)


# ── DTE & SpreadBase delegation ───────────────────────────────────────────────

def test_dte_delegates_to_center_put(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.get_dte() == ib.center_put.get_dte()


def test_dte_is_positive_before_expiry(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.get_dte() > 0


def test_spot_price_delegates_to_first_option(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.spot_price == ib.options[0].spot_price


def test_quote_datetime_delegates_to_first_option(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.quote_datetime == ib.options[0].quote_datetime


def test_get_profit_loss_after_open(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    assert isinstance(ib.get_profit_loss(), float)


def test_current_value_sums_legs(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    assert ib.current_value == pytest.approx(sum(o.current_value for o in ib.options), abs=0.01)


def test_trade_value_sums_legs(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    assert ib.trade_value == pytest.approx(sum(o.trade_value for o in ib.options), abs=0.01)


def test_max_profit_returns_none_before_open(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.max_profit is None


def test_max_loss_returns_none_before_open(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.max_loss is None


def test_short_max_profit_equals_trade_price(make_iron_butterfly):
    """SHORT: max profit is the net credit received."""
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    assert ib.max_profit == pytest.approx(ib.get_trade_price(), abs=0.01)


def test_short_max_loss_equals_wing_width_minus_credit(make_iron_butterfly):
    """SHORT: max loss = wing_width - net credit."""
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    wing_width = max(
        ib.center_put.strike - ib.lower_put.strike,
        ib.upper_call.strike - ib.center_put.strike,
    )
    expected = wing_width - ib.get_trade_price()
    assert ib.max_loss == pytest.approx(expected, abs=0.01)


def test_long_max_profit_equals_wing_width_minus_debit(make_iron_butterfly):
    """LONG: max profit = wing_width - net debit."""
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ib._open_trade()
    wing_width = max(
        ib.center_put.strike - ib.lower_put.strike,
        ib.upper_call.strike - ib.center_put.strike,
    )
    expected = wing_width - ib.get_trade_price()
    assert ib.max_profit == pytest.approx(expected, abs=0.01)


def test_long_max_loss_equals_trade_price(make_iron_butterfly):
    """LONG: max loss is the net debit paid."""
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ib._open_trade()
    assert ib.max_loss == pytest.approx(ib.get_trade_price(), abs=0.01)


def test_max_profit_plus_max_loss_equals_wing_width(make_iron_butterfly):
    """max_profit + max_loss must always equal the wing width."""
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    wing_width = max(
        ib.center_put.strike - ib.lower_put.strike,
        ib.upper_call.strike - ib.center_put.strike,
    )
    assert ib.max_profit + ib.max_loss == pytest.approx(wing_width, abs=0.01)


# ── get_required_margin ───────────────────────────────────────────────────────

def test_required_margin_long_is_zero(make_iron_butterfly):
    """LONG iron butterfly is a debit trade — no margin required."""
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG)
    assert ib.get_required_margin(1) == 0.0


def test_required_margin_short_is_positive(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.get_required_margin(1) > 0


def test_required_margin_short_formula(make_iron_butterfly):
    """SHORT margin = (wing_width - current_price) * 100 * quantity."""
    ib = make_iron_butterfly()
    wing_width = max(
        ib.center_put.strike - ib.lower_put.strike,
        ib.upper_call.strike - ib.center_put.strike,
    )
    expected = (wing_width - ib.price) * 100 * 1
    assert ib.get_required_margin(1) == pytest.approx(expected, abs=1.0)


def test_required_margin_scales_with_quantity(make_iron_butterfly):
    ib = make_iron_butterfly()
    assert ib.get_required_margin(3) == pytest.approx(ib.get_required_margin(1) * 3, abs=0.01)


def test_required_margin_uses_absolute_quantity(make_iron_butterfly):
    """Negative quantity should give same margin as positive."""
    ib = make_iron_butterfly()
    assert ib.get_required_margin(-2) == pytest.approx(ib.get_required_margin(2), abs=0.01)


# ── get_price_history ─────────────────────────────────────────────────────────

def test_price_history_raises_before_open(make_iron_butterfly):
    ib = make_iron_butterfly()
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        ib.get_history()


def test_price_history_returns_list(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    assert isinstance(ib.get_history(), list)


def test_price_history_each_entry_has_required_keys(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    for entry in ib.get_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_length_matches_lower_put_updates(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    last_date = ib.lower_put.quote_datetime
    expected_len = sum(1 for k in ib.lower_put.updates if k <= last_date)
    assert len(ib.get_history()) == expected_len


def test_price_history_price_matches_calculate_price_each_row(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    lp_u = ib.lower_put.updates
    cp_u = ib.center_put.updates
    cc_u = ib.center_call.updates
    uc_u = ib.upper_call.updates
    last_date = ib.lower_put.quote_datetime
    keys = sorted(k for k in lp_u if k <= last_date)

    for i, entry in enumerate(ib.get_history()):
        k = keys[i]
        expected = ib._calculate_price(
            lower_put_price=lp_u[k]['price'],
            center_put_price=cp_u[k]['price'],
            center_call_price=cc_u[k]['price'],
            upper_call_price=uc_u[k]['price'],
        )
        assert entry['price'] == pytest.approx(expected, abs=0.01)


def test_price_history_spot_price_matches_lower_put_updates(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    lp_u = ib.lower_put.updates
    last_date = ib.lower_put.quote_datetime
    keys = sorted(k for k in lp_u if k <= last_date)
    for i, entry in enumerate(ib.get_history()):
        assert entry['spot_price'] == lp_u[keys[i]].get('spot_price')


def test_price_history_pnl_is_zero_at_open_bar(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    assert ib.get_history()[0]['pnl'] == pytest.approx(0.0, abs=1.0)


def test_price_history_pnl_pct_is_zero_at_open_bar(make_iron_butterfly):
    ib = make_iron_butterfly(fill_factor=1.0)
    ib._open_trade()
    assert ib.get_history()[0]['pnl_pct'] == pytest.approx(0.0, abs=0.01)


def test_price_history_long_iron_butterfly_has_required_keys(make_iron_butterfly):
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ib._open_trade()
    for entry in ib.get_history():
        assert entry.keys() == REQUIRED_HISTORY_KEYS


def test_price_history_long_iron_butterfly_price_formula(make_iron_butterfly):
    ib = make_iron_butterfly(position_type=OptionPositionType.LONG, fill_factor=1.0)
    ib._open_trade()
    lp_u = ib.lower_put.updates
    cp_u = ib.center_put.updates
    cc_u = ib.center_call.updates
    uc_u = ib.upper_call.updates
    last_date = ib.lower_put.quote_datetime
    keys = sorted(k for k in lp_u if k <= last_date)

    for i, entry in enumerate(ib.get_history()):
        k = keys[i]
        expected = (lp_u[k]['price'] + uc_u[k]['price']) - (cp_u[k]['price'] + cc_u[k]['price'])
        assert entry['price'] == pytest.approx(expected, abs=0.01)
