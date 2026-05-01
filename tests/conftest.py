import os
import pytest
from unittest.mock import MagicMock, patch
import copy
import pickle
import datetime
from pathlib import Path

os.environ["OPTIONS_FRAMEWORK_CONFIG_FOLDER"] = r'C:\_code\options_backtesting_framework\tests\config'
fixture_path = Path(__file__).parent / "fixtures"
from options_framework.option import Option
from options_framework.option_types import OptionSpreadType, OptionStatus, OptionPositionType
from options_framework.spreads.single import Single

REQUIRED_HISTORY_KEYS = {
    'quote_datetime', 'price', 'spot_price',
    'pnl', 'pnl_pct',
    'delta', 'gamma', 'theta', 'vega', 'rho', 'iv',
}

@pytest.fixture(scope="module")
def daily_updates_put_380() -> list[dict]:
    pkl_fn = fixture_path.joinpath("MSFT20260410P00038000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        updates = pickle.load(f)
    return updates

@pytest.fixture(scope="module")
def daily_updates_call_380() -> list[dict]:
    pkl_fn = fixture_path.joinpath("MSFT20260410C00038000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        updates = pickle.load(f)
    return updates

@pytest.fixture(scope="module")
def daily_updates_put_360() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260410P00036000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def daily_updates_put_370() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260410P00037000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def daily_updates_put_390() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260410P00039000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def daily_updates_put_400() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260410P00040000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def daily_updates_call_390() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260410C00039000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def daily_updates_call_400() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260410C00040000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def daily_updates_put_370_far() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260417P00037000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def daily_updates_put_380_far() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260417P00038000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def daily_updates_call_380_far() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260417C00038000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def daily_updates_call_390_far() -> dict:
    pkl_fn = fixture_path.joinpath("MSFT20260417C00039000_daily_updates.pkl")
    with open(pkl_fn, "rb") as f:
        return pickle.load(f)

@pytest.fixture
def settings_overrides(monkeypatch):
    base = {
        "data_frequency": "intraday",
        "incur_fees": False,
        "standard_fee": 0.65,
        "fill_factor": 0,
        "minute_granularity": 30,
        "start_time": "0930",
        "end_time": "1600",
    }

    def _apply(**overrides):
        merged = {**base, **overrides}
        monkeypatch.setattr("options_framework.option.settings", merged)
        monkeypatch.setattr("options_framework.option_chain.settings", merged)
        return merged

    return _apply

@pytest.fixture
def make_option(settings_overrides):
    def _factory(daily_updates: dict, **overrides) -> Option:
        settings_keys = {'data_frequency', 'incur_fees', 'standard_fee',
                         'fill_factor', 'minute_granularity', 'start_time', 'end_time'}
        settings_kwargs = {k: v for k, v in overrides.items() if k in settings_keys}
        option_kwargs = {k: v for k, v in overrides.items() if k not in settings_keys}
        settings_overrides(**settings_kwargs)
        first_key = list(daily_updates.keys())[0]
        first_update = daily_updates[first_key]

        db = MagicMock()
        db.get_contract_updates.return_value = copy.deepcopy(daily_updates)

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
        kwargs.update(option_kwargs)

        with patch("options_framework.option.IntradayOptionsDB.from_symbol", return_value=db), \
             patch("options_framework.option.OptionsDB.from_symbol", return_value=db):
            return Option(**kwargs)

    return _factory


# ── Per-contract option factories (thin wrappers around make_option) ──────────

@pytest.fixture
def make_put_option_380(daily_updates_put_380, make_option):
    """380 put, exp 2026-04-10. Pass overrides to tweak fields."""
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_put_380, **overrides)
    return _factory

@pytest.fixture
def make_call_option_380(daily_updates_call_380, make_option):
    """380 call, exp 2026-04-10. Pass overrides to tweak fields."""
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_call_380, **overrides)
    return _factory

@pytest.fixture
def make_put_option_360(daily_updates_put_360, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_put_360, **overrides)
    return _factory

@pytest.fixture
def make_put_option_370(daily_updates_put_370, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_put_370, **overrides)
    return _factory

@pytest.fixture
def make_put_option_390(daily_updates_put_390, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_put_390, **overrides)
    return _factory

@pytest.fixture
def make_put_option_400(daily_updates_put_400, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_put_400, **overrides)
    return _factory

@pytest.fixture
def make_call_option_390(daily_updates_call_390, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_call_390, **overrides)
    return _factory

@pytest.fixture
def make_call_option_400(daily_updates_call_400, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_call_400, **overrides)
    return _factory

# ── Far expiration option factories ───────────────────────────────────────────

@pytest.fixture
def make_put_option_370_far(daily_updates_put_370_far, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_put_370_far, **overrides)
    return _factory

@pytest.fixture
def make_put_option_380_far(daily_updates_put_380_far, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_put_380_far, **overrides)
    return _factory

@pytest.fixture
def make_call_option_380_far(daily_updates_call_380_far, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_call_380_far, **overrides)
    return _factory

@pytest.fixture
def make_call_option_390_far(daily_updates_call_390_far, make_option):
    def _factory(**overrides) -> Option:
        return make_option(daily_updates_call_390_far, **overrides)
    return _factory


class MockOptionChain:
    """
    Minimal OptionChain stand-in for tests. Populates expirations,
    expiration_strikes, and options from provided parameters without
    touching any database.
    """
    def __init__(self, symbol, quote_datetime, options):
        self.symbol = symbol
        self.quote_datetime = quote_datetime
        self.options = options
        expirations = [x['expiration'] for x in options]
        expirations = list(set(expirations))
        self.expirations = sorted(expirations)
        expiration_strikes = [(x['expiration'], x['strike']) for x in options]
        expiration_strikes = list(set(expiration_strikes))
        expiration_strikes = sorted(expiration_strikes, key=lambda x: (x[0], x[1]))
        expiration_strikes = {exp: [s for (e, s) in expiration_strikes if e == exp] for exp in expirations}
        self.expiration_strikes = expiration_strikes

@pytest.fixture
def get_mock_option_chain():
    def _get(quote_datetime: datetime.datetime) -> MockOptionChain:
        pickle_path = Path(__file__).parent / 'fixtures' / 'MSFT_chain.pkl'
        with open(pickle_path, 'rb') as f:
            all_options = pickle.load(f)
        options = all_options[quote_datetime]
        symbol = options[0]['symbol']

        return MockOptionChain(symbol=symbol, quote_datetime=quote_datetime, options=options)
    return _get

@pytest.fixture
def mock_options_db(scope="session"):
    """
    A MagicMock standing in for IntradayOptionsDB / OptionsDB instances.
    The three query methods return sentinel values that tests can override.

    Use via the make_option_chain factory below — that factory patches
    the from_symbol classmethods to return this mock, so OptionChain
    construction goes through normal __post_init__ but the DB is mocked.
    """
    db = MagicMock()
    pkl_fn = fixture_path.joinpath("MSFT_get_chain_at.pkl")
    with open(pkl_fn, "rb") as f:
        options = pickle.load(f)
    db.get_chain_at.return_value = options
    db.get_expirations_at.return_value = [[datetime.date(2026, 4, 1), datetime.date(2026, 4, 2), datetime.date(2026, 4, 10), datetime.date(2026, 4, 17), datetime.date(2026, 4, 24), datetime.date(2026, 5, 1)]   ]
    pkl_fn = fixture_path.joinpath("MSFT_expiration_strikes.pkl")
    with open(pkl_fn, "rb") as f:
        exp_strikes = pickle.load(f)
    db.get_expiration_strikes_at.return_value = exp_strikes
    return db


@pytest.fixture
def make_option_chain(mock_options_db, settings_overrides):
    """
    Factory for *real* OptionChain instances with the DB layer mocked.
    Use this when testing OptionChain itself.

    For tests that need a chain-shaped object to feed into other classes
    (Single, SpreadBase, strategies), use get_mock_option_chain instead —
    that returns a MockOptionChain stand-in, not a real OptionChain.
    """
    from options_framework.option_chain import OptionChain

    def _factory(
        symbol="MSFT",
        quote_datetime=datetime.datetime(2024, 3, 17, 0, 0),
        end_datetime=datetime.datetime(2024, 4, 10, 0, 0),
        **settings_kwargs,
    ):
        defaults = dict(
            data_frequency="daily",
        )
        defaults.update(settings_kwargs)
        settings_overrides(**defaults)

        with patch(
            "options_framework.option_chain.IntradayOptionsDB.from_symbol",
            return_value=mock_options_db,
        ), patch(
            "options_framework.option_chain.OptionsDB.from_symbol",
            return_value=mock_options_db,
        ):
            from options_framework.option_chain import settings as oc_settings
            return OptionChain(
                symbol=symbol,
                quote_datetime=quote_datetime,
                end_datetime=end_datetime,
            )

    return _factory


class _EventCapture(list):
    """A list that also holds a strong ref to a bound callback."""
    pass

def capture_events(obj, event_name):
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

# ── Portfolio fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def mock_chain():
    """
    Patches options_framework.portfolio.OptionChain for the duration of the
    test so _initialize_ticker never hits the DB.  Any test that calls
    open_position or next must include this fixture.
    """
    chain = MagicMock()
    chain.on_next = lambda quote_datetime: None
    with patch("options_framework.portfolio.OptionChain", return_value=chain):
        yield chain

@pytest.fixture
def make_portfolio(settings_overrides):
    """
    Factory for OptionPortfolio with settings patched in per-test.
    Pass portfolio constructor overrides and/or settings overrides as kwargs.

    Example:
        portfolio = make_portfolio(cash=5_000, incur_fees=True)
    """
    from options_framework.portfolio import OptionPortfolio

    def _factory(
        cash=10_000.0,
        start_date=datetime.datetime(2026, 3, 1),
        end_date=datetime.datetime(2026, 4, 10),
        current_datetime=datetime.datetime(2026, 3, 17),
        check_margin_on_open=True,
        **settings_kwargs,
    ):
        settings_overrides(**settings_kwargs)
        p = OptionPortfolio(
            cash=cash,
            start_date=start_date,
            end_date=end_date,
            check_margin_on_open=check_margin_on_open,
        )
        p.current_datetime = current_datetime
        return p

    return _factory


@pytest.fixture
def portfolio(make_portfolio):
    """Convenience fixture for tests that need a default portfolio."""
    return make_portfolio()


@pytest.fixture
def make_single(make_put_option_380):
    """
    Factory: builds a Single spread wrapping a freshly constructed put option.
    Pass option-level field overrides as kwargs (e.g. strike=300).
    """
    def _factory(**option_overrides):
        option = make_put_option_380(**option_overrides)
        return Single(options=[option], spread_type=OptionSpreadType.SINGLE)

    return _factory

@pytest.fixture
def make_mock_position():
    def make_mock_position(option_instance_id=42, all_expired=True):
        opt = MagicMock()
        opt.instance_id = option_instance_id
        opt.status = OptionStatus.EXPIRED if all_expired else OptionStatus.TRADE_IS_OPEN

        pos = MagicMock()
        pos.options = [opt]
        pos.instance_id = 99
        pos.quantity = 1
        return pos
    return make_mock_position


@pytest.fixture
def make_vertical(make_option, daily_updates_put_370, daily_updates_put_380):
    from options_framework.spreads.vertical import Vertical

    def _factory(
        long_updates: dict = None,
        short_updates: dict = None,
        option_type: str = 'put',
        position_type=OptionPositionType.SHORT,
        long_strike: float = 370.0,
        short_strike: float = 380.0,
        **leg_overrides,
    ):
        long_updates = long_updates if long_updates is not None else daily_updates_put_370
        short_updates = short_updates if short_updates is not None else daily_updates_put_380
        long_opt = make_option(long_updates, strike=long_strike,
                               option_type=option_type, **leg_overrides)
        short_opt = make_option(short_updates, strike=short_strike,
                                option_type=option_type, **leg_overrides)
        return Vertical(
            options=[long_opt, short_opt],
            spread_type=OptionSpreadType.VERTICAL,
            position_type=position_type,
        )

    return _factory

@pytest.fixture
def make_straddle(make_option, daily_updates_call_380, daily_updates_put_380):
    from options_framework.spreads.straddle import Straddle

    def _factory(
        call_updates: dict = None,
        put_updates: dict = None,
        strike: float = 380.0,
        **leg_overrides,
    ):
        call_updates = call_updates if call_updates is not None else daily_updates_call_380
        put_updates = put_updates if put_updates is not None else daily_updates_put_380
        call_opt = make_option(call_updates, strike=strike, option_type='call', **leg_overrides)
        put_opt = make_option(put_updates, strike=strike, option_type='put', **leg_overrides)
        return Straddle(
            options=[call_opt, put_opt],
            spread_type=OptionSpreadType.STRADDLE,
        )

    return _factory

@pytest.fixture
def make_strangle(make_option, daily_updates_call_390, daily_updates_put_380):
    from options_framework.spreads.strangle import Strangle

    def _factory(
        call_updates: dict = None,
        put_updates: dict = None,
        call_strike: float = 390.0,
        put_strike: float = 380.0,
        **leg_overrides,
    ):
        call_updates = call_updates if call_updates is not None else daily_updates_call_390
        put_updates = put_updates if put_updates is not None else daily_updates_put_380
        call_opt = make_option(call_updates, strike=call_strike, option_type='call', **leg_overrides)
        put_opt = make_option(put_updates, strike=put_strike, option_type='put', **leg_overrides)
        return Strangle(
            options=[call_opt, put_opt],
            spread_type=OptionSpreadType.STRANGLE,
        )

    return _factory


@pytest.fixture
def make_butterfly(
        make_option,
        daily_updates_put_370,
        daily_updates_put_380,
        daily_updates_put_390,
        daily_updates_call_380,
        daily_updates_call_390,
        daily_updates_call_400,
):
    """
    Factory: builds a Butterfly spread.

    Defaults to a LONG PUT butterfly: 370/380/390 (lower/center/upper).
    Use option_type='call' for call butterflies (defaults: 380/390/400).
    Pass position_type=OptionPositionType.SHORT for a short butterfly.
    Extra kwargs are forwarded to all three make_option calls as overrides.
    """
    from options_framework.spreads.butterfly import Butterfly

    def _factory(
            option_type: str = 'put',
            position_type: OptionPositionType = OptionPositionType.LONG,
            lower_updates: dict = None,
            center_updates: dict = None,
            upper_updates: dict = None,
            **leg_overrides,
    ):
        if option_type == 'put':
            lower_updates = lower_updates or daily_updates_put_370
            center_updates = center_updates or daily_updates_put_380
            upper_updates = upper_updates or daily_updates_put_390
            lower_strike, center_strike, upper_strike = 370.0, 380.0, 390.0
        else:
            lower_updates = lower_updates or daily_updates_call_380
            center_updates = center_updates or daily_updates_call_390
            upper_updates = upper_updates or daily_updates_call_400
            lower_strike, center_strike, upper_strike = 380.0, 390.0, 400.0

        lower_opt = make_option(lower_updates, strike=lower_strike, option_type=option_type, **leg_overrides)
        center_opt = make_option(center_updates, strike=center_strike, option_type=option_type, **leg_overrides)
        upper_opt = make_option(upper_updates, strike=upper_strike, option_type=option_type, **leg_overrides)

        return Butterfly(
            options=[lower_opt, center_opt, upper_opt],
            spread_type=OptionSpreadType.BUTTERFLY,
            position_type=position_type,
        )

    return _factory


# ── conftest.py addition ───────────────────────────────────────────────────────
# Default legs use available MSFT 2026-04-10 pickles:
#   lower_put  = 370P  (daily_updates_put_370)
#   center_put = 380P  (daily_updates_put_380)
#   center_call= 380C  (daily_updates_call_380)
#   upper_call = 390C  (daily_updates_call_390)
# Default position_type is SHORT (net credit, the standard iron butterfly).

@pytest.fixture
def make_iron_butterfly(
        make_option,
        daily_updates_put_370,
        daily_updates_put_380,
        daily_updates_call_380,
        daily_updates_call_390,
):
    from options_framework.spreads.iron_butterfly import IronButterfly

    def _factory(
            position_type: OptionPositionType = OptionPositionType.SHORT,
            lower_put_updates: dict = None,
            center_put_updates: dict = None,
            center_call_updates: dict = None,
            upper_call_updates: dict = None,
            **leg_overrides,
    ):
        lower_put_updates = lower_put_updates or daily_updates_put_370
        center_put_updates = center_put_updates or daily_updates_put_380
        center_call_updates = center_call_updates or daily_updates_call_380
        upper_call_updates = upper_call_updates or daily_updates_call_390

        lower_put = make_option(lower_put_updates, strike=370.0, option_type='put', **leg_overrides)
        center_put = make_option(center_put_updates, strike=380.0, option_type='put', **leg_overrides)
        center_call = make_option(center_call_updates, strike=380.0, option_type='call', **leg_overrides)
        upper_call = make_option(upper_call_updates, strike=390.0, option_type='call', **leg_overrides)

        return IronButterfly(
            options=[lower_put, center_put, center_call, upper_call],
            spread_type=OptionSpreadType.IRON_BUTTERFLY,
            position_type=position_type,
        )

    return _factory


# ── conftest.py addition ───────────────────────────────────────────────────────
# Default legs use available MSFT 2026-04-10 put pickles:
#   lower        = 370P  (daily_updates_put_370)
#   lower_middle = 380P  (daily_updates_put_380)
#   upper_middle = 390P  (daily_updates_put_390)  -- need this fixture
#   upper        = 400P  (daily_updates_put_400)  -- need this fixture
# Default position_type is LONG (net debit).

@pytest.fixture
def make_condor(
        make_option,
        daily_updates_put_370,
        daily_updates_put_380,
        daily_updates_put_390,
        daily_updates_put_400,
):
    from options_framework.spreads.condor import Condor

    def _factory(
            position_type: OptionPositionType = OptionPositionType.LONG,
            lower_updates: dict = None,
            lower_middle_updates: dict = None,
            upper_middle_updates: dict = None,
            upper_updates: dict = None,
            **leg_overrides,
    ):
        lower_updates = lower_updates or daily_updates_put_370
        lower_middle_updates = lower_middle_updates or daily_updates_put_380
        upper_middle_updates = upper_middle_updates or daily_updates_put_390
        upper_updates = upper_updates or daily_updates_put_400

        lower = make_option(lower_updates, strike=370.0, option_type='put', **leg_overrides)
        lower_middle = make_option(lower_middle_updates, strike=380.0, option_type='put', **leg_overrides)
        upper_middle = make_option(upper_middle_updates, strike=390.0, option_type='put', **leg_overrides)
        upper = make_option(upper_updates, strike=400.0, option_type='put', **leg_overrides)

        return Condor(
            options=[lower, lower_middle, upper_middle, upper],
            spread_type=OptionSpreadType.CONDOR,
            position_type=position_type,
        )

    return _factory


# ── conftest.py addition ───────────────────────────────────────────────────────
# Default legs use available MSFT 2026-04-10 pickles:
#   lower_put  = 370P  (daily_updates_put_370)
#   upper_put  = 380P  (daily_updates_put_380)
#   lower_call = 390C  (daily_updates_call_390)
#   upper_call = 400C  (daily_updates_call_400)
# Default position_type is SHORT (net credit, the standard iron condor).

@pytest.fixture
def make_iron_condor(
        make_option,
        daily_updates_put_370,
        daily_updates_put_380,
        daily_updates_call_390,
        daily_updates_call_400,
):
    from options_framework.spreads.iron_condor import IronCondor

    def _factory(
            position_type: OptionPositionType = OptionPositionType.SHORT,
            lower_put_updates: dict = None,
            upper_put_updates: dict = None,
            lower_call_updates: dict = None,
            upper_call_updates: dict = None,
            **leg_overrides,
    ):
        lower_put_updates = lower_put_updates or daily_updates_put_370
        upper_put_updates = upper_put_updates or daily_updates_put_380
        lower_call_updates = lower_call_updates or daily_updates_call_390
        upper_call_updates = upper_call_updates or daily_updates_call_400

        lower_put = make_option(lower_put_updates, strike=370.0, option_type='put', **leg_overrides)
        upper_put = make_option(upper_put_updates, strike=380.0, option_type='put', **leg_overrides)
        lower_call = make_option(lower_call_updates, strike=390.0, option_type='call', **leg_overrides)
        upper_call = make_option(upper_call_updates, strike=400.0, option_type='call', **leg_overrides)

        return IronCondor(
            options=[lower_put, upper_put, lower_call, upper_call],
            spread_type=OptionSpreadType.IRON_CONDOR,
            position_type=position_type,
        )

    return _factory

# ── conftest.py addition ───────────────────────────────────────────────────────
# Default: LONG put calendar at 380 strike.
#   near_option = MSFT 380P 2026-04-10  (daily_updates_put_380)
#   far_option  = MSFT 380P 2026-04-17  (daily_updates_put_380_far)
# Also supports call calendars using 380C near/far.
# Default position_type is LONG (net debit, short near / long far).

@pytest.fixture
def make_calendar(
    make_option,
    daily_updates_put_380,
    daily_updates_put_380_far,
    daily_updates_call_380,
    daily_updates_call_380_far,
):
    from options_framework.spreads.calendar import Calendar

    def _factory(
        option_type: str = 'put',
        position_type: OptionPositionType = OptionPositionType.LONG,
        near_updates: dict = None,
        far_updates: dict  = None,
        **leg_overrides,
    ):
        if option_type == 'put':
            near_updates = near_updates or daily_updates_put_380
            far_updates  = far_updates  or daily_updates_put_380_far
        else:
            near_updates = near_updates or daily_updates_call_380
            far_updates  = far_updates  or daily_updates_call_380_far

        near_option = make_option(near_updates, strike=380.0, option_type=option_type,
                                  expiration=datetime.date(2026, 4, 10), **leg_overrides)
        far_option  = make_option(far_updates,  strike=380.0, option_type=option_type,
                                  expiration=datetime.date(2026, 4, 17), **leg_overrides)

        return Calendar(
            options=[near_option, far_option],
            spread_type=OptionSpreadType.CALENDAR,
            position_type=position_type,
        )

    return _factory

# ── conftest.py addition ───────────────────────────────────────────────────────
# Default: LONG put diagonal.
#   near_option = MSFT 380P 2026-04-10  (daily_updates_put_380)
#   far_option  = MSFT 370P 2026-04-17  (daily_updates_put_370_far)
# Different strikes (380 near, 370 far) AND different expirations.
# Default position_type is LONG (short near, long far — the standard diagonal).

@pytest.fixture
def make_diagonal(
    make_option,
    daily_updates_put_380,
    daily_updates_put_370_far,
    daily_updates_call_390,
    daily_updates_call_380_far,
):
    from options_framework.spreads.diagonal import Diagonal

    def _factory(
        option_type: str = 'put',
        position_type: OptionPositionType = OptionPositionType.LONG,
        near_updates: dict = None,
        far_updates: dict  = None,
        **leg_overrides,
    ):
        if option_type == 'put':
            near_updates = near_updates or daily_updates_put_380
            far_updates  = far_updates  or daily_updates_put_370_far
            near_strike, far_strike = 380.0, 370.0
        else:
            near_updates = near_updates or daily_updates_call_390
            far_updates  = far_updates  or daily_updates_call_380_far
            near_strike, far_strike = 390.0, 380.0

        near_option = make_option(near_updates, strike=near_strike, option_type=option_type,
                                  expiration=datetime.date(2026, 4, 10), **leg_overrides)
        far_option  = make_option(far_updates,  strike=far_strike,  option_type=option_type,
                                  expiration=datetime.date(2026, 4, 17), **leg_overrides)

        return Diagonal(
            options=[near_option, far_option],
            spread_type=OptionSpreadType.DIAGONAL,
            position_type=position_type,
        )

    return _factory


# ── conftest.py addition ───────────────────────────────────────────────────────
# Default: put ratio spread, ratio=2.
#   long_option  = MSFT 380P 2026-04-10  (daily_updates_put_380)
#   short_option = MSFT 370P 2026-04-10  (daily_updates_put_370)
# Buy 1x 380P, sell 2x 370P.

@pytest.fixture
def make_ratio(
        make_option,
        daily_updates_put_380,
        daily_updates_put_370,
        daily_updates_call_380,
        daily_updates_call_390,
):
    from options_framework.spreads.ratio import Ratio

    def _factory(
            option_type: str = 'put',
            ratio: int = 2,
            long_updates: dict = None,
            short_updates: dict = None,
            **leg_overrides,
    ):
        if option_type == 'put':
            long_updates = long_updates or daily_updates_put_380
            short_updates = short_updates or daily_updates_put_370
            long_strike, short_strike = 380.0, 370.0
        else:
            long_updates = long_updates or daily_updates_call_380
            short_updates = short_updates or daily_updates_call_390
            long_strike, short_strike = 380.0, 390.0

        long_option = make_option(long_updates, strike=long_strike, option_type=option_type, **leg_overrides)
        short_option = make_option(short_updates, strike=short_strike, option_type=option_type, **leg_overrides)

        return Ratio(
            options=[long_option, short_option],
            spread_type=OptionSpreadType.RATIO,
            ratio=ratio,
        )

    return _factory


# ── conftest.py addition ───────────────────────────────────────────────────────
# make_custom builds a Custom spread from explicitly passed options and quantities.
# Default: 3-leg custom spread (put vertical + extra long put) using available pickles.
#   options:    [380P, 370P, 390P]
#   quantities: [+1,   -1,   +1 ]
# This gives a non-standard spread that couldn't be expressed as any standard type.

@pytest.fixture
def make_custom(
        make_option,
        daily_updates_put_370,
        daily_updates_put_380,
        daily_updates_put_390,
):
    from options_framework.spreads.custom import Custom

    def _factory(
            options: list = None,
            quantities: list[int] = None,
            **leg_overrides,
    ):
        if options is not None:
            # Caller passed explicit options — use as-is
            return Custom.create(options=options, quantities=quantities, **leg_overrides)

        # Default: 3-leg spread
        opt_380 = make_option(daily_updates_put_380, strike=380.0, option_type='put', **leg_overrides)
        opt_370 = make_option(daily_updates_put_370, strike=370.0, option_type='put', **leg_overrides)
        opt_390 = make_option(daily_updates_put_390, strike=390.0, option_type='put', **leg_overrides)

        return Custom.create(
            options=[opt_380, opt_370, opt_390],
            quantities=[+1, -1, +1],
        )

    return _factory
