"""
Tests for Straddle spread.

Default fixture is a short straddle at strike 380:
    call = MSFT 380 call, exp 2026-04-10
    put  = MSFT 380 put,  exp 2026-04-10

Short straddle opened with quantity=-1.
Long straddle opened with quantity=1.
"""
import datetime
import pytest

from options_framework.option_types import OptionPositionType, OptionSpreadType, OptionStatus
from options_framework.spreads.straddle import Straddle

QUOTE_DT = datetime.datetime(2026, 3, 17)
STRIKE = 380.0


# ── __post_init__ validation ──────────────────────────────────────────────────

def test_post_init_raises_if_not_two_options(make_option, daily_updates_put_380):
    opt = make_option(daily_updates_put_380, strike=STRIKE, option_type='put')
    with pytest.raises(ValueError, match="two options"):
        Straddle(options=[opt], spread_type=OptionSpreadType.STRADDLE)


def test_post_init_raises_if_both_same_option_type(make_option, daily_updates_put_380):
    opt1 = make_option(daily_updates_put_380, strike=STRIKE, option_type='put')
    opt2 = make_option(daily_updates_put_380, strike=STRIKE, option_type='put')
    with pytest.raises(ValueError, match="one put and one call"):
        Straddle(options=[opt1, opt2], spread_type=OptionSpreadType.STRADDLE)


def test_post_init_raises_if_strikes_differ(make_option, daily_updates_call_380, daily_updates_put_370):
    call = make_option(daily_updates_call_380, strike=380.0, option_type='call')
    put = make_option(daily_updates_put_370, strike=370.0, option_type='put')
    with pytest.raises(ValueError, match="same strike"):
        Straddle(options=[call, put], spread_type=OptionSpreadType.STRADDLE)


def test_post_init_raises_if_different_symbols(make_option, daily_updates_call_380, daily_updates_put_380):
    call = make_option(daily_updates_call_380, strike=STRIKE, option_type='call')
    put = make_option(daily_updates_put_380, strike=STRIKE, option_type='put', symbol='AAPL')
    with pytest.raises(ValueError, match="same equity"):
        Straddle(options=[call, put], spread_type=OptionSpreadType.STRADDLE)


def test_post_init_raises_if_different_expirations(make_option, daily_updates_call_380, daily_updates_put_380):
    call = make_option(daily_updates_call_380, strike=STRIKE, option_type='call')
    put = make_option(daily_updates_put_380, strike=STRIKE, option_type='put',
                      expiration=datetime.date(2026, 5, 1))
    with pytest.raises(ValueError, match="same expiration"):
        Straddle(options=[call, put], spread_type=OptionSpreadType.STRADDLE)


def test_post_init_raises_on_wrong_spread_type(make_option, daily_updates_call_380, daily_updates_put_380):
    call = make_option(daily_updates_call_380, strike=STRIKE, option_type='call')
    put = make_option(daily_updates_put_380, strike=STRIKE, option_type='put')
    with pytest.raises(ValueError, match="spread type of STRADDLE"):
        Straddle(options=[call, put], spread_type=OptionSpreadType.SINGLE)


def test_post_init_assigns_call_and_put(make_straddle):
    s = make_straddle()
    assert s.call.option_type == 'call'
    assert s.put.option_type == 'put'


# ── open_trade ────────────────────────────────────────────────────────────────

def test_open_trade_short_sets_position_type(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    assert s.position_type == OptionPositionType.SHORT


def test_open_trade_long_sets_position_type(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=1)
    assert s.position_type == OptionPositionType.LONG


def test_open_trade_sets_quantity(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    assert s.quantity == -1


def test_open_trade_both_legs_open(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    assert OptionStatus.TRADE_IS_OPEN in s.call.status
    assert OptionStatus.TRADE_IS_OPEN in s.put.status


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_both_legs(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    s._close_trade(quote_datetime=QUOTE_DT)
    assert OptionStatus.TRADE_IS_CLOSED in s.call.status
    assert OptionStatus.TRADE_IS_CLOSED in s.put.status


def test_close_trade_updates_quantity(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-2)
    s._close_trade(quote_datetime=QUOTE_DT, quantity=1)
    assert s.quantity == -1


# ── price property ────────────────────────────────────────────────────────────

def test_price_is_call_plus_put(make_straddle):
    s = make_straddle()
    expected = round(s.call.price + s.put.price, 2)
    assert s.price == pytest.approx(expected)


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_none_before_open(make_straddle):
    s = make_straddle()
    assert s.get_trade_price() is None


def test_get_trade_price_returns_sum_after_open(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    expected = round(
        s.call.trade_open_info.price + s.put.trade_open_info.price, 2
    )
    assert s.get_trade_price() == pytest.approx(expected)


# ── get_closed_price ──────────────────────────────────────────────────────────

def test_get_closed_price_returns_none_before_close(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    assert s.get_closed_price() is None


def test_get_closed_price_returns_sum_after_close(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    s._close_trade(quote_datetime=QUOTE_DT)
    expected = round(
        s.call.trade_close_info.price + s.put.trade_close_info.price, 2
    )
    assert s.get_closed_price() == pytest.approx(expected)


# ── max_profit / max_loss ─────────────────────────────────────────────────────

def test_max_profit_short_equals_premium_received(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    assert s.max_profit == pytest.approx(s.get_trade_premium() * -1)


def test_max_profit_long_is_none(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=1)
    assert s.max_profit is None


def test_max_loss_long_equals_premium_paid(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=1)
    assert s.max_loss == pytest.approx(s.get_trade_premium() * -1)


def test_max_loss_short_is_none(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    assert s.max_loss is None


# ── get_required_margin ───────────────────────────────────────────────────────

def test_get_required_margin_zero_for_long(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=1)
    assert s.get_required_margin(1) == 0


def test_get_required_margin_positive_for_short(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    assert s.get_required_margin(-1) > 0


def test_get_required_margin_short_larger_leg_plus_other_premium(make_straddle):
    """Margin = larger of (call margin, put margin) + other leg's premium."""
    from decimal import Decimal
    from options_framework.utils.helpers import decimalize_4, decimalize_2, decimalize_0

    s = make_straddle()
    s._open_trade(quantity=-1)

    legs = [s.call, s.put]
    leg_margins = []
    leg_premiums = []
    for option in legs:
        pct_20 = decimalize_4(option.spot_price * 0.2)
        pct_10 = decimalize_4(option.spot_price * 0.1)
        otm_amount = decimalize_4(option.spot_price - option.strike) if option.otm() else decimalize_0(0)
        price = decimalize_2(option.price)
        calc1 = pct_20 - otm_amount + price
        calc2 = pct_10 + price
        calc3 = Decimal(1) + price
        leg_margin = float(max(calc1, calc2, calc3)) * 100
        leg_margins.append(leg_margin)
        leg_premiums.append(float(price) * 100)

    if leg_margins[0] >= leg_margins[1]:
        expected = round(leg_margins[0] + leg_premiums[1], 2)
    else:
        expected = round(leg_margins[1] + leg_premiums[0], 2)

    assert s.get_required_margin(-1) == pytest.approx(expected)


# ── properties ────────────────────────────────────────────────────────────────

def test_strike_delegates_to_call(make_straddle):
    s = make_straddle()
    assert s.strike == s.call.strike


def test_expiration_delegates_to_call(make_straddle):
    s = make_straddle()
    assert s.expiration == s.call.expiration

def test_get_dte_delegates_to_call(make_straddle):
    s = make_straddle()
    assert s.get_dte() == s.call.get_dte()


def test_symbol_from_spread_base(make_straddle):
    s = make_straddle()
    assert s.symbol == 'MSFT'


# ── get_price_history ─────────────────────────────────────────────────────────

def test_get_price_history_raises_before_open(make_straddle):
    s = make_straddle()
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        s.get_history()


def test_get_price_history_returns_list(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    assert isinstance(s.get_history(), list)


def test_get_price_history_entry_count_matches_updates(make_straddle, daily_updates_call_380, daily_updates_put_380):
    s = make_straddle()
    s._open_trade(quantity=-1)
    last_date = datetime.datetime(2026, 4, 10, 0, 0)
    s.call._next(last_date)
    s.put._next(last_date)
    history = s.get_history()
    expected = len(set(daily_updates_call_380.keys()) & set(daily_updates_put_380.keys()))
    assert len(history) == expected


def test_get_price_history_contains_expected_keys(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    history = s.get_history()
    expected_keys = {'quote_datetime', 'price', 'spot_price', 'pnl', 'pnl_pct',
                     'delta', 'gamma', 'theta', 'vega', 'rho', 'iv'}
    assert set(history[0].keys()) == expected_keys


def test_get_price_history_spread_price_is_call_plus_put(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1, fill_factor=1.0)
    history = s.get_history()
    # call=24.45, put=3.78 at open
    assert history[0]['price'] == pytest.approx(28.22, abs=0.02)


def test_get_price_history_pnl_zero_on_open_day(make_straddle):
    s = make_straddle(fill_factor=1.0)
    s._open_trade(quantity=-1)
    history = s.get_history()
    assert history[0]['pnl'] == pytest.approx(0.0, abs=0.01)


def test_get_price_history_pnl_second_entry(make_straddle):
    s = make_straddle(fill_factor=1.0)
    s._open_trade(quantity=-1)
    last_date = datetime.datetime(2026, 4, 10, 0, 0)
    s.call._next(last_date)
    s.put._next(last_date)
    history = s.get_history()
    # call pnl: (18.80 - 24.45) * 100 * -1 = 565.0
    # put pnl:  (5.93 - 3.78) * 100 * -1  = -215.0
    # spread pnl = 350.0
    assert history[1]['pnl'] == pytest.approx(350.0, abs=1.0)


def test_get_price_history_greeks_are_netted(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    history = s.get_history()
    # delta: 0.7708 + (-0.2218) = 0.549
    assert history[0]['delta'] == pytest.approx(0.549, abs=0.0001)


def test_get_price_history_bounded_by_close_date(make_straddle):
    s = make_straddle()
    s._open_trade(quantity=-1)
    close_dt = datetime.datetime(2026, 3, 19)
    s.call._next(close_dt)
    s.put._next(close_dt)
    s._close_trade(quote_datetime=close_dt)
    history = s.get_history()
    assert all(entry['quote_datetime'] <= close_dt for entry in history)
    assert history[-1]['quote_datetime'] == close_dt