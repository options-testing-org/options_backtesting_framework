from __future__ import annotations

import copy
import datetime
import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from numpy import rec

from options_framework.option import Option, TradeCloseInfo, TradeOpenInfo
from options_framework.option_types import OptionPositionType, OptionStatus

# fixture_path = Path(__file__).parent / "fixtures"

QUOTE_DT = datetime.datetime(2026, 3, 17, 0, 0)

class _EventCapture(list):
    """A list that also holds a strong ref to a bound callback."""
    pass

def _capture_events(obj, event_name):
    """
    Subscribe to an event and return a list that accumulates emissions.
    The inner function is kept alive by being an attribute of the returned
    list object, which the test holds a reference to - this dodges
    pydispatch's weak-ref storage that silently drops lambdas.
    """
    captured = _EventCapture()

    def _listener(*args, **kwargs):
        captured.append({"args": args, "kwargs": kwargs})

    obj.bind(**{event_name: _listener})
    captured._listener = _listener  # strong ref, survives until test ends
    return captured

def _make_close_record(opt, *, quantity, price):
    """Build a TradeCloseInfo matching what close_trade would produce."""
    open_price = opt.trade_open_info.price
    if opt.position_type == OptionPositionType.LONG:
        profit_loss = (price - open_price) * 100 * quantity
    else:  # SHORT
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

def _sorted_update_keys(option):
    # updates is loaded on first open; keys are the available quote datetimes
    return sorted(option.updates.keys())

def test_close_without_quantity_closes_full_position(make_put_option_380, settings_overrides):
    settings_overrides(data_frequency='daily')
    option = make_put_option_380()
    option._open_trade(quantity=10)

    option._close_trade(quote_datetime=QUOTE_DT)

    assert option.quantity == 0
    assert OptionStatus.TRADE_IS_CLOSED in option.status
    assert OptionStatus.TRADE_IS_OPEN not in option.status

def test_long_partial_close_reduces_quantity(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=10)
    rec = option._close_trade(quote_datetime=QUOTE_DT, quantity=4)

    assert option.quantity == 6
    assert rec.quantity == 4
    assert OptionStatus.TRADE_IS_OPEN in option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status
    assert OptionStatus.TRADE_IS_CLOSED not in option.status

def test_short_partial_close_reduces_quantity(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=-10)
    rec = option._close_trade(quote_datetime=QUOTE_DT, quantity=3)

    assert option.quantity == -7
    assert rec.quantity == 3
    assert OptionStatus.TRADE_IS_OPEN in option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status
    assert OptionStatus.TRADE_IS_CLOSED not in option.status

def test_successive_partial_closes_fully_close_position(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=10)
    option._close_trade(quote_datetime=QUOTE_DT, quantity=2)

    assert option.quantity == 8
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status

    option._close_trade(quote_datetime=QUOTE_DT, quantity=8)


    assert option.quantity == 0
    assert OptionStatus.TRADE_IS_CLOSED in option.status
    assert OptionStatus.TRADE_IS_OPEN not in option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED not in option.status

def test_close_quantity_greater_than_open_raises(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=5)

    with pytest.raises(ValueError, match="greater than"):
        option._close_trade(quote_datetime=QUOTE_DT, quantity=15)


def test_close_quantity_zero_raises(make_put_option_380):
    opt = make_put_option_380()
    opt._open_trade(quantity=5)
    close_datetime = datetime.datetime(2026, 3, 18, 0, 0)

    with pytest.raises(ValueError):
        opt._close_trade(quote_datetime=close_datetime, quantity=0)

def test_close_quantity_negative_raises(make_put_option_380):
    opt = make_put_option_380()
    opt._open_trade(quantity=5)
    close_datetime = datetime.datetime(2026, 3, 18, 0, 0)

    with pytest.raises(ValueError):
        opt._close_trade(quote_datetime=close_datetime, quantity=-3)

def test_close_quantity_non_integer_raises(make_put_option_380):
    opt = make_put_option_380()
    opt._open_trade(quantity=5)
    close_datetime = datetime.datetime(2026, 3, 18, 0, 0)

    with pytest.raises((ValueError, TypeError)):
        opt._close_trade(quote_datetime=close_datetime, quantity=2.5)

def test_partial_close_records_preserve_each_close(make_put_option_380):
    opt = make_put_option_380()
    opt._open_trade(quantity=10)
    opt._close_trade(quote_datetime=QUOTE_DT, quantity=4)
    opt._close_trade(quote_datetime=QUOTE_DT, quantity=3)

    assert len(opt.trade_close_records) == 2
    assert opt.trade_close_records[0].quantity == 4
    assert opt.trade_close_records[1].quantity == 3
    assert opt.quantity == 3, "3 contracts should still be open"
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in opt.status

def test_close_before_open_raises(make_put_option_380):
    opt = make_put_option_380()

    with pytest.raises(ValueError, match="not open"):
        opt._close_trade(quote_datetime=QUOTE_DT)

def test_close_after_full_close_returns_trade_close_info(make_put_option_380):
    opt = make_put_option_380()
    opt._open_trade(quantity=5)
    first = opt._close_trade(quote_datetime=QUOTE_DT)

    with pytest.raises(ValueError, match="already closed"):
        second = opt._close_trade(quote_datetime=QUOTE_DT)

def test_get_closing_price_raises_error_when_not_opened(make_put_option_380):
    """INITIALIZED status - no trade ever opened."""
    opt = make_put_option_380()

    assert opt.status == OptionStatus.INITIALIZED

    with pytest.raises(ValueError, match="opening trade|not.*open|has.*no"):
        opt.get_closing_price()

def test_get_closing_price_long_returns_bid_with_zero_fill_factor(make_put_option_380):
    opt = make_put_option_380()
    opt._open_trade(quantity=5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.00)

def test_get_closing_price_short_returns_ask_with_zero_fill_factor(make_put_option_380):
    opt = make_put_option_380()
    opt._open_trade(quantity=-5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.20)

def test_get_closing_price_long_fill_factor_blends_bid_toward_mid(make_put_option_380, settings_overrides):
    opt = make_put_option_380(fill_factor=0.5)
    opt._open_trade(quantity=5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    # bid + 0.5*(price - bid) = 2.00 + 0.5*(2.10 - 2.00) = 2.05
    assert opt.get_closing_price() == pytest.approx(2.05)

def test_get_closing_price_short_fill_factor_blends_ask_toward_mid(make_put_option_380, settings_overrides):
    opt = make_put_option_380(fill_factor=0.5)
    opt._open_trade(quantity=-5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    # ask - 0.5*(ask - price) = 2.20 - 0.5*(2.20 - 2.10) = 2.15
    assert opt.get_closing_price() == pytest.approx(2.15)

def test_get_closing_price_long_fill_factor_one_returns_mid(make_put_option_380, settings_overrides):
    opt = make_put_option_380(fill_factor=1.0)
    opt._open_trade(quantity=5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.10)

def test_get_closing_price_short_fill_factor_one_returns_mid(make_put_option_380, settings_overrides):
    opt = make_put_option_380(fill_factor=1.0)
    opt._open_trade(quantity=-5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.10)

def test_get_closing_price_itm_call_returns_intrinsic(make_call_option_380):
    opt = make_call_option_380(strike=100)
    opt._open_trade(quantity=5)
    opt.spot_price = 105.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(5.0)

def test_get_closing_price_otm_call_returns_zero(make_call_option_380):
    opt = make_call_option_380(strike=100)
    opt._open_trade(quantity=5)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_atm_call_returns_zero(make_call_option_380):
    opt = make_call_option_380(strike=100)
    opt._open_trade(quantity=5)
    opt.spot_price = 100.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_itm_put_returns_intrinsic(make_put_option_380):
    opt = make_put_option_380(strike=100)
    opt._open_trade(quantity=5)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(5.0)

def test_get_closing_price_otm_put_returns_zero(make_put_option_380):
    opt = make_put_option_380(strike=100)
    opt._open_trade(quantity=5)
    opt.spot_price = 105.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_atm_put_returns_zero(make_put_option_380):
    opt = make_put_option_380(strike=100)
    opt._open_trade(quantity=5)
    opt.spot_price = 100.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_expired_after_close_still_returns_intrinsic(make_put_option_380):
    """Status can be both TRADE_IS_CLOSED and EXPIRED. Intrinsic still applies."""
    opt = make_put_option_380(strike=100)
    opt._open_trade(quantity=5)
    opt._close_trade(quote_datetime=QUOTE_DT)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    assert OptionStatus.TRADE_IS_CLOSED in opt.status
    assert opt.get_closing_price() == pytest.approx(5.0)

def test_get_profit_loss_percent_raises_when_not_traded(make_put_option_380):
    opt = make_put_option_380()
    with pytest.raises(Exception, match="not been traded"):
        opt.get_profit_loss_percent()

def test_get_profit_loss_percent_long_no_closes_at_profit(make_put_option_380):
    # Open 10 @ $2.00 (premium = +$2000), price moves to $3.00
    # P&L: (3-2)*100*10 = $1000 -> 1000/2000 = +50%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)
    opt.price = 3.00

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)

def test_get_profit_loss_percent_long_no_closes_at_loss(make_put_option_380):
    # Open 10 @ $2.00, price drops to $1.50
    # P&L: (1.50-2)*100*10 = -$500 -> -500/2000 = -25%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)
    opt.price = 1.50

    assert opt.get_profit_loss_percent() == pytest.approx(-0.25)

def test_get_profit_loss_percent_long_partial_close_at_profit(make_put_option_380):
    # Open 10 @ $2.00 (premium = +$2000)
    # Close 5 @ $2.50 (realized: (2.50-2)*100*5 = +$250)
    # Remaining 5 at $3.00 (unrealized: (3-2)*100*5 = +$500)
    # Total: $750 -> 750/2000 = +37.5%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=2.50))
    opt.quantity = 5
    opt.price = 3.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    pnl_pct = opt.get_profit_loss_percent()
    assert pnl_pct == pytest.approx(0.375)

def test_get_profit_loss_percent_long_partial_close_at_loss(make_put_option_380):
    # Open 10 @ $2.00, close 5 @ $1.50 (realized -$250), remaining 5 @ $1.00 (unrealized -$500)
    # Total: -$750 -> -750/2000 = -37.5%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=1.50))
    opt.quantity = 5
    opt.price = 1.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(-0.375)


def test_get_profit_loss_percent_long_partial_close_mixed_outcomes(make_put_option_380):
    # Open 10 @ $2.00, close 5 @ $1.50 (realized -$250), remaining 5 @ $2.10 (unrealized +$50)
    # Total: -$200 -> -200/2000 = -10%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=1.50))
    opt.quantity = 5
    opt.price = 2.10
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(-0.10)


def test_get_profit_loss_percent_long_multiple_partial_closes(make_put_option_380):
    # Open 10 @ $2.00
    # Close 3 @ $2.50 (realized: (2.50-2)*100*3 = +$150)
    # Close 4 @ $2.25 (realized: (2.25-2)*100*4 = +$100)
    # Remaining 3 @ $2.75 (unrealized: (2.75-2)*100*3 = +$225)
    # Total: $475 -> 475/2000 = +23.75%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=3, price=2.50))
    opt.trade_close_records.append(_make_close_record(opt, quantity=4, price=2.25))
    opt.quantity = 3
    opt.price = 2.75
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(0.2375)


def test_get_profit_loss_percent_long_fully_closed_at_profit(make_put_option_380):
    # Open 10 @ $2.00, fully close 10 @ $3.00
    # After full close: quantity=0, self.price set to close price ($3.00) by close_trade
    # Total: (3-2)*100*10 = $1000 -> 1000/2000 = +50%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=10, price=3.00))
    opt.quantity = 0
    opt.price = 3.00
    opt.status &= ~OptionStatus.TRADE_IS_OPEN
    opt.status |= OptionStatus.TRADE_IS_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)


def test_get_profit_loss_percent_long_fully_closed_at_loss(make_put_option_380):
    # Open 10 @ $2.00, fully close 10 @ $1.20
    # Total: (1.20-2)*100*10 = -$800 -> -800/2000 = -40%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=10, price=1.20))
    opt.quantity = 0
    opt.price = 1.20
    opt.status &= ~OptionStatus.TRADE_IS_OPEN
    opt.status |= OptionStatus.TRADE_IS_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(-0.40)

def test_get_profit_loss_percent_short_no_closes_at_profit(make_put_option_380):
    # Open -10 @ $2.00 (premium = -$2000, cash inflow), price drops to $1.00
    # Short profits when price drops: (2-1)*100*10 = +$1000 -> 1000/2000 = +50%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=-10)
    opt.price = 1.00

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)


def test_get_profit_loss_percent_short_no_closes_at_loss(make_put_option_380):
    # Open -10 @ $2.00, price rises to $2.75
    # Short loses when price rises: (2-2.75)*100*10 = -$750 -> -750/2000 = -37.5%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=-10)
    opt.price = 2.75

    assert opt.get_profit_loss_percent() == pytest.approx(-0.375)


# ---------------------------------------------------------------------------
# SHORT, with closes - accidentally correct, pinned as regression anchor
# ---------------------------------------------------------------------------

def test_get_profit_loss_percent_short_partial_close_at_profit(make_put_option_380):
    # Open -10 @ $2.00, close 5 @ $1.50 (realized: (2-1.5)*100*5 = +$250)
    # Remaining -5 at $1.00 (unrealized: (2-1)*100*5 = +$500)
    # Total: $750 -> 750/2000 = +37.5%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=-10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=1.50))
    opt.quantity = -5
    opt.price = 1.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(0.375)


def test_get_profit_loss_percent_short_partial_close_at_loss(make_put_option_380):
    # Open -10 @ $2.00, close 5 @ $2.50 (realized: (2-2.5)*100*5 = -$250)
    # Remaining -5 at $3.00 (unrealized: (2-3)*100*5 = -$500)
    # Total: -$750 -> -750/2000 = -37.5%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=-10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=2.50))
    opt.quantity = -5
    opt.price = 3.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(-0.375)


def test_get_profit_loss_percent_short_fully_closed_at_profit(make_put_option_380):
    # Open -10 @ $2.00, fully close 10 @ $1.00
    # Total: (2-1)*100*10 = +$1000 -> 1000/2000 = +50%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=-10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=10, price=1.00))
    opt.quantity = 0
    opt.price = 1.00
    opt.status &= ~OptionStatus.TRADE_IS_OPEN
    opt.status |= OptionStatus.TRADE_IS_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)

def test_open_trade_premium_long_is_positive(make_put_option_380):
    # Open 10 @ $2.00: cash out $2000 -> premium = +2000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    info = opt._open_trade(quantity=10)

    assert info.premium == pytest.approx(2000.0)

def test_open_trade_premium_short_is_negative(make_put_option_380):
    # Open -10 @ $2.00: cash in $2000 -> premium = -2000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    info = opt._open_trade(quantity=-10)

    assert info.premium == pytest.approx(-2000.0)

def test_close_trade_premium_long_full_close_is_positive(make_put_option_380):
    # Open LONG 10 @ $2.00, close 10 @ $3.00: sell-to-close, cash in $3000
    # premium should be -3000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    rec = opt._close_trade(quote_datetime=QUOTE_DT)

    assert rec.premium == pytest.approx(3000.0)

def test_close_trade_premium_short_full_close_is_negative(make_put_option_380):
    # Open SHORT -10 @ $2.00, close 10 @ $1.00: buy-to-close, cash out $1000
    # premium should be +1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=-10)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    rec = opt._close_trade(quote_datetime=QUOTE_DT)

    assert rec.premium == pytest.approx(-1000.0)


def test_close_trade_premium_long_partial_close_is_negative(make_put_option_380):
    # Open LONG 10 @ $2.00, partial close 4 @ $2.50: cash in $1000
    # premium should be -1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)
    opt.bid, opt.ask, opt.price = 2.50, 2.50, 2.50
    rec = opt._close_trade(quote_datetime=QUOTE_DT, quantity=4)


def test_close_trade_premium_short_partial_close_is_negative(make_put_option_380):
    # Open SHORT -10 @ $2.00, partial close 4 @ $1.50: cash out $600
    # premium should be +600
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=-10)
    opt.bid, opt.ask, opt.price = 1.50, 1.50, 1.50
    rec = opt._close_trade(quote_datetime=QUOTE_DT, quantity=4)

    assert rec.premium == pytest.approx(-600.0)

def test_close_trade_premium_sum_equals_pnl_long_profit(make_put_option_380):
    # Open 10 @ $2.00 (+2000), close 10 @ $3.00 (-3000)
    # sum = -1000  |  pnl = +1000  |  -pnl = -1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt._open_trade(quantity=10)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    close_rec = opt._close_trade(quote_datetime=QUOTE_DT)

    premium_sum = close_rec.premium - open_info.premium
    assert premium_sum == pytest.approx(close_rec.profit_loss)

def test_close_trade_premium_sum_equals_pnl_long_loss(make_put_option_380):
    # Open 10 @ $2.00 (+2000), close 10 @ $1.50 (-1500)
    # sum = +500  |  pnl = -500  |  -pnl = +500
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt._open_trade(quantity=10)
    opt.bid, opt.ask, opt.price = 1.50, 1.50, 1.50
    close_rec = opt._close_trade(quote_datetime=QUOTE_DT)

    premium_sum = close_rec.premium - open_info.premium
    assert premium_sum == pytest.approx(close_rec.profit_loss)


def test_close_trade_premium_sum_equals_pnl_short_profit(make_put_option_380):
    # Open -10 @ $2.00 (-2000), close 10 @ $1.00 (+1000)
    # sum = -1000  |  pnl = +1000  |  -pnl = -1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt._open_trade(quantity=-10)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    close_rec = opt._close_trade(quote_datetime=QUOTE_DT)

    premium_sum = close_rec.premium - open_info.premium
    assert premium_sum == pytest.approx(close_rec.profit_loss)


def test_close_trade_premium_sum_equals_pnl_short_loss(make_put_option_380):
    # Open -10 @ $2.00 (-2000), close 10 @ $3.00 (+3000)
    # sum = +1000  |  pnl = -1000  |  -pnl = +1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt._open_trade(quantity=-10)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    close_rec = opt._close_trade(quote_datetime=QUOTE_DT)

    premium_sum = close_rec.premium - open_info.premium
    assert premium_sum == pytest.approx(close_rec.profit_loss)

def test_close_trade_premium_sum_equals_pnl_long_multiple_partials(make_put_option_380):
    # Round-trip invariant still holds across multiple partial closes
    # Open 10 @ $2.00 (+2000)
    # Close 4 @ $2.50 (-1000, pnl +200)
    # Close 6 @ $3.00 (-1800, pnl +600)
    # premium_sum = -800  |  total pnl = +800  |  -pnl = -800
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt._open_trade(quantity=10)

    opt.bid, opt.ask, opt.price = 2.50, 2.50, 2.50
    rec1 = opt._close_trade(quote_datetime=QUOTE_DT, quantity=4)

    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    rec2 = opt._close_trade(quote_datetime=QUOTE_DT, quantity=6)

    premium_sum = (rec1.premium + rec2.premium) - open_info.premium
    total_pnl = rec1.profit_loss + rec2.profit_loss
    assert premium_sum == pytest.approx(total_pnl)

def test_close_trade_premium_aggregate_matches_sum_of_records_long(make_put_option_380):
    # Aggregate trade_close_info.premium should equal the sum of individual
    # close record premiums, under the same convention.
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    opt.bid, opt.ask, opt.price = 2.50, 2.50, 2.50
    rec1 = opt._close_trade(quote_datetime=QUOTE_DT, quantity=4)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    rec2 = opt._close_trade(quote_datetime=QUOTE_DT, quantity=6)

    expected_sum = rec1.premium + rec2.premium
    assert opt.trade_close_info.premium == pytest.approx(expected_sum)

def test_close_trade_premium_aggregate_matches_sum_of_records_short(make_put_option_380):
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=-10)

    opt.bid, opt.ask, opt.price = 1.50, 1.50, 1.50
    rec1 = opt._close_trade(quote_datetime=QUOTE_DT, quantity=4)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    rec2 = opt._close_trade(quote_datetime=QUOTE_DT, quantity=6)

    expected_sum = rec1.premium + rec2.premium
    assert opt.trade_close_info.premium == pytest.approx(expected_sum)


# ---------------------------------------------------------------------------
# Not yet expired - returns False, no side effects
# ---------------------------------------------------------------------------

def test_is_expired_before_expiration_date_returns_false(make_put_option_380):
    # Quote date well before expiration
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 1, 10, 0),
    )
    assert opt.is_expired() is False
    assert OptionStatus.EXPIRED not in opt.status


def test_is_expired_morning_of_expiration_returns_false(make_put_option_380):
    # 9:30 AM on expiration day - PM settled option not yet expired
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 15, 9, 30),
    )
    assert opt.is_expired() is False
    assert OptionStatus.EXPIRED not in opt.status


def test_is_expired_one_minute_before_settlement_returns_false(make_put_option_380):
    # 15:59 on expiration day - still one minute to go
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 15, 15, 59),
    )
    assert opt.is_expired() is False
    assert OptionStatus.EXPIRED not in opt.status


# ---------------------------------------------------------------------------
# Expired - returns True, sets EXPIRED flag, emits option_expired
# ---------------------------------------------------------------------------

def test_is_expired_at_settlement_time_returns_true(make_put_option_380):
    # Exactly 16:00 on expiration day - boundary, should expire
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 15, 16, 0),
    )
    assert opt.is_expired() is True
    assert OptionStatus.EXPIRED in opt.status


def test_is_expired_after_settlement_time_returns_true(make_put_option_380):
    # 16:15 on expiration day
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 15, 16, 15),
    )
    assert opt.is_expired() is True
    assert OptionStatus.EXPIRED in opt.status


def test_is_expired_day_after_expiration_returns_true(make_put_option_380):
    # Quote date past expiration, any time
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 1, 10, 0),
    )
    opt.quote_datetime = datetime.datetime(2024, 3, 16, 9, 30)
    assert opt.is_expired() is True
    assert OptionStatus.EXPIRED in opt.status


def test_is_expired_emits_option_expired_event(make_put_option_380):
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 15, 16, 0),
    )

    events = _capture_events(opt, "option_expired")
    opt.bind(option_expired=lambda *args, **kwargs: events.append((args, kwargs)))

    opt.is_expired()

    assert len(events) == 1
    event_vals = events[0]
    kwargs = event_vals['kwargs']
    assert kwargs.get("instance_id") == opt.instance_id


def test_is_expired_does_not_emit_when_not_expired(make_put_option_380):
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 1, 10, 0),
    )
    events = _capture_events(opt, "option_expired")
    opt.bind(option_expired=lambda *args, **kwargs: events.append((args, kwargs)))

    opt.is_expired()

    assert len(events) == 0


# ---------------------------------------------------------------------------
# Idempotency - re-calling on an already-expired option
# ---------------------------------------------------------------------------

def test_is_expired_idempotent_returns_true_on_second_call(make_put_option_380):
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 15, 16, 0),
    )
    assert opt.is_expired() is True
    assert opt.is_expired() is True


def test_is_expired_does_not_re_emit_on_second_call(make_put_option_380):
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 15, 16, 0),
    )
    events = _capture_events(opt, "option_expired")
    opt.bind(option_expired=lambda *args, **kwargs: events.append(kwargs))

    opt.is_expired()
    opt.is_expired()
    opt.is_expired()

    assert len(events) == 1, "option_expired should fire exactly once"


# ---------------------------------------------------------------------------
# Flag interaction - EXPIRED is a flag bit, coexists with other statuses
# ---------------------------------------------------------------------------

def test_is_expired_preserves_trade_is_open_flag(make_put_option_380):
    # An option can be both TRADE_IS_OPEN and EXPIRED simultaneously.
    # is_expired should OR-in EXPIRED without clearing other flags.
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 1, 10, 0),  # open before expiry
    )
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=5)
    assert OptionStatus.TRADE_IS_OPEN in opt.status

    # Advance to expiration
    opt.quote_datetime = datetime.datetime(2024, 3, 15, 16, 0)
    opt.is_expired()

    assert OptionStatus.EXPIRED in opt.status
    assert OptionStatus.TRADE_IS_OPEN in opt.status


def test_is_expired_preserves_trade_is_closed_flag(make_put_option_380):
    # An option can be closed before expiry and still reach expiry later.
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 1, 10, 0),
    )
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=5)
    close_datetime = datetime.datetime(2024, 3, 1, 10, 0)
    opt._close_trade(quote_datetime=close_datetime, )
    assert OptionStatus.TRADE_IS_CLOSED in opt.status

    opt.quote_datetime = datetime.datetime(2024, 3, 15, 16, 0)
    opt.is_expired()

    assert OptionStatus.EXPIRED in opt.status
    assert OptionStatus.TRADE_IS_CLOSED in opt.status


# ---------------------------------------------------------------------------
# Bug #4: pd.Timestamp should be accepted
# These fail on current code.
# ---------------------------------------------------------------------------

def test_is_expired_accepts_pd_timestamp_not_yet_expired(make_put_option_380):
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=pd.Timestamp("2024-03-01 10:00:00"),
    )
    assert opt.is_expired() is False


def test_is_expired_accepts_pd_timestamp_after_expiration(make_put_option_380):
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=pd.Timestamp("2024-03-15 16:00:00"),
    )
    assert opt.is_expired() is True
    assert OptionStatus.EXPIRED in opt.status


def test_is_expired_accepts_pd_timestamp_emits_event(make_put_option_380):
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=pd.Timestamp("2024-03-15 16:30:00"),
    )
    events = _capture_events(opt, "option_expired")
    opt.bind(option_expired=lambda *args, **kwargs: events.append(kwargs))

    opt.is_expired()

    assert len(events) == 1
    assert events[0]['kwargs'].get("instance_id") == opt.instance_id


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_close_trade_accepts_matching_quote_datetime(make_put_option_380):
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    # Matching datetime - should succeed
    rec = opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    assert rec.quantity == 10
    assert OptionStatus.TRADE_IS_CLOSED in opt.status


def test_close_trade_accepts_matching_pd_timestamp(make_put_option_380):
    """pd.Timestamp equals datetime.datetime for the same moment - should work."""
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    # Equivalent pd.Timestamp should satisfy the equality check
    rec = opt._close_trade(quote_datetime=pd.Timestamp("2024-03-01 10:00:00"))
    assert rec.quantity == 10


def test_close_trade_accepts_matching_datetime_when_self_is_pd_timestamp(make_put_option_380):
    """Reverse: option's quote_datetime is pd.Timestamp, caller passes datetime."""
    opt = make_put_option_380(quote_datetime=pd.Timestamp("2024-03-01 10:00:00"))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    rec = opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    assert rec.quantity == 10


def test_close_trade_accepts_matching_datetime_for_partial_close(make_put_option_380):
    """Validation applies to partial closes too."""
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    rec = opt._close_trade(
        quote_datetime=datetime.datetime(2024, 3, 1, 10, 0),
        quantity=4,
    )
    assert rec.quantity == 4
    assert opt.quantity == 6


# ---------------------------------------------------------------------------
# Mismatch - the core bug this guard prevents
# ---------------------------------------------------------------------------

def test_close_trade_raises_when_quote_datetime_before_option_datetime(make_put_option_380):
    """Closing at an earlier datetime than the option's current clock - reject."""
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    # Option is at 10:00, try to close at 9:30
    with pytest.raises(ValueError, match="mismatch"):
        opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 9, 30))


def test_close_trade_raises_when_quote_datetime_after_option_datetime(make_put_option_380):
    """Closing at a later datetime than the option's current clock - reject.

    This is the common bug: strategy forgot to call next() before close_trade(),
    so the option's bid/ask are stale.
    """
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    # Option is at 10:00, try to close at 14:00 without having called next()
    with pytest.raises(ValueError, match="mismatch"):
        opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 14, 0))


def test_close_trade_raises_on_different_date(make_put_option_380):
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    with pytest.raises(ValueError, match="mismatch"):
        opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 2, 10, 0))


def test_close_trade_mismatch_does_not_mutate_state(make_put_option_380):
    """
    A failed validation must leave the option fully intact - no partial close,
    no status change, no fees incurred, no close record appended.
    """
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    original_qty = opt.quantity
    original_status = opt.status
    original_fees = opt.total_fees
    original_close_records = list(opt.trade_close_records)

    with pytest.raises(ValueError):
        opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 14, 0))

    assert opt.quantity == original_qty
    assert opt.status == original_status
    assert opt.total_fees == original_fees
    assert opt.trade_close_records == original_close_records


# ---------------------------------------------------------------------------
# Required and typed
# ---------------------------------------------------------------------------

def test_close_trade_raises_when_quote_datetime_missing(make_put_option_380):
    """quote_datetime is required - omitting it is a TypeError (kw-only, no default)."""
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    with pytest.raises(TypeError, match="quote_datetime"):
        opt._close_trade()


def test_close_trade_raises_when_quote_datetime_is_none(make_put_option_380):
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    with pytest.raises(ValueError, match="quote_datetime"):
        opt._close_trade(quote_datetime=None)


def test_close_trade_raises_when_quote_datetime_is_wrong_type(make_put_option_380):
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    with pytest.raises(TypeError, match="datetime"):
        opt._close_trade(quote_datetime="2024-03-01 10:00:00")


def test_close_trade_raises_when_quote_datetime_is_date_not_datetime(make_put_option_380):
    """A datetime.date is not a datetime.datetime - should raise."""
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)

    with pytest.raises(TypeError, match="datetime"):
        opt._close_trade(quote_datetime=datetime.date(2024, 3, 1))


# ---------------------------------------------------------------------------
# Interaction with existing behaviors
# ---------------------------------------------------------------------------

def test_close_trade_validation_happens_before_status_check(make_put_option_380):
    """
    An already-closed option called with bad quote_datetime should get one
    consistent error. Either order is defensible; pinning current behavior.
    Update the expected error if you change the order intentionally.
    """
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt._open_trade(quantity=10)
    opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))

    # Second close attempt with mismatched datetime - should still raise
    with pytest.raises((ValueError, TypeError)):
        opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 14, 0))


def test_close_trade_works_at_expiration_when_datetimes_match(make_call_option_380):
    """Expired path still requires matching quote_datetime."""
    opt = make_call_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 1, 10, 0),
        strike=100,
    )
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    opt.spot_price = 99.0
    opt._open_trade(quantity=10)

    # Advance to expiration
    opt.quote_datetime = datetime.datetime(2024, 3, 15, 16, 0)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    # Must pass the matching datetime
    rec = opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 15, 16, 0))
    assert rec.price == pytest.approx(0.0)  # OTM call


def test_close_trade_rejects_mismatched_datetime_at_expiration(make_call_option_380):
    """Expired options must still validate quote_datetime - no bypass."""
    opt = make_call_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 1, 10, 0),
        strike=100,
    )
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    opt.spot_price = 99.0
    opt._open_trade(quantity=10)

    opt.quote_datetime = datetime.datetime(2024, 3, 15, 16, 0)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    with pytest.raises(ValueError, match="mismatch"):
        opt._close_trade(quote_datetime=datetime.datetime(2024, 3, 14, 16, 0))

# ---------------------------------------------------------------------------
# quote_datetime type enforcement
# ---------------------------------------------------------------------------

def test_construct_accepts_datetime_datetime_for_quote_datetime(make_put_option_380):
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    assert isinstance(opt.quote_datetime, datetime.datetime)


def test_construct_accepts_pd_timestamp_for_quote_datetime(make_put_option_380):
    """pd.Timestamp is accepted at construction."""
    opt = make_put_option_380(quote_datetime=pd.Timestamp("2024-03-01 10:00:00"))
    # Normalized to datetime.datetime after construction
    assert type(opt.quote_datetime) is datetime.datetime


def test_construct_rejects_date_for_quote_datetime(make_put_option_380):
    with pytest.raises((TypeError, ValueError), match="datetime"):
        make_put_option_380(quote_datetime=datetime.date(2024, 3, 1))


def test_construct_rejects_string_for_quote_datetime(make_put_option_380):
    with pytest.raises((TypeError, ValueError), match="datetime"):
        make_put_option_380(quote_datetime="2024-03-01 10:00:00")


def test_construct_rejects_none_for_quote_datetime(make_put_option_380):
    with pytest.raises(ValueError, match="quote_datetime"):
        make_put_option_380(quote_datetime=None)


# ---------------------------------------------------------------------------
# expiration type enforcement
# ---------------------------------------------------------------------------

def test_construct_accepts_date_for_expiration(make_put_option_380):
    opt = make_put_option_380()
    assert type(opt.expiration) is datetime.date


def test_construct_rejects_datetime_for_expiration(make_put_option_380):
    """
    datetime.datetime IS a subclass of datetime.date, but the invariant
    requires exactly datetime.date. Prevents the date-vs-datetime equality
    bug in is_expired().
    """
    with pytest.raises((TypeError, ValueError), match="expiration"):
        make_put_option_380(expiration=datetime.datetime(2024, 3, 15, 16, 0))


def test_construct_rejects_pd_timestamp_for_expiration(make_put_option_380):
    """pd.Timestamp is a datetime, not a date - should be rejected for expiration."""
    with pytest.raises((TypeError, ValueError), match="expiration"):
        make_put_option_380(expiration=pd.Timestamp("2024-03-15"))


def test_construct_rejects_string_for_expiration(make_put_option_380):
    with pytest.raises((TypeError, ValueError), match="expiration"):
        make_put_option_380(expiration="2024-03-15")


def test_construct_rejects_none_for_expiration(make_put_option_380):
    with pytest.raises(ValueError, match="expiration"):
        make_put_option_380(expiration=None)


# ---------------------------------------------------------------------------
# Post-construction: pd.Timestamp normalization
# ---------------------------------------------------------------------------

def test_pd_timestamp_is_normalized_to_datetime_after_construction(make_put_option_380):
    """
    pd.Timestamp accepted at construction but stored as datetime.datetime.
    Downstream code can rely on type(self.quote_datetime) is datetime.datetime.
    """
    ts = pd.Timestamp("2024-03-01 10:00:00")
    opt = make_put_option_380(quote_datetime=ts)

    # Exact type check - not just isinstance, since pd.Timestamp IS a datetime
    assert type(opt.quote_datetime) is datetime.datetime
    # Value preserved
    assert opt.quote_datetime == datetime.datetime(2024, 3, 1, 10, 0)


def test_pd_timestamp_quote_datetime_equality_with_plain_datetime(make_put_option_380):
    """After normalization, a pd.Timestamp-constructed option's quote_datetime
    compares equal to an equivalent datetime.datetime - needed for close_trade
    validation to work regardless of which type the caller passes."""
    opt = make_put_option_380(quote_datetime=pd.Timestamp("2024-03-01 10:00:00"))

    assert opt.quote_datetime == datetime.datetime(2024, 3, 1, 10, 0)


# ---------------------------------------------------------------------------
# is_expired interaction - regression pins for the date/datetime bug we hit
# ---------------------------------------------------------------------------

def test_is_expired_works_with_date_expiration_on_expiration_day(make_put_option_380):
    """
    Regression: previously, if expiration was a datetime.datetime instead of
    a datetime.date, is_expired() would silently return False on expiration
    day because date == datetime is False. Enforcing expiration: datetime.date
    makes this comparison work reliably.
    """
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 15, 16, 0),
    )
    assert opt.is_expired() is True


def test_is_expired_works_after_pd_timestamp_normalization(make_put_option_380):
    """pd.Timestamp at construction, datetime after - is_expired must work."""
    opt = make_put_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=pd.Timestamp("2024-03-15 16:00:00"),
    )
    assert opt.is_expired() is True


# ---------------------------------------------------------------------------
# next() preserves the invariant on updates
# ---------------------------------------------------------------------------

def test_next_accepts_datetime_datetime(make_put_option_380):
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt._next(datetime.datetime(2024, 3, 1, 10, 1))
    assert type(opt.quote_datetime) is datetime.datetime


def test_next_normalizes_pd_timestamp(make_put_option_380):
    """next() should apply the same normalization __post_init__ does."""
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt._next(pd.Timestamp("2024-03-01 10:01:00"))
    assert type(opt.quote_datetime) is datetime.datetime


def test_next_rejects_date(make_put_option_380):
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    with pytest.raises((TypeError, ValueError), match="datetime"):
        opt._next(datetime.date(2024, 3, 1))

def test_open_transaction_completed_fires_after_state_is_consistent(make_call_option_380):
    """
    Regression for bug #5: listeners that introspect the Option during the
    handler should see fully populated state. If the emit moves above the
    state assignments, this test fails immediately.
    """
    opt = make_call_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00

    observed = {}

    def inspector(info):
        observed["trade_open_info"] = opt.trade_open_info
        observed["quantity"] = opt.quantity
        observed["status"] = opt.status
        observed["updates_populated"] = bool(opt.updates)

    opt.bind(open_transaction_completed=inspector)
    opt._open_trade(quantity=10)

    assert observed["trade_open_info"] is not None
    assert observed["quantity"] == 10
    assert OptionStatus.TRADE_IS_OPEN in observed["status"]
    assert observed["updates_populated"], "updates not populated at emit time"

def test_option_incur_fees_defaults_from_settings_when_not_specified(
    make_call_option_380, settings_overrides,
):
    """When incur_fees kwarg is not passed, settings value is used."""
    settings_overrides(incur_fees=False, standard_fee=0.65)
    opt = make_call_option_380()  # no incur_fees kwarg
    assert opt.incur_fees is False


def test_option_incur_fees_kwarg_overrides_settings(
    make_call_option_380, settings_overrides,
):
    """Explicit incur_fees=True overrides settings incur_fees=False."""
    settings_overrides(incur_fees=False, standard_fee=0.65)
    opt = make_call_option_380(incur_fees=True)
    assert opt.incur_fees is True


def test_option_incur_fees_kwarg_false_overrides_settings(
    make_call_option_380, settings_overrides,
):
    """Explicit incur_fees=False overrides settings incur_fees=True."""
    settings_overrides(incur_fees=True, standard_fee=0.65)
    opt = make_call_option_380(incur_fees=False)
    assert opt.incur_fees is False


def test_option_fee_per_contract_defaults_from_settings(
    make_call_option_380, settings_overrides,
):
    opt = make_call_option_380(incur_fees=True, standard_fee=1.25)
    assert opt.fee_per_contract == 1.25


def test_option_fee_per_contract_kwarg_overrides_settings(
    make_call_option_380, settings_overrides,
):
    settings_overrides(incur_fees=True, standard_fee=0.65)
    opt = make_call_option_380(fee_per_contract=1.50)
    assert opt.fee_per_contract == 1.50


def test_option_fee_per_contract_kwarg_zero_overrides_settings(
    make_call_option_380, settings_overrides,
):
    """Zero is a legitimate override value — don't confuse it with 'unset'."""
    settings_overrides(incur_fees=True, standard_fee=0.65)
    opt = make_call_option_380(fee_per_contract=0.0)
    assert opt.fee_per_contract == 0.0


def test_option_dict_unpacking_with_overrides(make_call_option_380, settings_overrides):
    """Regression for the actual instantiation pattern: Option(**dict)."""
    settings_overrides(incur_fees=True, standard_fee=0.65)

    # Simulate the real-world pattern — overrides live in a dict alongside
    # required fields and get unpacked into the constructor.
    extras = {"incur_fees": False, "fee_per_contract": 1.00}

    opt = make_call_option_380(**extras)

    assert opt.incur_fees is False
    assert opt.fee_per_contract == 1.00


def test_option_dict_unpacking_without_overrides_uses_settings(
    make_call_option_380, settings_overrides,
):
    """When the dict doesn't include fee kwargs, settings apply."""
    extras = {'incur_fees': False, 'standard_fee': 2.50}  # no fee overrides in this dict

    opt = make_call_option_380(**extras)

    assert opt.incur_fees is False
    assert opt.fee_per_contract == 2.50


def test_option_fee_fields_actually_affect_open_trade_fees(
    make_call_option_380, settings_overrides,
):
    """End-to-end: a per-option fee override changes the fees on the trade."""
    opt = make_call_option_380(incur_fees=True, standard_fee=0.45, fee_per_contract=2.00)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00

    info = opt._open_trade(quantity=10)

    # 10 contracts * $2.00 override (not the $0.65 from settings) = $20
    assert info.fees == pytest.approx(20.00)


def test_option_incur_fees_false_override_disables_fees_even_when_settings_enabled(
    make_call_option_380, settings_overrides,
):
    opt = make_call_option_380(incur_fees=False)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00

    info = opt._open_trade(quantity=10)

    assert info.fees == 0
    assert opt.total_fees == 0


# ── LONG ──────────────────────────────────────────────────────────────────

def test_long_close_premium_is_positive(make_call_option_380):
    """Selling a long must yield a positive close_premium."""
    opt = make_call_option_380()
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86
    opt._open_trade(quantity=+1)

    opt.bid, opt.ask, opt.price = 0.75, 0.82, 0.79
    rec: TradeCloseInfo = opt._close_trade(quote_datetime=QUOTE_DT, quantity=1)

    # close_price = bid = 0.75  →  expected premium = +75
    assert rec.premium > 0, (
        f"LONG close_premium should be positive (cash received). Got {rec.premium}. "
        f"Sign is inverted — check the negation of action_qty in close_trade()."
    )
    assert rec.premium == pytest.approx(75.0), (
        f"Expected +75.00 (0.75 × 100 × 1 contract). Got {rec.premium}."
    )

def test_long_close_premium_multi_contract(make_call_option_380):
    """Premium magnitude scales with number of contracts closed."""
    opt = make_call_option_380()
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86
    opt._open_trade(quantity=+3)

    bid = 0.60
    ask = 0.68
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    rec: TradeCloseInfo = opt._close_trade(quote_datetime=QUOTE_DT, quantity=3)

    # 0.60 × 100 × 3 = 180
    assert rec.premium == pytest.approx(180.0)

def test_long_partial_close_premium(make_call_option_380):
    """Partial close of a long: only closed contracts contribute."""
    opt = make_call_option_380()
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86
    opt._open_trade(quantity=+4)

    bid = 0.70
    ask = 0.78
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    rec: TradeCloseInfo = opt._close_trade(quote_datetime=QUOTE_DT, quantity=2)

    # 0.70 × 100 × 2 = 140
    assert rec.premium == pytest.approx(140.0)
    assert OptionStatus.TRADE_IS_OPEN in opt.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in opt.status

    # ── SHORT ─────────────────────────────────────────────────────────────────

def test_short_close_premium_is_negative(make_call_option_380):
    """Buying back a short must yield a negative close_premium."""
    opt = make_call_option_380()
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86
    opt._open_trade(quantity=-1)

    bid = 0.75
    ask = 0.82
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    rec: TradeCloseInfo = opt._close_trade(quote_datetime=QUOTE_DT, quantity=1)

    # close_price = ask = 0.82  →  expected premium = -82
    assert rec.premium < 0, (
        f"SHORT close_premium should be negative (cash paid). Got {rec.premium}. "
        f"Sign is inverted — check the negation of action_qty in close_trade()."
    )
    assert rec.premium == pytest.approx(-82.0), (
        f"Expected -82.00 (0.82 × 100 × 1 contract). Got {rec.premium}."
    )

def test_short_close_premium_multi_contract(make_call_option_380):
    """Premium magnitude scales with number of contracts closed."""
    opt = make_call_option_380()
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86
    opt._open_trade(quantity=-3)

    bid = 0.70
    ask = 0.78
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    rec: TradeCloseInfo = opt._close_trade(quote_datetime=QUOTE_DT, quantity=3)

    # 0.78 × 100 × 3 = 234
    assert rec.premium == pytest.approx(-234.0)

def test_short_partial_close_premium(make_call_option_380):
    """Partial close of a short: only closed contracts contribute."""
    opt = make_call_option_380()
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86
    opt._open_trade(quantity=-4)

    bid = 0.70
    ask = 0.78
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    rec: TradeCloseInfo = opt._close_trade(quote_datetime=QUOTE_DT, quantity=2)

    # 0.78 × 100 × 2 = 156
    assert rec.premium == pytest.approx(-156.0)

    # ── Profit/loss is independent of the sign fix ─────────────────────────────

def test_long_profit_loss_sign_unaffected(make_call_option_380):
    """
    profit_loss in the close record is computed independently of close_premium
    and must not be changed by the fix.
    Long: close < open → loss (negative PnL).
    """
    opt = make_call_option_380(bid=0.82, ask=0.90, price=0.86)  # open at ask=0.90
    opt._open_trade(quantity=+1)

    #_set_close_quote(opt, bid=0.70, ask=0.78)  # close at bid=0.70
    bid = 0.70
    ask = 0.78
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    rec: TradeCloseInfo = opt._close_trade(quote_datetime=QUOTE_DT, quantity=1)

    # (0.70 - 0.90) × 100 × 1 = -20
    assert rec.profit_loss == pytest.approx(-20.0)

def test_short_profit_loss_sign_unaffected(make_call_option_380):
    """
    Short: close (ask) > open (bid) → loss (negative PnL).
    """
    opt = make_call_option_380(bid=0.82, ask=0.90, price=0.86)  # open at bid=0.82
    opt._open_trade(quantity=-1)

    # close at ask=0.96
    bid = 0.88
    ask = 0.96
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    rec: TradeCloseInfo = opt._close_trade(quote_datetime=QUOTE_DT, quantity=1)

    # (0.82 - 0.96) × 100 × 1 = -14
    assert rec.profit_loss == pytest.approx(-14.0)


"""
   Verify that _calculate_trade_close_info() correctly accumulates premium
   across multiple partial closes.
   """


def test_single_close_aggregate_matches_record(make_call_option_380):
    """After a full one-lot close, trade_close_info.premium equals the record."""
    opt = make_call_option_380(bid=0.82, ask=0.90, price=0.86)
    opt._open_trade(quantity=+1)

    #_set_close_quote(opt, bid=0.70, ask=0.78)
    bid = 0.70
    ask = 0.78
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    opt._close_trade(quote_datetime=QUOTE_DT, quantity=1)

    assert opt.trade_close_info.premium == pytest.approx(
        opt.trade_close_records[0].premium
    )


def test_multi_partial_close_aggregate_sums_correctly(make_call_option_380):
    """
    Two partial closes: aggregate premium should be the sum of both records.
    Both records must have the same sign (positive for long closes).
    """
    opt = make_call_option_380(bid=0.82, ask=0.90, price=0.86)
    opt._open_trade(quantity=+4)

    bid = 0.70
    ask = 0.78
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    opt._close_trade(quote_datetime=QUOTE_DT, quantity=2)  # +140

    bid = 0.65
    ask = 0.72
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    opt._close_trade(quote_datetime=QUOTE_DT, quantity=2)  # +130

    # Aggregate: 140 + 130 = 270
    total_record_premium = sum(r.premium for r in opt.trade_close_records)
    assert total_record_premium == pytest.approx(270.0)
    assert opt.trade_close_info.premium == pytest.approx(270.0)

# ─── Integration tests: OptionPortfolio cash accounting ───────────────────────
"""
End-to-end cash accounting through OptionPortfolio.
These are the regression tests for the original bug report.

Sign table (fill_factor=0, no fees):
    Action        Fill price   open_premium   cash effect
    ──────────────────────────────────────────────────────
    LONG  open    ask=0.90     +90            cash − 90
    SHORT open    bid=0.82     −82            cash + 82
    LONG  close   bid=X        +X×100         cash + X×100
    SHORT close   ask=X        −X×100         cash − X×100
"""


# ── Open side (already working, sanity check) ──────────────────────────────

def test_long_open_deducts_cash(make_portfolio, make_single):
    """Opening a long deducts the ask premium from cash."""
    portfolio = make_portfolio(cash=10_000.0)
    single = make_single()
    single.option.bid, single.option.ask, single.option.price = 0.82, 0.90, 0.86

    portfolio.open_position(single, quantity=1)

    assert portfolio.cash == pytest.approx(10_000.0 - 0.90 * 100)


def test_short_open_credits_cash(make_portfolio, make_single):
    """Opening a short credits the bid premium to cash."""
    portfolio = make_portfolio(cash=10_000.0)
    single = make_single()
    single.option.bid, single.option.ask, single.option.price = 0.82, 0.90, 0.86

    portfolio.open_position(single, quantity=-1)

    assert portfolio.cash == pytest.approx(10_000.0 + 0.82 * 100)


# ── Close side (the bug) ───────────────────────────────────────────────────

def test_long_close_adds_cash(make_portfolio, make_single):
    """
    CORE REGRESSION: closing a long must add cash.
    Before fix: cash += -75 (decreases). After fix: cash += +75 (increases).
    """
    portfolio = make_portfolio(cash=10_000.0)
    single = make_single()
    opt = single.option
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86

    portfolio.open_position(single, quantity=1)
    cash_after_open = portfolio.cash  # 10_000 − 90 = 9_910

    #_set_close_quote(opt, bid=0.75, ask=0.82)
    bid = 0.75
    ask = 0.82
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    portfolio.close_position(single, quantity=1)

    # Sold at bid=0.75 → receive $75
    expected = cash_after_open + 75.0
    assert portfolio.cash == pytest.approx(expected), (
        f"LONG close should add $75 to cash. "
        f"Expected {expected:.2f}, got {portfolio.cash:.2f}. "
        f"close_premium sign is likely still inverted."
    )


def test_short_close_deducts_cash(make_portfolio, make_single):
    """
    CORE REGRESSION: closing a short (buying back) must cost cash.
    Before fix: cash += +82 (increases). After fix: cash += -82 (decreases).
    """
    portfolio = make_portfolio(cash=10_000.0)
    single = make_single()
    opt = single.option
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86

    portfolio.open_position(single, quantity=-1)
    cash_after_open = portfolio.cash  # 10_000 + 82 = 10_082

    bid = 0.75
    ask = 0.82
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    portfolio.close_position(single, quantity=1)

    # Bought back at ask=0.82 → pay $82
    expected = cash_after_open - 82.0
    assert portfolio.cash == pytest.approx(expected), (
        f"SHORT close should deduct $82 from cash. "
        f"Expected {expected:.2f}, got {portfolio.cash:.2f}. "
        f"close_premium sign is likely still inverted."
    )


# ── Full round-trips ───────────────────────────────────────────────────────

def test_long_round_trip_loss(make_portfolio, make_single):
    """Buy high, sell low → net loss reflected in cash."""
    portfolio = make_portfolio(cash=10_000.0)
    single = make_single()
    opt = single.option
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86

    portfolio.open_position(single, quantity=1)  # pay $90

    bid = 0.70
    ask = 0.78
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    portfolio.close_position(single, quantity=1)  # receive $70

    # Net: −90 + 70 = −$20
    assert portfolio.cash == pytest.approx(10_000.0 - 90.0 + 70.0)


def test_short_round_trip_profit(make_portfolio, make_single):
    """Sell high, buy back lower → net profit in cash."""
    portfolio = make_portfolio(cash=10_000.0)
    single = make_single()
    opt = single.option
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86

    portfolio.open_position(single, quantity=-1)  # receive $82

    bid = 0.55
    ask = 0.62
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    portfolio.close_position(single, quantity=1)  # pay $62

    # Net: +82 − 62 = +$20
    assert portfolio.cash == pytest.approx(10_000.0 + 82.0 - 62.0)


def test_long_round_trip_profit(make_portfolio, make_single):
    """Buy low, sell high → net profit in cash."""
    portfolio = make_portfolio(cash=10_000.0)
    single = make_single()
    opt = single.option
    opt.bid, opt.ask, opt.price = 0.40, 0.50, 0.45

    portfolio.open_position(single, quantity=1)  # pay $50

    bid = 0.80
    ask = 0.90
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    portfolio.close_position(single, quantity=1)  # receive $80

    # Net: −50 + 80 = +$30
    assert portfolio.cash == pytest.approx(10_000.0 - 50.0 + 80.0)


def test_short_round_trip_loss(make_portfolio, make_single):
    """Sell low, buy back higher → net loss in cash."""
    portfolio = make_portfolio(cash=10_000.0)
    single = make_single()
    opt = single.option
    opt.bid, opt.ask, opt.price = 0.40, 0.50, 0.45

    portfolio.open_position(single, quantity=-1)  # receive $40

    bid = 0.75
    ask = 0.85
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    portfolio.close_position(single, quantity=1)  # pay $85

    # Net: +40 − 85 = −$45
    assert portfolio.cash == pytest.approx(10_000.0 + 40.0 - 85.0)


# ── Multi-contract ─────────────────────────────────────────────────────────

def test_long_multi_contract_close(make_portfolio, make_single):
    """Premium scales correctly with contract count."""
    portfolio = make_portfolio(cash=10_000.0)
    single = make_single()
    opt = single.option
    opt.bid, opt.ask, opt.price = 0.82, 0.90, 0.86

    portfolio.open_position(single, quantity=3)  # pay 3 × $90 = $270

    # _set_close_quote(opt, bid=0.70, ask=0.78)
    bid = 0.70
    ask = 0.78
    price = round((bid + ask) / 2, 4)
    opt.bid, opt.ask, opt.price = bid, ask, price
    portfolio.close_position(single, quantity=3)  # receive 3 × $70 = $210

    assert portfolio.cash == pytest.approx(10_000.0 - 270.0 + 210.0)


# ── first open now populates trade_open_records ───────────────────────────────

def test_open_trade_first_open_appends_to_trade_open_records(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=-1)
    assert len(option.trade_open_records) == 1


def test_open_trade_first_open_record_is_returned_value(make_put_option_380):
    option = make_put_option_380()
    rec = option._open_trade(quantity=-1)
    assert option.trade_open_records[0] is rec


def test_open_trade_first_open_trade_open_info_matches_record(make_put_option_380):
    option = make_put_option_380()
    rec = option._open_trade(quantity=-1)
    assert option.trade_open_info.price == rec.price
    assert option.trade_open_info.quantity == rec.quantity
    assert option.trade_open_info.premium == rec.premium
    assert option.trade_open_info.fees == rec.fees


# ── scale-in: quantity accumulation ──────────────────────────────────────────

def test_open_trade_scale_in_long_accumulates_quantity(make_call_option_380):
    option = make_call_option_380()
    option._open_trade(quantity=2)
    option._open_trade(quantity=3)
    assert option.quantity == 5


def test_open_trade_scale_in_short_accumulates_quantity(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=-2)
    option._open_trade(quantity=-1)
    assert option.quantity == -3


# ── scale-in: trade_open_records ─────────────────────────────────────────────

def test_open_trade_scale_in_appends_a_record_per_open(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=-1)
    option._open_trade(quantity=-2)
    assert len(option.trade_open_records) == 2


def test_open_trade_scale_in_records_store_individual_lot_quantities(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=-1)
    option._open_trade(quantity=-2)
    assert option.trade_open_records[0].quantity == -1
    assert option.trade_open_records[1].quantity == -2


# ── scale-in: trade_open_info weighted average ───────────────────────────────

def test_open_trade_scale_in_trade_open_info_weighted_average_price(make_call_option_380):
    # First open:  ask=2.10, qty=2  → fill=2.10, notional=4.20
    # Second open: ask=3.20, qty=3  → fill=3.20, notional=9.60
    # Weighted avg = 13.80 / 5 = 2.76
    option = make_call_option_380(bid=1.90, ask=2.10, price=2.00, fill_factor=0)
    option._open_trade(quantity=2)

    option.bid = 2.80
    option.ask = 3.20
    option.price = 3.00
    option._open_trade(quantity=3)

    assert option.trade_open_info.price == pytest.approx(2.76, abs=0.01)


def test_open_trade_scale_in_trade_open_info_total_premium(make_call_option_380):
    # First open:  fill=2.10, qty=2  → premium = 2.10 * 100 * 2 = 420.00
    # Second open: fill=3.20, qty=3  → premium = 3.20 * 100 * 3 = 960.00
    # Total premium = 1380.00
    option = make_call_option_380(bid=1.90, ask=2.10, price=2.00, fill_factor=0)
    option._open_trade(quantity=2)

    option.bid = 2.80
    option.ask = 3.20
    option.price = 3.00
    option._open_trade(quantity=3)

    assert option.trade_open_info.premium == pytest.approx(1380.0, abs=0.01)


def test_open_trade_scale_in_trade_open_info_total_quantity(make_call_option_380,):
    option = make_call_option_380()
    option._open_trade(quantity=2)
    option._open_trade(quantity=3)
    assert option.trade_open_info.quantity == 5


def test_open_trade_scale_in_trade_open_info_uses_latest_date(make_put_option_380):
    # trade_open_info.date should reflect the most recent open lot's datetime
    option = make_put_option_380()
    option._open_trade(quantity=-1)
    first_date = option.trade_open_info.date
    option._open_trade(quantity=-1)
    # both opens happen at the same quote_datetime in this fixture, so dates match;
    # what matters is that date comes from records[-1], not records[0]
    assert option.trade_open_info.date == option.trade_open_records[-1].date


# ── scale-in: event emission ──────────────────────────────────────────────────

def test_open_trade_scale_in_emits_individual_lot_not_aggregate(make_put_option_380):
    # open_transaction_completed must carry the individual scale-in lot,
    # NOT the aggregate trade_open_info.
    option = make_put_option_380(bid=1.90, ask=2.10, price=2.00, fill_factor=0)
    option._open_trade(quantity=-1)

    option.bid = 1.50
    option.ask = 1.70
    option.price = 1.60

    emitted_lots = []

    def _capture(lot):
        emitted_lots.append(lot)

    option.bind(open_transaction_completed=_capture)

    rec = option._open_trade(quantity=-2)

    assert len(emitted_lots) == 1
    emitted = emitted_lots[0]
    # emitted is the individual lot
    assert emitted is rec
    assert emitted.quantity == -2
    # SHORT fills at bid — 1.50 with fill_factor=0
    assert emitted.price == pytest.approx(1.50, abs=0.01)
    # aggregate would have quantity=-3 and a blended price; confirm it's not that
    assert emitted is not option.trade_open_info


# ── scale-in: DB not reloaded ─────────────────────────────────────────────────

def test_open_trade_db_loaded_only_on_first_open(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=-1)
    call_count = option.db.get_contract_updates.call_count
    option._open_trade(quantity=-1)
    assert option.db.get_contract_updates.call_count == call_count


# ── scale-in: fees ───────────────────────────────────────────────────────────

def test_open_trade_scale_in_fees_accumulate_in_trade_open_info(make_put_option_380):
    # 2 contracts + 3 contracts at $0.65/contract = $3.25
    option = make_put_option_380(incur_fees=True, standard_fee=0.65)
    option._open_trade(quantity=-2)
    option._open_trade(quantity=-3)
    assert option.trade_open_info.fees == pytest.approx(3.25, abs=0.01)


def test_open_trade_scale_in_total_fees_field_accumulates(make_put_option_380):
    option = make_put_option_380(incur_fees=True, standard_fee=0.65)
    option._open_trade(quantity=-2)
    option._open_trade(quantity=-3)
    assert option.total_fees == pytest.approx(3.25, abs=0.01)


# ── scale-in: downstream PnL consumers ───────────────────────────────────────

def test_open_trade_scale_in_unrealized_pnl_uses_weighted_average_price(make_call_option_380):
    # First open:  fill=2.10, qty=2
    # Second open: fill=3.20, qty=3  →  weighted avg = 2.76, total qty = 5
    # current price after second open = 3.00
    # unrealized PnL = (3.00 - 2.76) * 100 * 5 = 120.00
    option = make_call_option_380(bid=1.90, ask=2.10, price=2.00, fill_factor=0)
    option._open_trade(quantity=2)

    option.bid = 2.80
    option.ask = 3.20
    option.price = 3.00
    option._open_trade(quantity=3)

    assert option.get_unrealized_profit_loss() == pytest.approx(120.0, abs=0.01)


# ── guard conditions ──────────────────────────────────────────────────────────

def test_open_trade_opposite_direction_raises(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=-1)
    with pytest.raises(ValueError, match="opposite direction"):
        option._open_trade(quantity=1)


def test_open_trade_on_closed_position_raises(make_put_option_380):

    option = make_put_option_380()
    option._open_trade(quantity=-1)
    option._close_trade(quote_datetime=option.quote_datetime)
    with pytest.raises(ValueError, match="closed"):
        option._open_trade(quantity=-1)


def test_open_trade_status_remains_trade_is_open_after_scale_in(make_put_option_380):
    option = make_put_option_380()
    option._open_trade(quantity=-1)
    option._open_trade(quantity=-2)
    assert OptionStatus.TRADE_IS_OPEN in option.status
    assert OptionStatus.INITIALIZED not in option.status


def test_trade_open_info_date_single_open_uses_that_open(make_put_option_380):
    option = make_put_option_380()
    open_dt = option.quote_datetime

    option._open_trade(quantity=-1)

    # With a single open lot, the aggregate date is simply that open's date.
    assert option.trade_open_info.date == open_dt
    assert option.trade_open_info.quantity == -1
    assert len(option.trade_open_records) == 1
    assert option.trade_open_records[0].date == open_dt


def test_trade_open_info_date_pins_to_first_open_after_scale_in(make_put_option_380):
    option = make_put_option_380()
    first_dt = option.quote_datetime

    # First open at the initial quote datetime.
    option._open_trade(quantity=-1)

    # Advance the clock to a later available quote datetime, then scale in.
    keys = _sorted_update_keys(option)
    later_keys = [k for k in keys if k > first_dt]
    # Assumption: the put-380 fixture has at least one quote after the open date.
    assert later_keys, "fixture must contain a quote after the first open date"
    scale_in_dt = later_keys[0]

    option._next(scale_in_dt)
    option._open_trade(quantity=-2)

    # The aggregate date must remain the FIRST open, not the scale-in date.
    assert option.trade_open_info.date == first_dt
    assert option.trade_open_info.date != scale_in_dt

    # Per-lot records preserve both dates in order.
    assert len(option.trade_open_records) == 2
    assert option.trade_open_records[0].date == first_dt
    assert option.trade_open_records[-1].date == scale_in_dt

    # Aggregate quantity sums both lots (same direction).
    assert option.trade_open_info.quantity == -3


def test_trade_open_info_date_unchanged_by_partial_close(make_put_option_380):
    option = make_put_option_380()
    first_dt = option.quote_datetime

    option._open_trade(quantity=-3)

    keys = _sorted_update_keys(option)
    later_keys = [k for k in keys if k > first_dt]
    assert later_keys, "fixture must contain a quote after the first open date"
    close_dt = later_keys[0]

    option._next(close_dt)
    option._close_trade(quote_datetime=close_dt, quantity=1)

    # Closing part of the position does not touch the open date.
    assert option.trade_open_info.date == first_dt
    assert option.trade_open_info.quantity == -3  # open aggregate is unchanged by closes