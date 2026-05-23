"""
Tests for Vertical spread.

Conventions
───────────
- Default fixture is a SHORT put vertical (put credit spread):
    long_option  = put at strike 370 (protection leg, positive qty)
    short_option = put at strike 380 (sold leg, negative qty)
    position_type = SHORT

- A LONG put vertical (debit spread) uses position_type=OptionPositionType.LONG.

- Strikes are deliberately round numbers to make math assertions readable.
"""
import datetime
import pytest

from options_framework.option_types import OptionPositionType, OptionSpreadType, OptionStatus
from options_framework.spreads.vertical import Vertical

QUOTE_DT = datetime.datetime(2026, 3, 17)
LONG_STRIKE = 370.0
SHORT_STRIKE = 380.0
STRIKE_WIDTH = SHORT_STRIKE - LONG_STRIKE  # 10


# ── __post_init__ validation ──────────────────────────────────────────────────

def test_post_init_raises_on_mixed_option_types(make_put_option_380, make_call_option_380):
    put = make_put_option_380(strike=370.0)
    call = make_call_option_380(strike=380.0)
    with pytest.raises(ValueError, match="Both legs must be either calls or puts"):
        Vertical(options=[put, call], spread_type=OptionSpreadType.VERTICAL,
                 position_type=OptionPositionType.SHORT)


def test_post_init_raises_on_mismatched_expirations(make_put_option_380):
    opt1 = make_put_option_380(strike=370.0)
    opt2 = make_put_option_380(strike=380.0, expiration=datetime.date(2026, 5, 1))
    with pytest.raises(ValueError, match="Both legs must have the same expiration"):
        Vertical(options=[opt1, opt2], spread_type=OptionSpreadType.VERTICAL,
                 position_type=OptionPositionType.SHORT)


def test_post_init_raises_on_same_strike(make_put_option_380):
    opt1 = make_put_option_380(strike=380.0)
    opt2 = make_put_option_380(strike=380.0)
    with pytest.raises(ValueError, match="strikes must not be the same"):
        Vertical(options=[opt1, opt2], spread_type=OptionSpreadType.VERTICAL,
                 position_type=OptionPositionType.SHORT)


def test_post_init_raises_on_wrong_spread_type(make_put_option_380):
    opt1 = make_put_option_380(strike=370.0)
    opt2 = make_put_option_380(strike=380.0)
    with pytest.raises(ValueError, match="spread type of VERTICAL"):
        Vertical(options=[opt1, opt2], spread_type=OptionSpreadType.SINGLE,
                 position_type=OptionPositionType.SHORT)


def test_post_init_assigns_long_and_short_option(make_vertical):
    v = make_vertical()
    assert v.long_option.strike == LONG_STRIKE
    assert v.short_option.strike == SHORT_STRIKE


def test_post_init_sets_leg_position_types(make_vertical):
    v = make_vertical()
    assert v.long_option.position_type == OptionPositionType.LONG
    assert v.short_option.position_type == OptionPositionType.SHORT


# ── create ────────────────────────────────────────────────────────────────────

def test_create_raises_if_position_type_is_none(get_mock_option_chain):
    chain = get_mock_option_chain(QUOTE_DT)
    expiration = chain.expirations[0]
    with pytest.raises(ValueError, match="position_type must be specified"):
        Vertical.create(
            option_chain=chain,
            expiration=expiration,
            option_type='put',
            long_strike=370.0,
            short_strike=380.0,
            position_type=None,
        )


def test_create_raises_if_long_and_short_strike_equal(get_mock_option_chain):
    chain = get_mock_option_chain(QUOTE_DT)
    expiration = chain.expirations[0]
    with pytest.raises(ValueError, match="cannot be the same"):
        Vertical.create(
            option_chain=chain,
            expiration=expiration,
            option_type='put',
            long_strike=380.0,
            short_strike=380.0,
            position_type=OptionPositionType.SHORT,
        )


def test_create_raises_if_no_matching_expiration(get_mock_option_chain):
    chain = get_mock_option_chain(QUOTE_DT)
    with pytest.raises(ValueError, match="No matching expiration"):
        Vertical.create(
            option_chain=chain,
            expiration=datetime.date(2099, 1, 1),
            option_type='put',
            long_strike=370.0,
            short_strike=380.0,
            position_type=OptionPositionType.SHORT,
        )


def test_create_returns_vertical_instance(get_mock_option_chain):
    chain = get_mock_option_chain(QUOTE_DT)
    expiration = chain.expirations[0]
    v = Vertical.create(
        option_chain=chain,
        expiration=expiration,
        option_type='put',
        long_strike=370.0,
        short_strike=380.0,
        position_type=OptionPositionType.SHORT,
    )
    assert isinstance(v, Vertical)


def test_create_sets_position_type(get_mock_option_chain):
    chain = get_mock_option_chain(QUOTE_DT)
    expiration = chain.expirations[0]
    v = Vertical.create(
        option_chain=chain,
        expiration=expiration,
        option_type='put',
        long_strike=370.0,
        short_strike=380.0,
        position_type=OptionPositionType.SHORT,
    )
    assert v.position_type == OptionPositionType.SHORT


# ── open_trade ────────────────────────────────────────────────────────────────

def test_open_trade_raises_on_non_positive_quantity(make_vertical):
    v = make_vertical()
    with pytest.raises(ValueError, match="Quantity must be positive"):
        v._open_trade(quantity=0)


def test_open_trade_raises_on_negative_quantity(make_vertical):
    v = make_vertical()
    with pytest.raises(ValueError, match="Quantity must be positive"):
        v._open_trade(quantity=-1)


def test_open_trade_sets_quantity(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=2)
    assert v.quantity == 2


def test_open_trade_long_leg_gets_positive_quantity(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=2)
    assert v.long_option.quantity == 2


def test_open_trade_short_leg_gets_negative_quantity(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=2)
    assert v.short_option.quantity == -2


def test_open_trade_does_not_overwrite_position_type(make_vertical):
    v = make_vertical(position_type=OptionPositionType.SHORT)
    v._open_trade(quantity=1)
    assert v.position_type == OptionPositionType.SHORT


def test_open_trade_long_leg_status_is_open(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=1)
    assert OptionStatus.TRADE_IS_OPEN in v.long_option.status


def test_open_trade_short_leg_status_is_open(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=1)
    assert OptionStatus.TRADE_IS_OPEN in v.short_option.status


# ── close_trade ───────────────────────────────────────────────────────────────

def test_close_trade_closes_both_legs(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=1)
    v._close_trade(quote_datetime=QUOTE_DT)
    assert OptionStatus.TRADE_IS_CLOSED in v.long_option.status
    assert OptionStatus.TRADE_IS_CLOSED in v.short_option.status


def test_close_trade_decrements_quantity(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=2)
    v._close_trade(quote_datetime=QUOTE_DT, quantity=1)
    assert v.quantity == 1


def test_close_trade_full_close_sets_quantity_to_zero(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=1)
    v._close_trade(quote_datetime=QUOTE_DT)
    assert v.quantity == 0


# ── price property ────────────────────────────────────────────────────────────

def test_price_is_long_minus_short(make_vertical):
    v = make_vertical()
    expected = round(v.long_option.price - v.short_option.price, 2)
    assert v.price == pytest.approx(expected)


# ── get_trade_price ───────────────────────────────────────────────────────────

def test_get_trade_price_returns_none_before_open(make_vertical):
    v = make_vertical()
    assert v.get_trade_price() is None


def test_get_trade_price_returns_net_debit_after_open(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=1)
    expected = round(
        v.long_option.trade_open_info.price - v.short_option.trade_open_info.price, 2
    )
    assert v.get_trade_price() == pytest.approx(expected)


# ── get_closed_price ──────────────────────────────────────────────────────────

def test_get_closed_price_returns_none_before_close(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=1)
    assert v.get_closed_price() is None


def test_get_closed_price_returns_net_price_after_close(make_vertical):
    v = make_vertical()
    v._open_trade(quantity=1)
    dt = QUOTE_DT + datetime.timedelta(days=1)
    v._close_trade(quote_datetime=QUOTE_DT)
    expected = round(
        v.long_option.trade_close_info.price - v.short_option.trade_close_info.price, 2
    )
    assert v.get_closed_price() == pytest.approx(expected)


# ── max_profit ────────────────────────────────────────────────────────────────

def test_max_profit_raises_if_position_type_is_none(make_put_option_380):
    # construct without position_type to trigger the guard
    opt1 = make_put_option_380(strike=LONG_STRIKE)
    opt2 = make_put_option_380(strike=SHORT_STRIKE)
    v = Vertical(options=[opt1, opt2], spread_type=OptionSpreadType.VERTICAL,
                 position_type=OptionPositionType.SHORT)
    v.position_type = None
    with pytest.raises(RuntimeError, match="Cannot calculate max profit"):
        _ = v.max_profit


def test_max_profit_short_equals_net_credit(make_vertical):
    """For a credit spread, max profit is the net premium received."""
    v = make_vertical(position_type=OptionPositionType.SHORT)
    v._open_trade(quantity=1)
    # trade_value is negative for a credit spread (net credit received)
    expected = v.trade_value * -1
    assert v.max_profit == pytest.approx(expected)


def test_max_profit_long_equals_spread_width_minus_debit(make_vertical):
    """For a debit spread, max profit is spread width minus net debit paid."""
    v = make_vertical(position_type=OptionPositionType.LONG)
    v._open_trade(quantity=1)
    long_price = v.long_option.trade_open_info.price
    short_price = v.short_option.trade_open_info.price
    expected = round((STRIKE_WIDTH - abs(long_price - short_price)) * 100, 2)
    assert v.max_profit == pytest.approx(expected)


# ── max_loss ──────────────────────────────────────────────────────────────────

def test_max_loss_raises_if_position_type_is_none(make_put_option_380):
    opt1 = make_put_option_380(strike=LONG_STRIKE)
    opt2 = make_put_option_380(strike=SHORT_STRIKE)
    v = Vertical(options=[opt1, opt2], spread_type=OptionSpreadType.VERTICAL,
                 position_type=OptionPositionType.SHORT)
    v.position_type = None
    with pytest.raises(RuntimeError, match="Cannot calculate max loss"):
        _ = v.max_loss


def test_max_loss_long_equals_trade_value(make_vertical):
    """For a debit spread, max loss is what you paid."""
    v = make_vertical(position_type=OptionPositionType.LONG)
    v._open_trade(quantity=1)
    assert v.max_loss == pytest.approx(v.trade_value)


def test_max_loss_short_equals_spread_width_minus_credit(make_vertical):
    """For a credit spread, max loss is spread width minus credit received."""
    v = make_vertical(position_type=OptionPositionType.SHORT)
    v._open_trade(quantity=1)
    long_price = v.long_option.trade_open_info.price
    short_price = v.short_option.trade_open_info.price
    expected = round((STRIKE_WIDTH - abs(long_price - short_price)) * 100 * 1, 2)
    assert v.max_loss == pytest.approx(expected)


# ── get_required_margin ───────────────────────────────────────────────────────

def test_get_required_margin_returns_zero_before_open(make_vertical):
    v = make_vertical()
    assert v.get_required_margin(1) == 0


def test_get_required_margin_returns_zero_for_long(make_vertical):
    v = make_vertical(position_type=OptionPositionType.LONG)
    v._open_trade(quantity=1)
    assert v.get_required_margin(1) == 0


def test_get_required_margin_short_equals_strike_width_times_quantity(make_vertical):
    v = make_vertical(position_type=OptionPositionType.SHORT)
    v._open_trade(quantity=2)
    expected = abs((SHORT_STRIKE - LONG_STRIKE) * 100 * 2)
    assert v.get_required_margin(2) == pytest.approx(expected)


# ── properties ────────────────────────────────────────────────────────────────

def test_symbol_delegates_to_long_option(make_vertical):
    v = make_vertical()
    assert v.symbol == v.long_option.symbol


def test_expiration_delegates_to_long_option(make_vertical):
    v = make_vertical()
    assert v.expiration == v.long_option.expiration


def test_option_type_delegates_to_long_option(make_vertical):
    v = make_vertical()
    assert v.option_type == v.long_option.option_type


def test_get_dte_delegates_to_long_option(make_vertical):
    v = make_vertical()
    assert v.get_dte() == v.long_option.get_dte()

# ── get_price_history ─────────────────────────────────────────────────────────

OPEN_DT = datetime.datetime(2026, 3, 17)

def test_get_price_history_raises_before_open(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380)
    with pytest.raises(RuntimeError, match="trade has not been opened"):
        v.get_price_history()


def test_get_price_history_returns_list(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380)
    v._open_trade(quantity=1)
    history = v.get_price_history()
    assert isinstance(history, list)


def test_get_price_history_entries_are_dicts(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380)
    v._open_trade(quantity=1)
    history = v.get_price_history()
    assert all(isinstance(entry, dict) for entry in history)


def test_get_price_history_entry_count_matches_updates(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380)
    v._open_trade(quantity=1)
    last_date = datetime.datetime(2026, 4, 10, 0, 0)
    v.long_option._next(quote_datetime=last_date)
    v.short_option._next(quote_datetime=last_date)
    history = v.get_price_history()
    expected_keys = set(daily_updates_put_370.keys()) & set(daily_updates_put_380.keys())
    assert len(history) == len(expected_keys)


def test_get_price_history_first_entry_quote_datetime(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380)
    v._open_trade(quantity=1)
    history = v.get_price_history()
    assert history[0]['quote_datetime'] == OPEN_DT


def test_get_price_history_spread_price_is_long_minus_short(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380)
    v._open_trade(quantity=1)
    history = v.get_price_history()
    # 370 put price=2.31, 380 put price=3.78 at open
    assert history[0]['price'] == pytest.approx(-1.47, abs=0.01)


def test_get_price_history_pnl_is_zero_on_open_day(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380, fill_factor=1.0)
    v._open_trade(quantity=1)
    history = v.get_price_history()
    assert history[0]['pnl'] == pytest.approx(0.0, abs=0.01)


def test_get_price_history_pnl_second_entry(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380, fill_factor=1.0)
    v._open_trade(quantity=1)
    last_date = datetime.datetime(2026, 4, 10, 0, 0)
    v.long_option._next(quote_datetime=last_date)
    v.short_option._next(quote_datetime=last_date)
    history = v.get_price_history()
    # long pnl: (3.72 - 2.31) * 100 * 1 = 141.0
    # short pnl: (5.93 - 3.78) * 100 * -1 = -215.0
    # spread pnl = -74.0
    assert history[1]['pnl'] == pytest.approx(-74.0, abs=1.0)


def test_get_price_history_contains_expected_keys(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380)
    v._open_trade(quantity=1)
    history = v.get_price_history()
    expected_keys = {'quote_datetime', 'price', 'spot_price', 'pnl', 'pnl_pct',
                     'delta', 'gamma', 'theta', 'vega', 'rho', 'iv'}
    assert set(history[0].keys()) == expected_keys


def test_get_price_history_greeks_are_netted(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380)
    v._open_trade(quantity=1)
    history = v.get_price_history()
    # delta: -0.1426 - (-0.2218) = 0.0792
    assert history[0]['delta'] == pytest.approx(0.0792, abs=0.0001)


def test_get_price_history_bounded_by_close_date(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380)
    v._open_trade(quantity=1)
    close_dt = datetime.datetime(2026, 3, 19)
    v.long_option._next(quote_datetime=close_dt)
    v.short_option._next(quote_datetime=close_dt)
    v._close_trade(quote_datetime=close_dt)
    history = v.get_price_history()
    assert all(entry['quote_datetime'] <= close_dt for entry in history)
    assert history[-1]['quote_datetime'] == close_dt

def test_get_price_history_pnl_pct_second_entry(make_vertical, daily_updates_put_370, daily_updates_put_380):
    v = make_vertical(long_updates=daily_updates_put_370, short_updates=daily_updates_put_380, fill_factor=1.0)
    v._open_trade(quantity=1)
    last_date = datetime.datetime(2026, 4, 10, 0, 0)
    v.long_option._next(quote_datetime=last_date)
    v.short_option._next(quote_datetime=last_date)
    history = v.get_price_history()
    actual_pnl = history[1]['pnl']
    trade_price = abs(v.get_trade_price())
    expected_pct = round(actual_pnl / (trade_price * 100), 4)
    assert history[1]['pnl_pct'] == pytest.approx(expected_pct, abs=0.001)