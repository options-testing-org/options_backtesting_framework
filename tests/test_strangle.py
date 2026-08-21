"""
Tests for Strangle spread.

Default fixture is a short strangle:
    call = MSFT 390 call, exp 2026-04-10
    put  = MSFT 380 put,  exp 2026-04-10

Call strike must be greater than put strike.
"""
import datetime
import pytest

from options_framework.option_types import OptionPositionType, OptionSpreadType, OptionStatus
from options_framework.spreads.strangle import Strangle

QUOTE_DT = datetime.datetime(2026, 3, 17)
CALL_STRIKE = 390.0
PUT_STRIKE = 380.0


# ── __post_init__ validation ──────────────────────────────────────────────────

def test_post_init_raises_if_not_two_options(make_option, daily_updates_put_380):
    opt = make_option(daily_updates_put_380, strike=PUT_STRIKE, option_type='put')
    with pytest.raises(ValueError, match="two options"):
        Strangle(options=[opt], spread_type=OptionSpreadType.STRANGLE)


def test_post_init_raises_if_both_same_option_type(make_option, daily_updates_put_380):
    opt1 = make_option(daily_updates_put_380, strike=PUT_STRIKE, option_type='put')
    opt2 = make_option(daily_updates_put_380, strike=CALL_STRIKE, option_type='put')
    with pytest.raises(ValueError, match="one put and one call"):
        Strangle(options=[opt1, opt2], spread_type=OptionSpreadType.STRANGLE)


def test_post_init_raises_if_call_strike_not_greater_than_put_strike(make_option, daily_updates_call_390, daily_updates_put_380):
    call = make_option(daily_updates_call_390, strike=CALL_STRIKE, option_type='call')
    put = make_option(daily_updates_put_380, strike=CALL_STRIKE, option_type='put')
    with pytest.raises(ValueError, match="call strike must be greater than put strike"):
        Strangle(options=[call, put], spread_type=OptionSpreadType.STRANGLE)


def test_post_init_raises_if_different_symbols(make_option, daily_updates_call_390, daily_updates_put_380):
    call = make_option(daily_updates_call_390, strike=CALL_STRIKE, option_type='call')
    put = make_option(daily_updates_put_380, strike=PUT_STRIKE, option_type='put', symbol='AAPL')
    with pytest.raises(ValueError, match="same equity"):
        Strangle(options=[call, put], spread_type=OptionSpreadType.STRANGLE)


def test_post_init_raises_if_different_expirations(make_option, daily_updates_call_390, daily_updates_put_380):
    call = make_option(daily_updates_call_390, strike=CALL_STRIKE, option_type='call')
    put = make_option(daily_updates_put_380, strike=PUT_STRIKE, option_type='put',
                      expiration=datetime.date(2026, 5, 1))
    with pytest.raises(ValueError, match="same expiration"):
        Strangle(options=[call, put], spread_type=OptionSpreadType.STRANGLE)


def test_post_init_raises_on_wrong_spread_type(make_option, daily_updates_call_390, daily_updates_put_380):
    call = make_option(daily_updates_call_390, strike=CALL_STRIKE, option_type='call')
    put = make_option(daily_updates_put_380, strike=PUT_STRIKE, option_type='put')
    with pytest.raises(ValueError, match="spread type of STRANGLE"):
        Strangle(options=[call, put], spread_type=OptionSpreadType.STRADDLE)


def test_post_init_assigns_call_and_put(make_strangle):
    s = make_strangle()
    assert s.call.option_type == 'call'
    assert s.put.option_type == 'put'


def test_post_init_call_strike_greater_than_put_strike(make_strangle):
    s = make_strangle()
    assert s.call.strike > s.put.strike


# ── create ────────────────────────────────────────────────────────────────────

def test_create_raises_if_call_strike_not_greater_than_put_strike(get_mock_option_chain):
    chain = get_mock_option_chain(QUOTE_DT)
    expiration = chain.expirations[0]
    with pytest.raises(ValueError, match="Call strike must be greater than put strike"):
        Strangle.create(
            option_chain=chain,
            expiration=expiration,
            call_strike=380.0,
            put_strike=390.0,
        )


def test_create_raises_if_no_matching_expiration(get_mock_option_chain):
    chain = get_mock_option_chain(QUOTE_DT)
    with pytest.raises(ValueError, match="No matching expiration"):
        Strangle.create(
            option_chain=chain,
            expiration=datetime.date(2099, 1, 1),
            call_strike=CALL_STRIKE,
            put_strike=PUT_STRIKE,
        )


def test_create_returns_strangle_instance(get_mock_option_chain):
    chain = get_mock_option_chain(QUOTE_DT)
    expiration = chain.expirations[0]
    s = Strangle.create(
        option_chain=chain,
        expiration=expiration,
        call_strike=CALL_STRIKE,
        put_strike=PUT_STRIKE,
    )
    assert isinstance(s, Strangle)


# ── open_trade ────────────────────────────────────────────────────────────────

def test_open_trade_short_sets_position_type(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    assert s.position_type == OptionPositionType.SHORT


def test_open_trade_long_sets_position_type(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=1)
    assert s.position_type == OptionPositionType.LONG


def test_open_trade_sets_quantity(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    assert s.quantity == -1


def test_open_trade_both_legs_open(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    assert OptionStatus.TRADE_IS_OPEN in s.call.status
    assert OptionStatus.TRADE_IS_OPEN in s.put.status


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_both_legs(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    s._close_trade(quote_datetime=QUOTE_DT)
    assert OptionStatus.TRADE_IS_CLOSED in s.call.status
    assert OptionStatus.TRADE_IS_CLOSED in s.put.status


def test_close_trade_updates_quantity(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-2)
    s._close_trade(quote_datetime=QUOTE_DT, quantity=1)
    assert s.quantity == -1


# ── price ─────────────────────────────────────────────────────────────────────

def test_price_is_call_plus_put(make_strangle):
    s = make_strangle()
    expected = round(s.call.price + s.put.price, 2)
    assert s.price == pytest.approx(expected)


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_none_before_open(make_strangle):
    s = make_strangle()
    assert s.get_trade_price() is None


def test_get_trade_price_returns_sum_after_open(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    expected = round(
        s.call.trade_open_info.price + s.put.trade_open_info.price, 2
    )
    assert s.get_trade_price() == pytest.approx(expected)


# ── get_closed_price ──────────────────────────────────────────────────────────

def test_get_closed_price_returns_none_before_close(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    assert s.get_closed_price() is None


def test_get_closed_price_returns_sum_after_close(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    s._close_trade(quote_datetime=QUOTE_DT)
    expected = round(
        s.call.trade_close_info.price + s.put.trade_close_info.price, 2
    )
    assert s.get_closed_price() == pytest.approx(expected)


# ── max_profit / max_loss ─────────────────────────────────────────────────────

def test_max_profit_short_equals_premium_received(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    assert s.max_profit == pytest.approx(s.get_trade_premium() * -1)


def test_max_profit_long_is_none(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=1)
    assert s.max_profit is None


def test_max_loss_long_equals_premium_paid(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=1)
    assert s.max_loss == pytest.approx(s.get_trade_premium() * -1)


def test_max_loss_short_is_none(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    assert s.max_loss is None


# ── get_required_margin ───────────────────────────────────────────────────────

def test_get_required_margin_zero_for_long(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=1)
    assert s.get_required_margin(1) == 0


def test_get_required_margin_positive_for_short(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    assert s.get_required_margin(-1) > 0


# ── properties ────────────────────────────────────────────────────────────────

def test_strike_call_and_put_strikes_differ(make_strangle):
    s = make_strangle()
    assert s.call.strike != s.put.strike


def test_expiration_delegates_to_call(make_strangle):
    s = make_strangle()
    assert s.expiration == s.call.expiration


def test_get_dte_delegates_to_call(make_strangle):
    s = make_strangle()
    assert s.get_dte() == s.call.get_dte()


def test_symbol_from_spread_base(make_strangle):
    s = make_strangle()
    assert s.symbol == 'MSFT'


# ── get_price_history ─────────────────────────────────────────────────────────

def test_get_price_history_raises_before_open(make_strangle):
    s = make_strangle()
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        s.get_history()


def test_get_price_history_returns_list(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    assert isinstance(s.get_history(), list)


def test_get_price_history_entry_count_matches_updates(make_strangle, daily_updates_call_390, daily_updates_put_380):
    s = make_strangle()
    s._open_trade(quantity=-1)
    last_date = datetime.datetime(2026, 4, 10, 0, 0)
    s.call._next(last_date)
    s.put._next(last_date)
    history = s.get_history()
    expected = len(set(daily_updates_call_390.keys()) & set(daily_updates_put_380.keys()))
    assert len(history) == expected


def test_get_price_history_contains_expected_keys(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    history = s.get_history()
    expected_keys = {'quote_datetime', 'price', 'spot_price', 'pnl', 'pnl_pct',
                     'delta', 'gamma', 'theta', 'vega', 'rho', 'iv'}
    assert set(history[0].keys()) == expected_keys


def test_get_price_history_spread_price_is_call_plus_put(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    history = s.get_history()
    # call=16.78, put=3.78 at open
    assert history[0]['price'] == pytest.approx(20.55, abs=0.01)


def test_get_price_history_pnl_zero_on_open_day(make_strangle):
    s = make_strangle(fill_factor=1.0)
    s._open_trade(quantity=-1)
    history = s.get_history()
    assert history[0]['pnl'] == pytest.approx(0.0, abs=0.01)


def test_get_price_history_pnl_second_entry(make_strangle):
    s = make_strangle(fill_factor=1.0)
    s._open_trade(quantity=-1)
    last_date = datetime.datetime(2026, 4, 10, 0, 0)
    s.call._next(last_date)
    s.put._next(last_date)
    history = s.get_history()
    # call pnl: (12.13 - 16.78) * 100 * -1 = 465.0
    # put pnl:  (5.93 - 3.78) * 100 * -1   = -215.0
    # spread pnl = 250.0
    assert history[1]['pnl'] == pytest.approx(250.0, abs=1.0)


def test_get_price_history_greeks_are_netted(make_strangle):
    s = make_strangle()
    s._open_trade(quantity=-1)
    history = s.get_history()
    # delta: 0.6618 + (-0.2218) = 0.44
    assert history[0]['delta'] == pytest.approx(0.44, abs=0.0001)


def test_get_price_history_bounded_by_close_date(make_strangle):
    s = make_strangle(fill_factor=1.0)
    s._open_trade(quantity=-1)
    close_dt = datetime.datetime(2026, 3, 19)
    s.call._next(close_dt)
    s.put._next(close_dt)
    s._close_trade(quote_datetime=close_dt)
    history = s.get_history()
    assert all(entry['quote_datetime'] <= close_dt for entry in history)
    assert history[-1]['quote_datetime'] == close_dt