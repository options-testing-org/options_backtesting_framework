from __future__ import annotations

import copy
import datetime
import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from unittest.mock import MagicMock, patch

from numpy import rec

from options_framework.option import Option, TradeCloseInfo, TradeOpenInfo
from options_framework.option_types import OptionPositionType, OptionStatus

fixture_path = Path(__file__).parent / "fixtures"

@pytest.fixture(scope="module")
def daily_updates() -> list[dict]:
    pkl_fn = fixture_path.joinpath("MSFT20260410P00038000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        updates = pickle.load(f)
    return updates

@pytest.fixture
def settings_overrides(monkeypatch):
    base = {
        "data_frequency": "intraday",
        "incur_fees": False,
        "standard_fee": 0.65,
        "fill_factor": 0,
    }

    def _apply(**overrides):
        merged = {**base, **overrides}
        monkeypatch.setattr("options_framework.option.settings", merged)
        return merged

    return _apply

@pytest.fixture
def mock_db(daily_updates) -> MagicMock:
    db = MagicMock()
    db.get_contract_updates.return_value = copy.deepcopy(daily_updates)
    return db

@pytest.fixture
def make_option(daily_updates: list[dict], mock_db: MagicMock, settings_overrides) -> Option:
    """
        Factory returning a freshly-constructed Option wired to the mock DB.
        Pass overrides as kwargs if a test needs to tweak the initial quote.
        """
    settings_overrides()
    first_update = daily_updates[list(daily_updates.keys())[0]]
    def _factory(**overrides) -> Option:
        kwargs = dict(
            option_id=first_update["option_id"],
            symbol=first_update["symbol"],
            strike=first_update["strike"],
            expiration=first_update["expiration"],
            option_type=first_update["option_type"],
            quote_datetime=first_update["quote_datetime"],
            spot_price=first_update["spot_price"],
            bid=first_update["bid"],
            ask=first_update["ask"],
            price=first_update["price"],
        )
        kwargs.update(overrides)
        with patch(
                "options_framework.option.IntradayOptionsDB.from_symbol",
                return_value=mock_db,
        ), patch(
            "options_framework.option.OptionsDB.from_symbol",
            return_value=mock_db,
        ):
            return Option(**kwargs)

    return _factory

def _make_close_record(opt, *, quantity, price):
    """Build a TradeCloseInfo with only the fields get_profit_loss_percent reads."""
    return TradeCloseInfo(
        option_id=opt.option_id,
        instance_id=opt.instance_id,
        date=opt.quote_datetime,
        quantity=quantity,   # positive count, per close_trade convention
        price=price,
        premium=0.0,
        profit_loss=0.0,
        profit_loss_percent=0.0,
        fees=0.0,
        spot_price=float(opt.spot_price),
    )


@pytest.mark.parametrize("data_frequency", ["daily", "intraday"])
def test_close_without_quantity_closes_full_position(make_option, settings_overrides, data_frequency):
    settings_overrides(data_frequency=data_frequency)
    option = make_option()
    option.open_trade(quantity=10)

    option.close_trade()

    assert option.quantity == 0
    assert OptionStatus.TRADE_IS_CLOSED in option.status
    assert OptionStatus.TRADE_IS_OPEN not in option.status

def test_long_partial_close_reduces_quantity(make_option):
    option = make_option()
    option.open_trade(quantity=10)
    rec = option.close_trade(quantity=4)

    assert option.quantity == 6
    assert rec.quantity == 4
    assert OptionStatus.TRADE_IS_OPEN in option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status
    assert OptionStatus.TRADE_IS_CLOSED not in option.status

def test_short_partial_close_reduces_quantity(make_option):
    option = make_option()
    option.open_trade(quantity=-10)
    rec = option.close_trade(quantity=3)

    assert option.quantity == -7
    assert rec.quantity == 3
    assert OptionStatus.TRADE_IS_OPEN in option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status
    assert OptionStatus.TRADE_IS_CLOSED not in option.status

def test_successive_partial_closes_fully_close_position(make_option):
    option = make_option()
    option.open_trade(quantity=10)
    option.close_trade(quantity=2)

    assert option.quantity == 8
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in option.status

    option.close_trade(quantity=8)


    assert option.quantity == 0
    assert OptionStatus.TRADE_IS_CLOSED in option.status
    assert OptionStatus.TRADE_IS_OPEN not in option.status
    assert OptionStatus.TRADE_PARTIALLY_CLOSED not in option.status

def test_close_quantity_greater_than_open_raises(make_option):
    option = make_option()
    option.open_trade(quantity=5)

    with pytest.raises(ValueError, match="greater than"):
        option.close_trade(quantity=15)


def test_close_quantity_zero_raises(make_option):
    opt = make_option()
    opt.open_trade(quantity=5)

    with pytest.raises(ValueError):
        opt.close_trade(quantity=0)

def test_close_quantity_negative_raises(make_option):
    opt = make_option()
    opt.open_trade(quantity=5)

    with pytest.raises(ValueError):
        opt.close_trade(quantity=-3)

def test_close_quantity_non_integer_raises(make_option):
    opt = make_option()
    opt.open_trade(quantity=5)

    with pytest.raises((ValueError, TypeError)):
        opt.close_trade(quantity=2.5)

def test_partial_close_records_preserve_each_close(make_option):
    opt = make_option()
    opt.open_trade(quantity=10)

    opt.close_trade(quantity=4)
    opt.close_trade(quantity=3)

    assert len(opt.trade_close_records) == 2
    assert opt.trade_close_records[0].quantity == 4
    assert opt.trade_close_records[1].quantity == 3
    assert opt.quantity == 3, "3 contracts should still be open"
    assert OptionStatus.TRADE_PARTIALLY_CLOSED in opt.status

def test_close_before_open_raises(make_option):
    opt = make_option()

    with pytest.raises(ValueError, match="not open"):
        opt.close_trade()

def test_close_after_full_close_returns_trade_close_info(make_option):
    opt = make_option()
    opt.open_trade(quantity=5)
    first = opt.close_trade()

    with pytest.raises(ValueError, match="already closed"):
        second = opt.close_trade()

def test_get_closing_price_raises_error_when_not_opened(make_option):
    """INITIALIZED status - no trade ever opened."""
    opt = make_option()
    assert opt.status == OptionStatus.INITIALIZED

    with pytest.raises(ValueError, match="opening trade|not.*open|has.*no"):
        opt.get_closing_price()

def test_get_closing_price_long_returns_bid_with_zero_fill_factor(make_option):
    opt = make_option()
    opt.open_trade(quantity=5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.00)

def test_get_closing_price_short_returns_ask_with_zero_fill_factor(make_option):
    opt = make_option()
    opt.open_trade(quantity=-5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.20)

def test_get_closing_price_long_fill_factor_blends_bid_toward_mid(make_option, settings_overrides):
    settings_overrides(fill_factor=0.5)
    opt = make_option()
    opt.open_trade(quantity=5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    # bid + 0.5*(price - bid) = 2.00 + 0.5*(2.10 - 2.00) = 2.05
    assert opt.get_closing_price() == pytest.approx(2.05)

def test_get_closing_price_short_fill_factor_blends_ask_toward_mid(make_option, settings_overrides):
    settings_overrides(fill_factor=0.5)
    opt = make_option()
    opt.open_trade(quantity=-5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    # ask - 0.5*(ask - price) = 2.20 - 0.5*(2.20 - 2.10) = 2.15
    assert opt.get_closing_price() == pytest.approx(2.15)

def test_get_closing_price_long_fill_factor_one_returns_mid(make_option, settings_overrides):
    settings_overrides(fill_factor=1.0)
    opt = make_option()
    opt.open_trade(quantity=5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.10)

def test_get_closing_price_short_fill_factor_one_returns_mid(make_option, settings_overrides):
    settings_overrides(fill_factor=1.0)
    opt = make_option()
    opt.open_trade(quantity=-5)
    opt.bid, opt.ask, opt.price = 2.00, 2.20, 2.10

    assert opt.get_closing_price() == pytest.approx(2.10)

def test_get_closing_price_itm_call_returns_intrinsic(make_option):
    opt = make_option(option_type="call", strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 105.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(5.0)

def test_get_closing_price_otm_call_returns_zero(make_option):
    opt = make_option(option_type="call", strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_atm_call_returns_zero(make_option):
    opt = make_option(option_type="call", strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 100.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_itm_put_returns_intrinsic(make_option):
    opt = make_option(option_type="put", strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(5.0)

def test_get_closing_price_otm_put_returns_zero(make_option):
    opt = make_option(option_type="put", strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 105.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_atm_put_returns_zero(make_option):
    opt = make_option(option_type="put", strike=100)
    opt.open_trade(quantity=5)
    opt.spot_price = 100.0
    opt.status |= OptionStatus.EXPIRED

    assert opt.get_closing_price() == pytest.approx(0.0)

def test_get_closing_price_expired_after_close_still_returns_intrinsic(make_option):
    """Status can be both TRADE_IS_CLOSED and EXPIRED. Intrinsic still applies."""
    opt = make_option(option_type="put", strike=100)
    opt.open_trade(quantity=5)
    opt.close_trade()
    opt.spot_price = 95.0
    opt.status |= OptionStatus.EXPIRED

    assert OptionStatus.TRADE_IS_CLOSED in opt.status
    assert opt.get_closing_price() == pytest.approx(5.0)

def test_get_profit_loss_percent_raises_when_not_traded(make_option):
    opt = make_option()
    with pytest.raises(Exception, match="not been traded"):
        opt.get_profit_loss_percent()

def test_get_profit_loss_percent_long_no_closes_at_profit(make_option):
    # Open 10 @ $2.00 (premium = +$2000), price moves to $3.00
    # P&L: (3-2)*100*10 = $1000 -> 1000/2000 = +50%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.price = 3.00

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)

def test_get_profit_loss_percent_long_no_closes_at_loss(make_option):
    # Open 10 @ $2.00, price drops to $1.50
    # P&L: (1.50-2)*100*10 = -$500 -> -500/2000 = -25%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)
    opt.price = 1.50

    assert opt.get_profit_loss_percent() == pytest.approx(-0.25)

def test_get_profit_loss_percent_long_partial_close_at_profit(make_option):
    # Open 10 @ $2.00 (premium = +$2000)
    # Close 5 @ $2.50 (realized: (2.50-2)*100*5 = +$250)
    # Remaining 5 at $3.00 (unrealized: (3-2)*100*5 = +$500)
    # Total: $750 -> 750/2000 = +37.5%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=2.50))
    opt.quantity = 5
    opt.price = 3.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    pnl_pct = opt.get_profit_loss_percent()
    assert pnl_pct == pytest.approx(0.375)

def test_get_profit_loss_percent_long_partial_close_at_loss(make_option):
    # Open 10 @ $2.00, close 5 @ $1.50 (realized -$250), remaining 5 @ $1.00 (unrealized -$500)
    # Total: -$750 -> -750/2000 = -37.5%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=1.50))
    opt.quantity = 5
    opt.price = 1.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(-0.375)


def test_get_profit_loss_percent_long_partial_close_mixed_outcomes(make_option):
    # Open 10 @ $2.00, close 5 @ $1.50 (realized -$250), remaining 5 @ $2.10 (unrealized +$50)
    # Total: -$200 -> -200/2000 = -10%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=1.50))
    opt.quantity = 5
    opt.price = 2.10
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(-0.10)


def test_get_profit_loss_percent_long_multiple_partial_closes(make_option):
    # Open 10 @ $2.00
    # Close 3 @ $2.50 (realized: (2.50-2)*100*3 = +$150)
    # Close 4 @ $2.25 (realized: (2.25-2)*100*4 = +$100)
    # Remaining 3 @ $2.75 (unrealized: (2.75-2)*100*3 = +$225)
    # Total: $475 -> 475/2000 = +23.75%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=3, price=2.50))
    opt.trade_close_records.append(_make_close_record(opt, quantity=4, price=2.25))
    opt.quantity = 3
    opt.price = 2.75
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(0.2375)


def test_get_profit_loss_percent_long_fully_closed_at_profit(make_option):
    # Open 10 @ $2.00, fully close 10 @ $3.00
    # After full close: quantity=0, self.price set to close price ($3.00) by close_trade
    # Total: (3-2)*100*10 = $1000 -> 1000/2000 = +50%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=10, price=3.00))
    opt.quantity = 0
    opt.price = 3.00
    opt.status &= ~OptionStatus.TRADE_IS_OPEN
    opt.status |= OptionStatus.TRADE_IS_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)


def test_get_profit_loss_percent_long_fully_closed_at_loss(make_option):
    # Open 10 @ $2.00, fully close 10 @ $1.20
    # Total: (1.20-2)*100*10 = -$800 -> -800/2000 = -40%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=10, price=1.20))
    opt.quantity = 0
    opt.price = 1.20
    opt.status &= ~OptionStatus.TRADE_IS_OPEN
    opt.status |= OptionStatus.TRADE_IS_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(-0.40)

def test_get_profit_loss_percent_short_no_closes_at_profit(make_option):
    # Open -10 @ $2.00 (premium = -$2000, cash inflow), price drops to $1.00
    # Short profits when price drops: (2-1)*100*10 = +$1000 -> 1000/2000 = +50%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
    opt.price = 1.00

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)


def test_get_profit_loss_percent_short_no_closes_at_loss(make_option):
    # Open -10 @ $2.00, price rises to $2.75
    # Short loses when price rises: (2-2.75)*100*10 = -$750 -> -750/2000 = -37.5%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)
    opt.price = 2.75

    assert opt.get_profit_loss_percent() == pytest.approx(-0.375)


# ---------------------------------------------------------------------------
# SHORT, with closes - accidentally correct, pinned as regression anchor
# ---------------------------------------------------------------------------

def test_get_profit_loss_percent_short_partial_close_at_profit(make_option):
    # Open -10 @ $2.00, close 5 @ $1.50 (realized: (2-1.5)*100*5 = +$250)
    # Remaining -5 at $1.00 (unrealized: (2-1)*100*5 = +$500)
    # Total: $750 -> 750/2000 = +37.5%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=1.50))
    opt.quantity = -5
    opt.price = 1.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(0.375)


def test_get_profit_loss_percent_short_partial_close_at_loss(make_option):
    # Open -10 @ $2.00, close 5 @ $2.50 (realized: (2-2.5)*100*5 = -$250)
    # Remaining -5 at $3.00 (unrealized: (2-3)*100*5 = -$500)
    # Total: -$750 -> -750/2000 = -37.5%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=5, price=2.50))
    opt.quantity = -5
    opt.price = 3.00
    opt.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(-0.375)


def test_get_profit_loss_percent_short_fully_closed_at_profit(make_option):
    # Open -10 @ $2.00, fully close 10 @ $1.00
    # Total: (2-1)*100*10 = +$1000 -> 1000/2000 = +50%
    opt = make_option()
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    opt.open_trade(quantity=-10)

    opt.trade_close_records.append(_make_close_record(opt, quantity=10, price=1.00))
    opt.quantity = 0
    opt.price = 1.00
    opt.status &= ~OptionStatus.TRADE_IS_OPEN
    opt.status |= OptionStatus.TRADE_IS_CLOSED

    assert opt.get_profit_loss_percent() == pytest.approx(0.5)