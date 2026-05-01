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


def test_close_without_quantity_closes_full_position(make_put_option_380, settings_overrides):
    settings_overrides(data_frequency='daily')
    option = make_put_option_380()
    option.open_trade(quantity=10)

    option.close_trade(quote_datetime=QUOTE_DT)

    assert option.quantity == 0
    assert OptionStatus.TRADE_IS_CLOSED in option.status
    assert OptionStatus.TRADE_IS_OPEN not in option.status

def test_long_partial_close_reduces_quantity(make_put_option_380):
    option = make_put_option_380()
    option.open_trade(quantity=10)
    rec = option.close_trade(quote_datetime=QUOTE_DT, quantity=4)

    assert option.quantity == 6
    assert rec.quantity == 4
    assert OptionStatus.TRADE_IS_OPEN in option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status
    assert OptionStatus.TRADE_IS_CLOSED not in option.status

def test_short_partial_close_reduces_quantity(make_put_option_380):
    option = make_put_option_380()
    option.open_trade(quantity=-10)
    rec = option.close_trade(quote_datetime=QUOTE_DT, quantity=3)

    assert option.quantity == -7
    assert rec.quantity == 3
    assert OptionStatus.TRADE_IS_OPEN in option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status
    assert OptionStatus.TRADE_IS_CLOSED not in option.status

def test_successive_partial_closes_fully_close_position(make_put_option_380):
    option = make_put_option_380()
    option.open_trade(quantity=10)
    option.close_trade(quote_datetime=QUOTE_DT, quantity=2)

    assert option.quantity == 8
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status

    option.close_trade(quote_datetime=QUOTE_DT, quantity=8)


    assert option.quantity == 0
    assert OptionStatus.TRADE_IS_CLOSED in option.status
    assert OptionStatus.TRADE_IS_OPEN not in option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED not in option.status

def test_close_quantity_greater_than_open_raises(make_put_option_380):
    option = make_put_option_380()
    option.open_trade(quantity=5)

    with pytest.raises(ValueError, match="greater than"):
        option.close_trade(quote_datetime=QUOTE_DT, quantity=15)


def test_close_quantity_zero_raises(make_put_option_380):
    opt = make_put_option_380()
    opt.open_trade(quantity=5)
    close_datetime = datetime.datetime(2026, 3, 18, 0, 0)

    with pytest.raises(ValueError):
        opt.close_trade(quote_datetime=close_datetime, quantity=0)

def test_close_quantity_negative_raises(make_put_option_380):
    opt = make_put_option_380()
    opt.open_trade(quantity=5)
    close_datetime = datetime.datetime(2026, 3, 18, 0, 0)

    with pytest.raises(ValueError):
        opt.close_trade(quote_datetime=close_datetime, quantity=-3)

def test_close_quantity_non_integer_raises(make_put_option_380):
    opt = make_put_option_380()
    opt.open_trade(quantity=5)
    close_datetime = datetime.datetime(2026, 3, 18, 0, 0)

    with pytest.raises((ValueError, TypeError)):
        opt.close_trade(quote_datetime=close_datetime, quantity=2.5)

def test_partial_close_records_preserve_each_close(make_put_option_380):
    opt = make_put_option_380()
    opt.open_trade(quantity=10)
    opt.close_trade(quote_datetime=QUOTE_DT, quantity=4)
    opt.close_trade(quote_datetime=QUOTE_DT, quantity=3)

    assert len(opt.trade_close_records) == 2
    assert opt.trade_close_records[0].quantity == 4
    assert opt.trade_close_records[1].quantity == 3
    assert opt.quantity == 3, "3 contracts should still be open"
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in opt.status

def test_close_before_open_raises(make_put_option_380):
    opt = make_put_option_380()

    with pytest.raises(ValueError, match="not open"):
        opt.close_trade(quote_datetime=QUOTE_DT)

def test_close_after_full_close_returns_trade_close_info(make_put_option_380):
    opt = make_put_option_380()
    opt.open_trade(quantity=5)
    first = opt.close_trade(quote_datetime=QUOTE_DT)

    with pytest.raises(ValueError, match="already closed"):
        second = opt.close_trade(quote_datetime=QUOTE_DT)

def test_get_closing_price_raises_error_when_not_opened(make_put_option_380):
    """INITIALIZED status - no trade ever opened."""
    opt = make_put_option_380()

    assert opt.status == OptionStatus.INITIALIZED

    with pytest.raises(ValueError, match="opening trade|not.*open|has.*no"):
        opt.get_closing_price()

def test_get_closing_price_long_returns_bid_with_zero_fill_factor(make_put_option_380):
    opt = make_put_option_380()
    opt.open_trade(quantity=5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.00)

def test_get_closing_price_short_returns_ask_with_zero_fill_factor(make_put_option_380):
    opt = make_put_option_380()
    opt.open_trade(quantity=-5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.20)

def test_get_closing_price_long_fill_factor_blends_bid_toward_mid(make_put_option_380, settings_overrides):
    opt = make_put_option_380(fill_factor=0.5)
    opt.open_trade(quantity=5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    # bid + 0.5*(price - bid) = 2.00 + 0.5*(2.10 - 2.00) = 2.05
    assert opt.get_closing_price() == pytest.approx(2.05)

def test_get_closing_price_short_fill_factor_blends_ask_toward_mid(make_put_option_380, settings_overrides):
    opt = make_put_option_380(fill_factor=0.5)
    opt.open_trade(quantity=-5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    # ask - 0.5*(ask - price) = 2.20 - 0.5*(2.20 - 2.10) = 2.15
    assert opt.get_closing_price() == pytest.approx(2.15)

def test_get_closing_price_long_fill_factor_one_returns_mid(make_put_option_380, settings_overrides):
    opt = make_put_option_380(fill_factor=1.0)
    opt.open_trade(quantity=5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.10)

def test_get_closing_price_short_fill_factor_one_returns_mid(make_put_option_380, settings_overrides):
    opt = make_put_option_380(fill_factor=1.0)
    opt.open_trade(quantity=-5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.10)

def test_get_closing_price_itm_call_returns_intrinsic(make_call_option_380):
    opt = make_call_option_380(strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 105.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(5.0)

def test_get_closing_price_otm_call_returns_zero(make_call_option_380):
    opt = make_call_option_380(strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_atm_call_returns_zero(make_call_option_380):
    opt = make_call_option_380(strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 100.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_itm_put_returns_intrinsic(make_put_option_380):
    opt = make_put_option_380(strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(5.0)

def test_get_closing_price_otm_put_returns_zero(make_put_option_380):
    opt = make_put_option_380(strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 105.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_atm_put_returns_zero(make_put_option_380):
    opt = make_put_option_380(strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 100.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_expired_after_close_still_returns_intrinsic(make_put_option_380):
    """Status can be both TRADE_IS_CLOSED and EXPIRED. Intrinsic still applies."""
    opt = make_put_option_380(strike=100)
    opt.open_trade(quantity=5)
    opt.close_trade(quote_datetime=QUOTE_DT)
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
    opt.open_trade(quantity=10)
    opt.price = 3.00

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)

def test_get_profit_loss_percent_long_no_closes_at_loss(make_put_option_380):
    # Open 10 @ $2.00, price drops to $1.50
    # P&L: (1.50-2)*100*10 = -$500 -> -500/2000 = -25%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.price = 1.50

    assert opt.get_profit_loss_percent() == pytest.approx(-0.25)

def test_get_profit_loss_percent_long_partial_close_at_profit(make_put_option_380):
    # Open 10 @ $2.00 (premium = +$2000)
    # Close 5 @ $2.50 (realized: (2.50-2)*100*5 = +$250)
    # Remaining 5 at $3.00 (unrealized: (3-2)*100*5 = +$500)
    # Total: $750 -> 750/2000 = +37.5%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

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
    opt.open_trade(quantity=10)

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
    opt.open_trade(quantity=10)

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
    opt.open_trade(quantity=10)

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
    opt.open_trade(quantity=10)

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
    opt.open_trade(quantity=10)

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
    opt.open_trade(quantity=-10)
    opt.price = 1.00

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)


def test_get_profit_loss_percent_short_no_closes_at_loss(make_put_option_380):
    # Open -10 @ $2.00, price rises to $2.75
    # Short loses when price rises: (2-2.75)*100*10 = -$750 -> -750/2000 = -37.5%
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
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
    opt.open_trade(quantity=-10)

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
    opt.open_trade(quantity=-10)

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
    opt.open_trade(quantity=-10)

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
    info = opt.open_trade(quantity=10)

    assert info.premium == pytest.approx(2000.0)

def test_open_trade_premium_short_is_negative(make_put_option_380):
    # Open -10 @ $2.00: cash in $2000 -> premium = -2000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    info = opt.open_trade(quantity=-10)

    assert info.premium == pytest.approx(-2000.0)

def test_close_trade_premium_long_full_close_is_negative(make_put_option_380):
    # Open LONG 10 @ $2.00, close 10 @ $3.00: sell-to-close, cash in $3000
    # premium should be -3000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    assert rec.premium == pytest.approx(-3000.0)

def test_close_trade_premium_short_full_close_is_positive(make_put_option_380):
    # Open SHORT -10 @ $2.00, close 10 @ $1.00: buy-to-close, cash out $1000
    # premium should be +1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    rec = opt.close_trade(quote_datetime=QUOTE_DT)

    assert rec.premium == pytest.approx(1000.0)


def test_close_trade_premium_long_partial_close_is_negative(make_put_option_380):
    # Open LONG 10 @ $2.00, partial close 4 @ $2.50: cash in $1000
    # premium should be -1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.bid, opt.ask, opt.price = 2.50, 2.50, 2.50
    rec = opt.close_trade(quote_datetime=QUOTE_DT, quantity=4)


def test_close_trade_premium_short_partial_close_is_positive(make_put_option_380):
    # Open SHORT -10 @ $2.00, partial close 4 @ $1.50: cash out $600
    # premium should be +600
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
    opt.bid, opt.ask, opt.price = 1.50, 1.50, 1.50
    rec = opt.close_trade(quote_datetime=QUOTE_DT, quantity=4)

    assert rec.premium == pytest.approx(600.0)

def test_close_trade_premium_sum_equals_negative_pnl_long_profit(make_put_option_380):
    # Open 10 @ $2.00 (+2000), close 10 @ $3.00 (-3000)
    # sum = -1000  |  pnl = +1000  |  -pnl = -1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt.open_trade(quantity=10)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    close_rec = opt.close_trade(quote_datetime=QUOTE_DT)

    premium_sum = open_info.premium + close_rec.premium
    assert premium_sum == pytest.approx(-close_rec.profit_loss)

def test_close_trade_premium_sum_equals_negative_pnl_long_loss(make_put_option_380):
    # Open 10 @ $2.00 (+2000), close 10 @ $1.50 (-1500)
    # sum = +500  |  pnl = -500  |  -pnl = +500
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt.open_trade(quantity=10)
    opt.bid, opt.ask, opt.price = 1.50, 1.50, 1.50
    close_rec = opt.close_trade(quote_datetime=QUOTE_DT)

    premium_sum = open_info.premium + close_rec.premium
    assert premium_sum == pytest.approx(-close_rec.profit_loss)


def test_close_trade_premium_sum_equals_negative_pnl_short_profit(make_put_option_380):
    # Open -10 @ $2.00 (-2000), close 10 @ $1.00 (+1000)
    # sum = -1000  |  pnl = +1000  |  -pnl = -1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt.open_trade(quantity=-10)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    close_rec = opt.close_trade(quote_datetime=QUOTE_DT)

    premium_sum = open_info.premium + close_rec.premium
    assert premium_sum == pytest.approx(-close_rec.profit_loss)


def test_close_trade_premium_sum_equals_negative_pnl_short_loss(make_put_option_380):
    # Open -10 @ $2.00 (-2000), close 10 @ $3.00 (+3000)
    # sum = +1000  |  pnl = -1000  |  -pnl = +1000
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt.open_trade(quantity=-10)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    close_rec = opt.close_trade(quote_datetime=QUOTE_DT)

    premium_sum = open_info.premium + close_rec.premium
    assert premium_sum == pytest.approx(-close_rec.profit_loss)

def test_close_trade_premium_sum_equals_negative_pnl_long_multiple_partials(make_put_option_380):
    # Round-trip invariant still holds across multiple partial closes
    # Open 10 @ $2.00 (+2000)
    # Close 4 @ $2.50 (-1000, pnl +200)
    # Close 6 @ $3.00 (-1800, pnl +600)
    # premium_sum = -800  |  total pnl = +800  |  -pnl = -800
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    open_info = opt.open_trade(quantity=10)

    opt.bid, opt.ask, opt.price = 2.50, 2.50, 2.50
    rec1 = opt.close_trade(quote_datetime=QUOTE_DT, quantity=4)

    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    rec2 = opt.close_trade(quote_datetime=QUOTE_DT, quantity=6)

    premium_sum = open_info.premium + rec1.premium + rec2.premium
    total_pnl = rec1.profit_loss + rec2.profit_loss
    assert premium_sum == pytest.approx(-total_pnl)

def test_close_trade_premium_aggregate_matches_sum_of_records_long(make_put_option_380):
    # Aggregate trade_close_info.premium should equal the sum of individual
    # close record premiums, under the same convention.
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.bid, opt.ask, opt.price = 2.50, 2.50, 2.50
    rec1 = opt.close_trade(quote_datetime=QUOTE_DT, quantity=4)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    rec2 = opt.close_trade(quote_datetime=QUOTE_DT, quantity=6)

    expected_sum = rec1.premium + rec2.premium
    assert opt.trade_close_info.premium == pytest.approx(expected_sum)
    # And still negative (sell-to-close LONG is net cash in)
    assert opt.trade_close_info.premium < 0


def test_close_trade_premium_aggregate_matches_sum_of_records_short(make_put_option_380):
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)

    opt.bid, opt.ask, opt.price = 1.50, 1.50, 1.50
    rec1 = opt.close_trade(quote_datetime=QUOTE_DT, quantity=4)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    rec2 = opt.close_trade(quote_datetime=QUOTE_DT, quantity=6)

    expected_sum = rec1.premium + rec2.premium
    assert opt.trade_close_info.premium == pytest.approx(expected_sum)
    # And still positive (buy-to-close SHORT is net cash out)
    assert opt.trade_close_info.premium > 0

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
    opt.open_trade(quantity=5)
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
    opt.open_trade(quantity=5)
    close_datetime = datetime.datetime(2024, 3, 1, 10, 0)
    opt.close_trade(quote_datetime=close_datetime,)
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
    opt.open_trade(quantity=10)

    # Matching datetime - should succeed
    rec = opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    assert rec.quantity == 10
    assert OptionStatus.TRADE_IS_CLOSED in opt.status


def test_close_trade_accepts_matching_pd_timestamp(make_put_option_380):
    """pd.Timestamp equals datetime.datetime for the same moment - should work."""
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    # Equivalent pd.Timestamp should satisfy the equality check
    rec = opt.close_trade(quote_datetime=pd.Timestamp("2024-03-01 10:00:00"))
    assert rec.quantity == 10


def test_close_trade_accepts_matching_datetime_when_self_is_pd_timestamp(make_put_option_380):
    """Reverse: option's quote_datetime is pd.Timestamp, caller passes datetime."""
    opt = make_put_option_380(quote_datetime=pd.Timestamp("2024-03-01 10:00:00"))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    rec = opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    assert rec.quantity == 10


def test_close_trade_accepts_matching_datetime_for_partial_close(make_put_option_380):
    """Validation applies to partial closes too."""
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    rec = opt.close_trade(
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
    opt.open_trade(quantity=10)

    # Option is at 10:00, try to close at 9:30
    with pytest.raises(ValueError, match="mismatch"):
        opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 9, 30))


def test_close_trade_raises_when_quote_datetime_after_option_datetime(make_put_option_380):
    """Closing at a later datetime than the option's current clock - reject.

    This is the common bug: strategy forgot to call next() before close_trade(),
    so the option's bid/ask are stale.
    """
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    # Option is at 10:00, try to close at 14:00 without having called next()
    with pytest.raises(ValueError, match="mismatch"):
        opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 14, 0))


def test_close_trade_raises_on_different_date(make_put_option_380):
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    with pytest.raises(ValueError, match="mismatch"):
        opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 2, 10, 0))


def test_close_trade_mismatch_does_not_mutate_state(make_put_option_380):
    """
    A failed validation must leave the option fully intact - no partial close,
    no status change, no fees incurred, no close record appended.
    """
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    original_qty = opt.quantity
    original_status = opt.status
    original_fees = opt.total_fees
    original_close_records = list(opt.trade_close_records)

    with pytest.raises(ValueError):
        opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 14, 0))

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
    opt.open_trade(quantity=10)

    with pytest.raises(TypeError, match="quote_datetime"):
        opt.close_trade()


def test_close_trade_raises_when_quote_datetime_is_none(make_put_option_380):
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    with pytest.raises(ValueError, match="quote_datetime"):
        opt.close_trade(quote_datetime=None)


def test_close_trade_raises_when_quote_datetime_is_wrong_type(make_put_option_380):
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    with pytest.raises(TypeError, match="datetime"):
        opt.close_trade(quote_datetime="2024-03-01 10:00:00")


def test_close_trade_raises_when_quote_datetime_is_date_not_datetime(make_put_option_380):
    """A datetime.date is not a datetime.datetime - should raise."""
    opt = make_put_option_380()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    with pytest.raises(TypeError, match="datetime"):
        opt.close_trade(quote_datetime=datetime.date(2024, 3, 1))


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
    opt.open_trade(quantity=10)
    opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))

    # Second close attempt with mismatched datetime - should still raise
    with pytest.raises((ValueError, TypeError)):
        opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 1, 14, 0))


def test_close_trade_works_at_expiration_when_datetimes_match(make_call_option_380):
    """Expired path still requires matching quote_datetime."""
    opt = make_call_option_380(
        expiration=datetime.date(2024, 3, 15),
        quote_datetime=datetime.datetime(2024, 3, 1, 10, 0),
        strike=100,
    )
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    opt.spot_price = 99.0
    opt.open_trade(quantity=10)

    # Advance to expiration
    opt.quote_datetime = datetime.datetime(2024, 3, 15, 16, 0)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    # Must pass the matching datetime
    rec = opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 15, 16, 0))
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
    opt.open_trade(quantity=10)

    opt.quote_datetime = datetime.datetime(2024, 3, 15, 16, 0)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    with pytest.raises(ValueError, match="mismatch"):
        opt.close_trade(quote_datetime=datetime.datetime(2024, 3, 14, 16, 0))

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
    opt.next(datetime.datetime(2024, 3, 1, 10, 1))
    assert type(opt.quote_datetime) is datetime.datetime


def test_next_normalizes_pd_timestamp(make_put_option_380):
    """next() should apply the same normalization __post_init__ does."""
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    opt.next(pd.Timestamp("2024-03-01 10:01:00"))
    assert type(opt.quote_datetime) is datetime.datetime


def test_next_rejects_date(make_put_option_380):
    opt = make_put_option_380(quote_datetime=datetime.datetime(2024, 3, 1, 10, 0))
    with pytest.raises((TypeError, ValueError), match="datetime"):
        opt.next(datetime.date(2024, 3, 1))

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
    opt.open_trade(quantity=10)

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

    info = opt.open_trade(quantity=10)

    # 10 contracts * $2.00 override (not the $0.65 from settings) = $20
    assert info.fees == pytest.approx(20.00)


def test_option_incur_fees_false_override_disables_fees_even_when_settings_enabled(
    make_call_option_380, settings_overrides,
):
    opt = make_call_option_380(incur_fees=False)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00

    info = opt.open_trade(quantity=10)

    assert info.fees == 0
    assert opt.total_fees == 0