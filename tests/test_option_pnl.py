"""
Tests for Option.get_unrealized_profit_loss, get_profit_loss, and
get_unrealized_profit_loss_percent.

get_profit_loss_percent (bug #3) is tested separately in its own module.

Test setup pattern:
  - Open trade at bid=ask=price so fill_factor doesn't affect entry
  - Set self.price directly to simulate price movement
  - For partial-close scenarios, construct close state directly to isolate
    the P&L math from close_trade's behavior

Expected values calculated by hand; see comment above each test.
"""
import pytest
import datetime

from options_framework.option import TradeCloseInfo
from options_framework.option_types import OptionPositionType, OptionStatus

QUOTE_DT = datetime.datetime(2026, 3, 17, 0, 0)

def _make_close_record(opt, *, quantity, price):
    """Build a TradeCloseInfo matching what close_trade would produce."""
    open_price = opt.trade_open_info.price
    if opt.position_type == OptionPositionType.LONG:
        profit_loss = (price - open_price) * 100 * quantity
    else:
        profit_loss = (open_price - price) * 100 * quantity

    return TradeCloseInfo(
        option_id=opt.option_id,
        instance_id=opt.instance_id,
        date=opt.quote_datetime,
        quantity=quantity,
        price=price,
        premium=0.0,
        profit_loss=profit_loss,
        profit_loss_percent=0.0,
        fees=0.0,
        spot_price=float(opt.spot_price),
    )


# ---------------------------------------------------------------------------
# Preconditions
# ---------------------------------------------------------------------------

def test_get_unrealized_profit_loss_raises_when_not_traded(make_put_option_380):
    opt = make_put_option_380()
    with pytest.raises(Exception, match="no transactions"):
        opt.get_unrealized_profit_loss()


def test_get_profit_loss_raises_when_not_traded(make_put_option_380):
    opt = make_put_option_380()
    with pytest.raises(Exception, match="not been traded"):
        opt.get_profit_loss()


def test_get_unrealized_profit_loss_percent_raises_when_not_traded(make_put_option_380):
    opt = make_put_option_380()
    with pytest.raises(Exception, match="no transactions"):
        opt.get_unrealized_profit_loss_percent()


# ---------------------------------------------------------------------------
# get_unrealized_profit_loss - no closes
# ---------------------------------------------------------------------------

def test_get_unrealized_profit_loss_long_at_profit(make_put_option_380):
    # Open 10 @ $2.00, price rises to $2.75
    # unrealized = (2.75 - 2.00) * 100 * 10 = +$750
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.price = 2.75

    assert opt.get_unrealized_profit_loss() == pytest.approx(750.0)


def test_get_unrealized_profit_loss_long_at_loss(make_put_option_380):
    # Open 10 @ $2.00, price drops to $1.50
    # unrealized = (1.50 - 2.00) * 100 * 10 = -$500
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.price = 1.50

    assert opt.get_unrealized_profit_loss() == pytest.approx(-500.0)


def test_get_unrealized_profit_loss_at_break_even(make_put_option_380):
    # Open 10 @ $2.00, price unchanged
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    assert opt.get_unrealized_profit_loss() == pytest.approx(0.0)


def test_get_unrealized_profit_loss_short_at_profit(make_put_option_380):
    # Open -10 @ $2.00, price drops to $1.25
    # unrealized = (1.25 - 2.00) * 100 * (-10) = +$750
    # (SHORT profits when price falls)
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
    opt.price = 1.25

    assert opt.get_unrealized_profit_loss() == pytest.approx(750.0)


def test_get_unrealized_profit_loss_short_at_loss(make_put_option_380):
    # Open -10 @ $2.00, price rises to $2.50
    # unrealized = (2.50 - 2.00) * 100 * (-10) = -$500
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
    opt.price = 2.50

    assert opt.get_unrealized_profit_loss() == pytest.approx(-500.0)


def test_get_unrealized_profit_loss_after_partial_close_covers_only_remaining(make_put_option_380):
    # Open 10 @ $2.00, close 4 (not relevant to unrealized math), remaining 6
    # Current price $3.00
    # unrealized = (3.00 - 2.00) * 100 * 6 = +$600   (ONLY the 6 still open)
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=4, price=2.50))
    opt.quantity = 6
    opt.price = 3.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_unrealized_profit_loss() == pytest.approx(600.0)


def test_get_unrealized_profit_loss_after_full_close_is_zero(make_put_option_380):
    # Fully closed: self.quantity = 0, so unrealized = 0
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.close_trade(quote_datetime=QUOTE_DT)

    assert opt.get_unrealized_profit_loss() == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# get_profit_loss - combines realized + unrealized
# ---------------------------------------------------------------------------

def test_get_profit_loss_long_no_closes_equals_unrealized(make_put_option_380):
    # Open 10 @ $2.00, price rises to $2.50
    # No realized -> should just be unrealized = (2.50-2.00)*100*10 = $500
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.price = 2.50

    assert opt.get_profit_loss() == pytest.approx(500.0)
    assert opt.get_profit_loss() == pytest.approx(opt.get_unrealized_profit_loss())


def test_get_profit_loss_short_no_closes_equals_unrealized(make_put_option_380):
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
    opt.price = 1.50

    # (1.50 - 2.00) * 100 * (-10) = +$500
    assert opt.get_profit_loss() == pytest.approx(500.0)
    assert opt.get_profit_loss() == pytest.approx(opt.get_unrealized_profit_loss())


def test_get_profit_loss_long_with_partial_close_sums_realized_and_unrealized(make_put_option_380):
    # Open 10 @ $2.00
    # Close 4 @ $2.50     realized = (2.50-2.00)*100*4 = +$200
    # Remaining 6 @ $3.00 unrealized = (3.00-2.00)*100*6 = +$600
    # Total = $800
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=4, price=2.50))
    opt.quantity = 6
    opt.price = 3.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss() == pytest.approx(800.0)


def test_get_profit_loss_short_with_partial_close_sums_realized_and_unrealized(make_put_option_380):
    # Open -10 @ $2.00
    # Close 4 @ $1.50     realized = (2.00-1.50)*100*4 = +$200
    # Remaining -6 @ $1.25 unrealized = (1.25-2.00)*100*(-6) = +$450
    # Total = $650
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=4, price=1.50))
    opt.quantity = -6
    opt.price = 1.25
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss() == pytest.approx(650.0)


def test_get_profit_loss_fully_closed_long_equals_realized_only(make_put_option_380):
    # Fully closed via single close at profit
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    opt.close_trade(quote_datetime=QUOTE_DT)

    # Realized = (3-2)*100*10 = $1000, unrealized = 0 (nothing open)
    assert opt.get_profit_loss() == pytest.approx(1000.0)


def test_get_profit_loss_mixed_outcomes_long(make_put_option_380):
    # Open 10 @ $2.00, close 4 @ $1.50 (loss), remaining 6 @ $2.20 (small gain)
    # realized = (1.50-2.00)*100*4 = -$200
    # unrealized = (2.20-2.00)*100*6 = +$120
    # total = -$80
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=4, price=1.50))
    opt.quantity = 6
    opt.price = 2.20
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss() == pytest.approx(-80.0)


def test_get_profit_loss_multiple_partial_closes(make_put_option_380):
    # Open 10 @ $2.00
    # Close 3 @ $2.50, realized +$150
    # Close 4 @ $1.80, realized -$80
    # Remaining 3 @ $2.10, unrealized +$30
    # Total = +$100
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=3, price=2.50))
    opt.trade_close_records.append(_make_close_record(opt, quantity=4, price=1.80))
    opt.quantity = 3
    opt.price = 2.10
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss() == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# get_unrealized_profit_loss_percent - price ratio on remaining contracts
# ---------------------------------------------------------------------------

def test_get_unrealized_profit_loss_percent_long_at_profit(make_put_option_380):
    # Open 10 @ $2.00, price $2.50
    # percent = (2.50 - 2.00) / 2.00 = 25%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.price = 2.50

    assert opt.get_unrealized_profit_loss_percent() == pytest.approx(0.25)


def test_get_unrealized_profit_loss_percent_long_at_loss(make_put_option_380):
    # Open 10 @ $2.00, price $1.50
    # percent = (1.50 - 2.00) / 2.00 = -25%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.price = 1.50

    assert opt.get_unrealized_profit_loss_percent() == pytest.approx(-0.25)


def test_get_unrealized_profit_loss_percent_short_at_profit(make_put_option_380):
    # Open -10 @ $2.00, price drops to $1.50
    # SHORT profit. percent should be +25%
    # Formula: ((1.50 - 2.00) / 2.00) * (-10 / 10) = -0.25 * -1 = +0.25
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
    opt.price = 1.50

    assert opt.get_unrealized_profit_loss_percent() == pytest.approx(0.25)


def test_get_unrealized_profit_loss_percent_short_at_loss(make_put_option_380):
    # Open -10 @ $2.00, price rises to $2.50
    # Formula: ((2.50 - 2.00) / 2.00) * (-10 / 10) = +0.25 * -1 = -0.25
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
    opt.price = 2.50

    assert opt.get_unrealized_profit_loss_percent() == pytest.approx(-0.25)


def test_get_unrealized_profit_loss_percent_after_partial_close(make_put_option_380):
    # Open 10 @ $2.00, close 4, remaining 6 at $2.50
    # unrealized % is on remaining only: (2.50-2.00)/2.00 = +25%
    # (partial close doesn't change the per-contract percent)
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=4, price=2.30))
    opt.quantity = 6
    opt.price = 2.50
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_unrealized_profit_loss_percent() == pytest.approx(0.25)


def test_get_unrealized_profit_loss_percent_returns_zero_when_fully_closed(make_put_option_380):
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.close_trade(quote_datetime=QUOTE_DT)

    assert opt.get_unrealized_profit_loss_percent() == 0.0


# ---------------------------------------------------------------------------
# Cross-function invariants
# ---------------------------------------------------------------------------

def test_get_profit_loss_equals_sum_of_close_records_pnl_plus_unrealized(make_put_option_380):
    """Structural invariant: get_profit_loss = sum(close.pnl) + unrealized"""
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=3, price=2.40))
    opt.trade_close_records.append(_make_close_record(opt, quantity=2, price=1.90))
    opt.quantity = 5
    opt.price = 2.15
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    realized = sum(r.profit_loss for r in opt.trade_close_records)
    unrealized = opt.get_unrealized_profit_loss()
    total = opt.get_profit_loss()

    assert total == pytest.approx(realized + unrealized)

# ---------------------------------------------------------------------------
# LONG at expiration
# ---------------------------------------------------------------------------

def test_close_trade_expired_long_otm_call_settles_worthless(make_call_option_380, settings_overrides):
    # Reproduces the row 5 scenario: LONG 442 call, spot 440.07 at expiry
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_call_option_380(strike=442)
    opt.bid, opt.ask, opt.price = 0.69, 0.69, 0.69
    opt.spot_price = 440.07
    opt.open_trade(quantity=40)

    # Stale quote from before expiration should be ignored once EXPIRED is set
    opt.bid, opt.ask, opt.price = 0.65, 0.75, 0.70
    opt.spot_price = 440.07
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    # Intrinsic for OTM call = max(440.07 - 442, 0) = 0
    assert rec.price == pytest.approx(0.0)
    # Full loss: (0 - 0.69) * 100 * 40 = -2760
    assert rec.profit_loss == pytest.approx(-2760.0)


def test_close_trade_expired_long_itm_call_settles_at_intrinsic(make_call_option_380, settings_overrides):
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    opt.spot_price = 99.0
    opt.open_trade(quantity=10)

    opt.spot_price = 105.0  # ITM at expiration
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    # Intrinsic = max(105 - 100, 0) = 5.00
    assert rec.price == pytest.approx(5.0)
    # P&L = (5.00 - 1.00) * 100 * 10 = +4000
    assert rec.profit_loss == pytest.approx(4000.0)


def test_close_trade_expired_long_otm_put_settles_worthless(make_put_option_380, settings_overrides):
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 0.50, 0.50, 0.50
    opt.spot_price = 101.0
    opt.open_trade(quantity=10)

    opt.spot_price = 105.0  # OTM at expiration
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    assert rec.price == pytest.approx(0.0)
    # Full loss: (0 - 0.50) * 100 * 10 = -500
    assert rec.profit_loss == pytest.approx(-500.0)


def test_close_trade_expired_long_itm_put_settles_at_intrinsic(make_put_option_380, settings_overrides):
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.spot_price = 99.0
    opt.open_trade(quantity=10)

    opt.spot_price = 95.0  # ITM at expiration
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    # Intrinsic = max(100 - 95, 0) = 5.00
    assert rec.price == pytest.approx(5.0)
    # P&L = (5.00 - 2.00) * 100 * 10 = +3000
    assert rec.profit_loss == pytest.approx(3000.0)


# ---------------------------------------------------------------------------
# SHORT at expiration - PCS and PMCC short leg scenarios
# ---------------------------------------------------------------------------

def test_close_trade_expired_short_otm_put_captures_full_premium(make_put_option_380, settings_overrides):
    # Classic PCS short leg expiring OTM - full credit captured
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 1.50, 1.50, 1.50
    opt.spot_price = 105.0
    opt.open_trade(quantity=-10)

    opt.spot_price = 105.0  # above strike, put is OTM
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    assert rec.price == pytest.approx(0.0)
    # Short profit = (entry - close) * 100 * qty = (1.50 - 0) * 100 * 10 = +1500
    assert rec.profit_loss == pytest.approx(1500.0)


def test_close_trade_expired_short_otm_call_captures_full_premium(make_call_option_380, settings_overrides):
    # PMCC short leg scenario: short weekly call expires worthless
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 0.80, 0.80, 0.80
    opt.spot_price = 95.0
    opt.open_trade(quantity=-10)

    opt.spot_price = 98.0  # below strike, call is OTM
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    assert rec.price == pytest.approx(0.0)
    # P&L = (0.80 - 0) * 100 * 10 = +800
    assert rec.profit_loss == pytest.approx(800.0)


def test_close_trade_expired_short_itm_put_settles_at_loss(make_put_option_380, settings_overrides):
    # Short put goes against you - spot drops below strike at expiration
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    opt.spot_price = 101.0
    opt.open_trade(quantity=-10)

    opt.spot_price = 97.0  # ITM, intrinsic = 3
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    assert rec.price == pytest.approx(3.0)
    # P&L = (1.00 - 3.00) * 100 * 10 = -2000
    assert rec.profit_loss == pytest.approx(-2000.0)


def test_close_trade_expired_short_itm_call_settles_at_loss(make_call_option_380, settings_overrides):
    # Short call goes against you - spot rips above strike
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 0.50, 0.50, 0.50
    opt.spot_price = 99.0
    opt.open_trade(quantity=-10)

    opt.spot_price = 104.0  # ITM, intrinsic = 4
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    assert rec.price == pytest.approx(4.0)
    # P&L = (0.50 - 4.00) * 100 * 10 = -3500
    assert rec.profit_loss == pytest.approx(-3500.0)


# ---------------------------------------------------------------------------
# Edge cases and settings interactions
# ---------------------------------------------------------------------------

def test_close_trade_expired_call_at_strike_is_worthless(make_call_option_380, settings_overrides):
    # Spot exactly at strike: intrinsic is zero (pin risk aside, it's zero)
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 0.50, 0.50, 0.50
    opt.spot_price = 99.0
    opt.open_trade(quantity=10)

    opt.spot_price = 100.0
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    assert rec.price == pytest.approx(0.0)


def test_close_trade_expired_ignores_fill_factor(make_call_option_380, settings_overrides):
    """
    Intrinsic settlement should not be blended with the mid via fill_factor.
    fill_factor models market microstructure; at expiration there is no
    market, just settlement.
    """
    settings_overrides(fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    opt.spot_price = 99.0
    opt.open_trade(quantity=10)

    # Leave a stale non-zero quote. If fill_factor blending leaks into the
    # expired branch: bid + 0.5*(price - bid) = 0.10 + 0.5*(0.30 - 0.10) = 0.20
    # Correct intrinsic: max(99 - 100, 0) = 0.0
    opt.bid, opt.ask, opt.price = 0.10, 0.50, 0.30
    opt.spot_price = 99.0
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    assert rec.price == pytest.approx(0.0)


def test_close_trade_expired_still_incurs_fees(make_call_option_380, settings_overrides):
    """Close fees apply to expired settlements same as live closes."""
    opt = make_call_option_380(strike=100, fill_factor=0.50, incur_fees=True, standard_fee=0.50)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    opt.spot_price = 95.0
    opt.open_trade(quantity=10)

    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    # Close fees: 10 contracts * $0.50 = $5.00
    assert rec.fees == pytest.approx(5.0)

def test_long_call_option_profitable_pnl(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=1)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    opt.close_trade(quote_datetime=QUOTE_DT)
    pnl = opt.get_profit_loss()
    pnl_pct = opt.get_profit_loss_percent()

    assert pnl == 100.0
    assert pnl_pct == 0.50

def test_long_call_option_unprofitable_pnl(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=1)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    opt.close_trade(quote_datetime=QUOTE_DT)
    pnl = opt.get_profit_loss()
    pnl_pct = opt.get_profit_loss_percent()

    assert pnl == -100.0
    assert pnl_pct == -0.50

def test_short_call_option_profitable_pnl(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-1)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    opt.close_trade(quote_datetime=QUOTE_DT)
    pnl = opt.get_profit_loss()
    pnl_pct = opt.get_profit_loss_percent()

    assert pnl == 100.0
    assert pnl_pct == 0.50

def test_short_call_option_unprofitable_pnl(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-1)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    opt.close_trade(quote_datetime=QUOTE_DT)
    pnl = opt.get_profit_loss()
    pnl_pct = opt.get_profit_loss_percent()

    assert pnl == -100.0
    assert pnl_pct == -0.50