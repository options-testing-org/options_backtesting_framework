import datetime
import pytest

from options_framework.option_types import OptionStatus
from options_framework.option import TradeOpenInfo, TradeCloseInfo
from conftest import capture_events
from unittest.mock import MagicMock, patch

INITIAL_CASH = 10_000.0
QUOTE_DT = datetime.datetime(2026, 3, 18)

# ── open_position ─────────────────────────────────────────────────────────────
def test_position_appended_to_positions(portfolio, make_single, mock_chain):
    single = make_single()
    portfolio.open_position(single, quantity=1)
    assert single in portfolio.positions


def test_open_premium_deducted_from_cash(portfolio, make_single, mock_chain):
    single = make_single()
    portfolio.open_position(single, quantity=1)
    expected_cash = INITIAL_CASH - single.get_trade_premium()
    assert portfolio.cash == pytest.approx(expected_cash)


def test_ticker_initialized_for_new_symbol(portfolio, make_single, mock_chain):
    single = make_single()
    portfolio.open_position(single, quantity=1)
    assert single.symbol in portfolio.option_chains


def test_ticker_not_reinitialized_for_existing_symbol(portfolio, make_single, mock_chain):
    single1 = make_single()
    portfolio.open_position(single1, quantity=1)
    chain_before = portfolio.option_chains[single1.symbol]

    single2 = make_single()
    portfolio.open_position(single2, quantity=1)
    assert portfolio.option_chains[single1.symbol] is chain_before


# ── close_position ────────────────────────────────────────────────────────────
@pytest.fixture
def opened(portfolio, make_single, mock_chain):
    """Portfolio with one long single already open."""
    single = make_single()
    portfolio.open_position(single, quantity=1)
    return portfolio, single

def test_position_removed_from_positions(opened):
    portfolio, single = opened
    dt = QUOTE_DT + datetime.timedelta(days=1)
    portfolio.current_datetime = dt
    single.option.quote_datetime = dt
    portfolio.close_position(single)
    assert single not in portfolio.positions

def test_position_added_to_closed_positions(opened):
    portfolio, single = opened
    dt = QUOTE_DT + datetime.timedelta(days=1)
    portfolio.current_datetime = dt
    single.option.quote_datetime = dt
    portfolio.close_position(single)
    assert single in portfolio.closed_positions

def test_position_closed_event_emitted(opened):
    portfolio, single = opened
    dt = QUOTE_DT + datetime.timedelta(days=1)
    portfolio.current_datetime = dt
    single.option.quote_datetime = dt
    events = capture_events(portfolio, 'position_closed')
    portfolio.close_position(single)
    assert len(events) == 1
    assert events[0]['args'][0] is single

def test_raises_if_position_not_in_positions(portfolio, make_single):
    single = make_single()  # never opened
    with pytest.raises(ValueError, match="not in open positions"):
        portfolio.close_position(single)


def test_on_option_open_transaction_completed_deducts_premium(portfolio):
    info = TradeOpenInfo(
        option_id=1, instance_id=1, date=QUOTE_DT, quantity=1,
        price=1.50, premium=150.00, fees=0.0, spot_price=380.0
    )
    portfolio.on_option_open_transaction_completed(info)
    assert portfolio.cash == pytest.approx(INITIAL_CASH - 150.00)


def test_on_option_close_transaction_completed_adds_premium(portfolio):
    portfolio.cash = 9_000.0
    info = TradeCloseInfo(
        option_id=1, instance_id=1, date=QUOTE_DT, quantity=1,
        price=1.20, premium=120.00, profit_loss=-30.0,
        profit_loss_percent=-0.20, fees=0.0, spot_price=380.0
    )
    portfolio.on_option_close_transaction_completed(info)
    assert portfolio.cash == pytest.approx(9_120.00)

# ── margin checks ────────────────────────────────────────────────────────

def test_insufficient_margin_raises_value_error(portfolio, make_single, mock_chain):
    portfolio.cash = 0.0
    single = make_single()
    with pytest.raises(ValueError, match="Insufficient margin"):
        portfolio.open_position(single, quantity=-1)

def test_cash_restored_after_margin_exception(portfolio, make_single, mock_chain):
    portfolio.cash = 0.0
    single = make_single()
    with pytest.raises(ValueError):
        portfolio.open_position(single, quantity=-1)
    assert portfolio.cash == pytest.approx(0.0)

def test_position_not_appended_after_margin_exception(portfolio, make_single, mock_chain):
    portfolio.cash = 0.0
    single = make_single()
    with pytest.raises(ValueError):
        portfolio.open_position(single, quantity=-1)
    assert single not in portfolio.positions

def test_margin_not_checked_for_long_positions(portfolio, make_single, mock_chain):
    # Zero cash would fail a margin check — but long positions skip it.
    portfolio.cash = 0.0
    single = make_single()
    portfolio.open_position(single, quantity=1)
    assert single in portfolio.positions

def test_margin_check_skipped_when_disabled(portfolio, make_single, mock_chain):
    portfolio.check_margin_on_open = False
    portfolio.cash = 0.0
    single = make_single()
    portfolio.open_position(single, quantity=-1)
    assert single in portfolio.positions


# ── next ──────────────────────────────────────────────────────────────────────
def test_updates_current_datetime(portfolio, mock_chain):
    new_dt = datetime.datetime(2026, 3, 18)
    portfolio.next(new_dt)
    assert portfolio.current_datetime == new_dt

def test_appends_datetime_and_value_to_close_values(portfolio, mock_chain):
    portfolio.next(QUOTE_DT)
    assert len(portfolio.close_values) == 1
    row = portfolio.close_values[0]
    assert row[0] == QUOTE_DT
    assert row[1] == pytest.approx(portfolio.current_value)

def test_emits_next_event(portfolio, mock_chain):
    events = capture_events(portfolio, 'next')
    portfolio.next(QUOTE_DT)
    assert len(events) == 1

def test_initializes_ticker_for_passed_symbol(portfolio, mock_chain):
    portfolio.next(QUOTE_DT, symbols='AAPL')
    assert 'AAPL' in portfolio.option_chains

def test_string_symbol_coerced_to_list(portfolio, mock_chain):
    # Should not raise TypeError treating a string as an iterable of chars.
    portfolio.next(QUOTE_DT, symbols='AAPL')
    assert 'AAPL' in portfolio.option_chains

def test_duplicate_symbol_not_reinitialized(portfolio, make_single, mock_chain):
    single = make_single()
    portfolio.open_position(single, quantity=1)
    chain_before = portfolio.option_chains[single.symbol]
    # Same symbol is both in open positions and passed explicitly.
    portfolio.next(QUOTE_DT, symbols=single.symbol)
    assert portfolio.option_chains[single.symbol] is chain_before

def test_unused_symbol_removed_after_next(portfolio, mock_chain):
    # Seed a ticker for a symbol that has no open position.
    portfolio._initialize_ticker('FAKE', QUOTE_DT)
    assert 'FAKE' in portfolio.option_chains
    portfolio.next(QUOTE_DT)
    assert 'FAKE' not in portfolio.option_chains


# ── on_option_expired ─────────────────────────────────────────────────────────
"""
on_option_expired fires when the Option emits option_expired.  The portfolio:
  1. Finds the parent position.
  2. Calls close_position if ALL legs are expired.
  3. Emits position_expired.

Note on double events: close_position emits position_closed, and then
on_option_expired also emits position_expired — so an expired position
triggers BOTH events.  Listeners bound to position_closed must be aware
they will also receive a position_expired for the same position.
"""
def test_close_position_called_when_all_options_expired(make_mock_position, portfolio):
    pos = make_mock_position(all_expired=True)
    portfolio.positions.append(pos)
    with patch.object(portfolio, 'close_position') as mock_close:
        portfolio.on_option_expired(instance_id=42)
    mock_close.assert_called_once_with(pos, pos.quantity)

def test_position_expired_event_emitted(make_mock_position, portfolio):
    pos = make_mock_position(all_expired=True)
    portfolio.positions.append(pos)
    events = capture_events(portfolio, 'position_expired')
    with patch.object(portfolio, 'close_position'):
        portfolio.on_option_expired(instance_id=42)
    assert len(events) == 1
    assert events[0]['args'][0] is pos

def test_both_position_closed_and_position_expired_fire(make_mock_position, portfolio):
    """
    Documents the double-event contract.  Listeners bound to position_closed
    generically will receive expired positions too — they must handle overlap.
    """
    pos = make_mock_position(all_expired=True)
    portfolio.positions.append(pos)
    closed_events = capture_events(portfolio, 'position_closed')
    expired_events = capture_events(portfolio, 'position_expired')

    # Simulate close_position emitting position_closed without running
    # the real trade-mechanics on the mock position.
    def fake_close(p, q):
        portfolio.emit('position_closed', p)

    with patch.object(portfolio, 'close_position', side_effect=fake_close):
        portfolio.on_option_expired(instance_id=42)

    assert len(closed_events) == 1
    assert len(expired_events) == 1

def test_close_not_called_when_only_some_options_expired(portfolio):
    """Multi-leg spread: only closes when every leg has expired."""
    opt1 = MagicMock()
    opt1.instance_id = 42
    opt1.status = OptionStatus.EXPIRED

    opt2 = MagicMock()
    opt2.instance_id = 43
    opt2.status = OptionStatus.TRADE_IS_OPEN  # still live

    pos = MagicMock()
    pos.options = [opt1, opt2]
    pos.instance_id = 99
    portfolio.positions.append(pos)

    with patch.object(portfolio, 'close_position') as mock_close:
        portfolio.on_option_expired(instance_id=42)
    mock_close.assert_not_called()

def test_raises_if_expired_option_not_found(portfolio):
    with pytest.raises(ValueError, match="Cannot find expired option"):
        portfolio.on_option_expired(instance_id=999)


# ── current_value ─────────────────────────────────────────────────────────────
def test_equals_cash_when_no_positions(portfolio):
    assert portfolio.current_value == pytest.approx(INITIAL_CASH)

def test_includes_value_of_open_positions(portfolio, make_single, mock_chain):
    single = make_single()
    portfolio.open_position(single, quantity=1)
    expected = portfolio.cash + sum(o.current_value for o in single.options)
    assert portfolio.current_value == pytest.approx(expected)

def test_updates_after_close(portfolio, make_single, mock_chain):
    single = make_single()
    portfolio.open_position(single, quantity=1)
    value_while_open = portfolio.current_value
    dt = QUOTE_DT + datetime.timedelta(days=1)
    portfolio.current_datetime = dt
    single.option.quote_datetime = dt
    portfolio.close_position(single)
    # After closing the value should just be cash (no open positions).
    assert portfolio.current_value == pytest.approx(portfolio.cash)


# ── on_fees_incurred ──────────────────────────────────────────────────────────
def test_fee_deducted_from_cash(portfolio):
    portfolio.on_fees_incurred(1.30)
    assert portfolio.cash == pytest.approx(INITIAL_CASH - 1.30)

def test_multiple_fees_accumulate(portfolio):
    portfolio.on_fees_incurred(0.65)
    portfolio.on_fees_incurred(0.65)
    assert portfolio.cash == pytest.approx(INITIAL_CASH - 1.30)


# ── portfolio_margin_allocation ───────────────────────────────────────────────

def test_zero_when_no_positions(portfolio):
    assert portfolio.portfolio_margin_allocation == pytest.approx(0.0)

def test_sums_margin_across_positions(portfolio, make_single, mock_chain):
    single1 = make_single()
    single2 = make_single()
    portfolio.cash = INITIAL_CASH*2
    portfolio.open_position(single1, quantity=-1)
    portfolio.open_position(single2, quantity=-1)
    expected = (single1.get_required_margin(-1) + single2.get_required_margin(-1))
    assert portfolio.portfolio_margin_allocation == pytest.approx(expected)