import pytest
import datetime

from options_framework.spreads.single import Single
from options_framework.option_types import OptionSpreadType, OptionStatus

CHAIN_DT = datetime.datetime(2026, 3, 17, 0, 0)


def test_long_call_option_profitable_pnl(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single_call = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single_call._open_trade(quantity=1)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    single_call._close_trade(quote_datetime=CHAIN_DT)
    pnl = single_call.get_profit_loss()
    pnl_pct = single_call.get_profit_loss_percent()

    assert pnl == 100.0
    assert pnl_pct == 0.50

def test_long_call_option_unprofitable_pnl(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single_call = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single_call._open_trade(quantity=1)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    single_call._close_trade(quote_datetime=CHAIN_DT)
    pnl = single_call.get_profit_loss()
    pnl_pct = single_call.get_profit_loss_percent()

    assert pnl == -100.0
    assert pnl_pct == -0.50

def test_short_call_option_profitable_pnl(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single_call = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single_call._open_trade(quantity=-1)
    opt.bid, opt.ask, opt.price = 1.00, 1.00, 1.00
    single_call._close_trade(quote_datetime=CHAIN_DT)
    pnl = single_call.get_profit_loss()
    pnl_pct = single_call.get_profit_loss_percent()

    assert pnl == 100.0
    assert pnl_pct == 0.50

def test_short_call_option_unprofitable_pnl(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single_call = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single_call._open_trade(quantity=-1)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    single_call._close_trade(quote_datetime=CHAIN_DT)
    pnl = single_call.get_profit_loss()
    pnl_pct = single_call.get_profit_loss_percent()

    assert pnl == -100.0
    assert pnl_pct == -0.50

# --- full close, default quantity ---

def test_close_trade_long_full_close_default_quantity(make_put_option_380):
    option = make_put_option_380()  # assumes default is a call or put, doesn't matter
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    single._close_trade(quote_datetime=single.option.quote_datetime)

    assert OptionStatus.TRADE_IS_CLOSED in single.option.status
    assert single.option.quantity == 0
    assert single.quantity == single.option.quantity  # sync check


def test_close_trade_short_full_close_default_quantity(make_put_option_380):
    # BUG: currently passes -1 to Option.close_trade, which expects a positive value.
    # This test should fail before the fix and pass after:
    #   quantity = abs(self.option.quantity)
    option = make_put_option_380()
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-1)

    single._close_trade(quote_datetime=single.option.quote_datetime)

    assert OptionStatus.TRADE_IS_CLOSED in single.option.status
    assert single.option.quantity == 0
    assert single.quantity == single.option.quantity


# --- explicit quantity (caller bypasses the default path) ---

def test_close_trade_long_explicit_quantity(make_put_option_380):
    option = make_put_option_380()
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    single._close_trade(quote_datetime=single.option.quote_datetime, quantity=1)

    assert OptionStatus.TRADE_IS_CLOSED in single.option.status
    assert single.option.quantity == 0
    assert single.quantity == single.option.quantity


def test_close_trade_short_explicit_quantity(make_put_option_380):
    # Explicit positive quantity bypasses the bug entirely — should pass today
    option = make_put_option_380()
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-1)

    single._close_trade(quote_datetime=single.option.quote_datetime, quantity=1)

    assert OptionStatus.TRADE_IS_CLOSED in single.option.status
    assert single.option.quantity == 0
    assert single.quantity == single.option.quantity


# --- partial close ---

def test_close_trade_long_partial_close(make_put_option_380):
    option = make_put_option_380()
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=3)

    single._close_trade(quote_datetime=single.option.quote_datetime, quantity=1)

    assert OptionStatus.TRADE_IS_CLOSED not in single.option.status
    assert single.option.quantity == 2
    assert single.quantity == single.option.quantity  # sync check on partial


def test_close_trade_short_partial_close(make_put_option_380):
    option = make_put_option_380()
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-3)

    single._close_trade(quote_datetime=single.option.quote_datetime, quantity=1)

    assert OptionStatus.TRADE_IS_CLOSED not in single.option.status
    assert single.option.quantity == -2
    assert single.quantity == single.option.quantity


# --- guard: over-close raises ---

def test_close_trade_over_close_raises(make_put_option_380):
    option = make_put_option_380()
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    with pytest.raises(ValueError):
        single._close_trade(quote_datetime=single.option.quote_datetime, quantity=99)

def test_get_trade_premium_raises_when_not_opened(make_call_option_380):
    opt = make_call_option_380(strike=100)
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)

    with pytest.raises(RuntimeError):
        single.get_trade_premium()


def test_get_profit_loss_percent_raises_when_not_opened(make_call_option_380):
    opt = make_call_option_380(strike=100)
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)

    with pytest.raises(RuntimeError):
        single.get_profit_loss_percent()


def test_max_profit_raises_when_not_opened(make_call_option_380):
    opt = make_call_option_380(strike=100)
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)

    with pytest.raises(RuntimeError):
        _ = single.max_profit


def test_max_loss_raises_when_not_opened(make_call_option_380):
    opt = make_call_option_380(strike=100)
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)

    with pytest.raises(RuntimeError):
        _ = single.max_loss

# --- raise before open ---

def test_max_profit_raises_when_not_opened(make_call_option_380):
    opt = make_call_option_380(strike=100)
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)

    with pytest.raises(RuntimeError):
        _ = single.max_profit


def test_max_loss_raises_when_not_opened(make_call_option_380):
    opt = make_call_option_380(strike=100)
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)

    with pytest.raises(RuntimeError):
        _ = single.max_loss


# --- long call: max_profit is None (unlimited), max_loss is premium paid ---

def test_max_profit_long_call_is_none(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    assert single.max_profit is None


def test_max_loss_long_call_is_premium_paid(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    # premium paid = 2.00 * 100 * 1 = 200.00
    assert single.max_loss == 200.00


# --- long put: max_profit is finite, max_loss is premium paid ---

def test_max_profit_long_put_is_finite(make_put_option_380, settings_overrides):
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    # strike * 100 * qty - premium paid = (100 * 100 * 1) - 200 = 9800.00
    assert single.max_profit == 9800.00


def test_max_loss_long_put_is_premium_paid(make_put_option_380, settings_overrides):
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    assert single.max_loss == 200.00


# --- short call: max_profit is premium received, max_loss is None (unlimited) ---

def test_max_profit_short_call_is_premium_received(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-1)

    # premium received = 2.00 * 100 * 1 = 200.00
    assert single.max_profit == 200.00


def test_max_loss_short_call_is_none(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-1)

    assert single.max_loss is None


# --- short put: max_profit is premium received, max_loss is finite ---

def test_max_profit_short_put_is_premium_received(make_put_option_380, settings_overrides):
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-1)

    assert single.max_profit == 200.00


def test_max_loss_short_put_is_finite(make_put_option_380, settings_overrides):
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-1)

    # (strike * 100 * qty) - premium received = (100 * 100 * 1) - 200 = 9800.00
    assert single.max_loss == 9800.00


# --- multi-contract: verify qty scaling ---

def test_max_loss_long_call_scales_with_quantity(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=3)

    # premium paid = 2.00 * 100 * 3 = 600.00
    assert single.max_loss == 600.00


def test_max_profit_short_put_scales_with_quantity(make_put_option_380, settings_overrides):
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-3)

    # (100 * 100 * 3) - (2.00 * 100 * 3) = 30000 - 600 = 29400.00
    assert single.max_loss == 29400.00

# --- raises before open ---

def test_get_price_history_raises_when_not_opened(make_call_option_380):
    opt = make_call_option_380(strike=100)
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)

    with pytest.raises(RuntimeError):
        single.get_history()


# --- basic shape and fields ---

def test_get_price_history_returns_list_of_dicts(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    history = single.get_history()

    assert isinstance(history, list)
    assert len(history) > 0
    assert all(isinstance(row, dict) for row in history)


def test_get_price_history_contains_expected_keys(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    history = single.get_history()
    expected_keys = {'quote_datetime', 'price', 'spot_price', 'bid', 'ask',
                     'delta', 'gamma', 'theta', 'vega', 'rho', 'iv', 'pnl', 'pnl_pct'}

    assert set(history[0].keys()) == expected_keys


# --- history stops at close date ---

def test_get_price_history_stops_at_close_date(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)
    close_dt = datetime.datetime(2026, 4, 1, 0, 0)
    opt.bid, opt.ask, opt.price = 3.00, 3.00, 3.00
    opt.quote_datetime = close_dt
    single._close_trade(quote_datetime=close_dt)

    history = single.get_history()

    assert all(row['quote_datetime'] <= close_dt for row in history)


# --- pnl calculations: long ---

def test_get_price_history_pnl_long_profitable(make_call_option_380, settings_overrides):
    # open at 2.00, one update at 3.00
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    # inject a known update directly so the test isn't coupled to mock_db shape
    update_dt = opt.quote_datetime + datetime.timedelta(days=1)
    opt.quote_datetime = update_dt
    opt.updates[update_dt] = {
        'price': 3.00, 'spot_price': 105.0, 'bid': 3.00, 'ask': 3.00
    }

    history = single.get_history()
    target = next(row for row in history if row['quote_datetime'] == update_dt)

    assert target['pnl'] == 100.0       # (3.00 - 2.00) * 100 * 1
    assert target['pnl_pct'] == 0.50    # 100 / 200


def test_get_price_history_pnl_long_losing(make_call_option_380, settings_overrides):
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=1)

    update_dt = opt.quote_datetime + datetime.timedelta(days=1)
    opt.quote_datetime = update_dt
    opt.updates[update_dt] = {
        'price': 1.00, 'spot_price': 95.0, 'bid': 1.00, 'ask': 1.00
    }

    history = single.get_history()
    target = next(row for row in history if row['quote_datetime'] == update_dt)

    assert target['pnl'] == -100.0
    assert target['pnl_pct'] == -0.50


# --- pnl calculations: short ---

def test_get_price_history_pnl_short_profitable(make_put_option_380, settings_overrides):
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-1)

    update_dt = opt.quote_datetime + datetime.timedelta(days=1)
    opt.quote_datetime = update_dt
    opt.updates[update_dt] = {
        'price': 1.00, 'spot_price': 105.0, 'bid': 1.00, 'ask': 1.00
    }

    history = single.get_history()
    target = next(row for row in history if row['quote_datetime'] == update_dt)

    assert target['pnl'] == 100.0
    assert target['pnl_pct'] == 0.50


def test_get_price_history_pnl_short_losing(make_put_option_380, settings_overrides):
    opt = make_put_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=-1)

    update_dt = opt.quote_datetime + datetime.timedelta(days=1)
    opt.quote_datetime = update_dt
    opt.updates[update_dt] = {
        'price': 3.00, 'spot_price': 95.0, 'bid': 3.00, 'ask': 3.00
    }

    history = single.get_history()
    target = next(row for row in history if row['quote_datetime'] == update_dt)

    assert target['pnl'] == -100.0
    assert target['pnl_pct'] == -0.50


# --- partial close: quantity adjusts correctly ---

def test_get_price_history_pnl_after_partial_close(make_call_option_380, settings_overrides):
    # open long 2, close 1 at t1, check pnl at t2 uses remaining qty of 1
    opt = make_call_option_380(strike=100)
    opt.bid, opt.ask, opt.price = 2.00, 2.00, 2.00
    single = Single(options=[opt], spread_type=OptionSpreadType.SINGLE)
    single._open_trade(quantity=2)

    t1 = opt.quote_datetime + datetime.timedelta(days=1)
    opt.updates[t1] = {'price': 2.50, 'spot_price': 102.0, 'bid': 2.50, 'ask': 2.50}

    # partial close at t1
    opt.quote_datetime = t1
    single._close_trade(quote_datetime=t1, quantity=1)

    t2 = opt.quote_datetime + datetime.timedelta(days=1)
    opt.quote_datetime = t2
    opt.updates[t2] = {'price': 3.00, 'spot_price': 105.0, 'bid': 3.00, 'ask': 3.00}

    history = single.get_history()
    t1_row = next(row for row in history if row['quote_datetime'] == t1)
    t2_row = next(row for row in history if row['quote_datetime'] == t2)

    # at t1: 2 contracts still open at that moment (close happens at t1 but quantity check is <=)
    # pnl = (2.50 - 2.00) * 100 * 2 = 100.0
    assert t1_row['pnl'] == 50.0
    assert t1_row['pnl_pct'] == 0.25

    # at t2: only 1 contract remaining after t1 close
    # pnl = (3.00 - 2.00) * 100 * 1 = 100.0
    assert t2_row['pnl'] == 100.0
    assert t2_row['pnl_pct'] == 0.50

# --- exact match ---

def test_create_exact_expiration_and_strike(get_mock_option_chain):
    chain = get_mock_option_chain(CHAIN_DT)
    single = Single.create(
        option_chain=chain,
        expiration=datetime.date(2026, 3, 18),
        strike=330.0,
        option_type='call',
    )

    assert single.expiration == datetime.date(2026, 3, 18)
    assert single.strike == 330.0
    assert single.option_type == 'call'


# --- nearest expiration ---

def test_create_selects_nearest_expiration(get_mock_option_chain):
    # 3/19 doesn't exist — nearest on or after is 3/20
    chain = get_mock_option_chain(CHAIN_DT)
    single = Single.create(
        option_chain=chain,
        expiration=datetime.date(2026, 3, 19),
        strike=330.0,
        option_type='call',
    )

    assert single.expiration == datetime.date(2026, 3, 20)


# --- nearest strike ---

def test_create_selects_nearest_strike(get_mock_option_chain):
    # 336.0 is between 335.0 (diff=1.0) and 337.5 (diff=1.5) — nearest is 335.0
    chain = get_mock_option_chain(CHAIN_DT)
    single = Single.create(
        option_chain=chain,
        expiration=datetime.date(2026, 3, 18),
        strike=336.0,
        option_type='call',
    )

    assert single.strike == 335.0


# --- no matching expiration raises ---

def test_create_raises_when_no_matching_expiration(get_mock_option_chain):
    chain = get_mock_option_chain(CHAIN_DT)

    with pytest.raises(ValueError, match="No matching expiration"):
        Single.create(
            option_chain=chain,
            expiration=datetime.date(2029, 1, 1),  # past all expirations
            strike=330.0,
            option_type='call',
        )


# --- zero price raises ---

def test_create_raises_when_option_price_is_zero(get_mock_option_chain):
    chain = get_mock_option_chain(CHAIN_DT)

    # force price to zero on the target option
    target = next(
        o for o in chain.options
        if o['expiration'] == datetime.date(2026, 3, 18)
        and o['strike'] == 330.0
        and o['option_type'] == 'call'
    )
    target['price'] = 0

    with pytest.raises(Exception, match="price is zero"):
        Single.create(
            option_chain=chain,
            expiration=datetime.date(2026, 3, 18),
            strike=330.0,
            option_type='call',
        )


# --- kwargs saved to user_defined ---

def test_create_saves_kwargs_to_user_defined(get_mock_option_chain):
    chain = get_mock_option_chain(CHAIN_DT)
    single = Single.create(
        option_chain=chain,
        expiration=datetime.date(2026, 3, 18),
        strike=330.0,
        option_type='call',
        strategy='test_strategy',
        signal_strength=0.85,
    )

    assert single.user_defined['strategy'] == 'test_strategy'
    assert single.user_defined['signal_strength'] == 0.85


# --- returned Single has correct spread type ---

def test_create_returns_single_spread_type(get_mock_option_chain):
    chain = get_mock_option_chain(CHAIN_DT)
    single = Single.create(
        option_chain=chain,
        expiration=datetime.date(2026, 3, 18),
        strike=330.0,
        option_type='call',
    )

    assert single.spread_type == OptionSpreadType.SINGLE


# --- put option ---

def test_create_put_option(get_mock_option_chain):
    chain = get_mock_option_chain(CHAIN_DT)
    single = Single.create(
        option_chain=chain,
        expiration=datetime.date(2026, 3, 18),
        strike=330.0,
        option_type='put',
    )

    assert single.option_type == 'put'
    assert single.strike == 330.0