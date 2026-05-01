import datetime
import pytest

"""
Tests for OptionChain.

Construction tests verify the datetime-grid generation logic for both
daily and intraday modes. on_next tests verify state transitions when
the chain receives a new datetime - both the happy path (data exists)
and the no-data path (datetime not in timeline, or DB returns empty).

State invariant tests pin behavior that was problematic in the original
code: no mutation of self.datetimes, repeated calls work, non-monotonic
calls work, and the three state fields (options/expirations/
expiration_strikes) stay consistent across all paths.
"""
import datetime

import pytest


# ---------------------------------------------------------------------------
# Construction and datetime grid generation
# ---------------------------------------------------------------------------

def test_construct_daily_generates_one_datetime_per_market_date(make_option_chain):
    chain = make_option_chain(
        data_frequency="daily",
        quote_datetime=datetime.datetime(2024, 3, 1),
        end_datetime=datetime.datetime(2024, 3, 8),
    )

    # Each entry should be at midnight on a market date
    for dt in chain.datetimes:
        assert dt.time() == datetime.time(0, 0)
    # All entries should be unique dates
    assert len(set(d.date() for d in chain.datetimes)) == len(chain.datetimes)


def test_construct_intraday_generates_grid_of_dates_and_times(make_option_chain):
    chain = make_option_chain(
        data_frequency="intraday",
        minute_granularity=30,
        start_time="0930",
        end_time="1600",
        quote_datetime=datetime.datetime(2024, 3, 1, 9, 30),
        end_datetime=datetime.datetime(2024, 3, 8, 16, 0),
    )

    # 14 30-minute buckets per day (09:30 through 16:00 inclusive)
    times_per_day = {}
    for dt in chain.datetimes:
        times_per_day.setdefault(dt.date(), []).append(dt.time())

    for d, times in times_per_day.items():
        assert times[0] == datetime.time(9, 30), f"{d} should start at 09:30"
        assert times[-1] == datetime.time(16, 0), f"{d} should end at 16:00"
        assert len(times) == 14, f"{d} should have 14 30-min buckets"


def test_construct_intraday_includes_end_time_when_granularity_divides_evenly(
    make_option_chain,
):
    chain = make_option_chain(
        data_frequency="intraday",
        minute_granularity=15,
        start_time="0930",
        end_time="1600",
        quote_datetime=datetime.datetime(2024, 3, 1, 9, 30),
        end_datetime=datetime.datetime(2024, 3, 8, 16, 0),
    )

    end_dt_first_day = datetime.datetime(2024, 3, 1, 16, 0)
    assert end_dt_first_day in chain.datetimes


def test_construct_intraday_excludes_end_time_when_granularity_misaligned(
    make_option_chain,
):
    """
    Pinning current behavior: when minute_granularity doesn't divide
    evenly into the trading window, the last bucket lands past end_time
    and is excluded. e.g. start=09:30, end=16:00, granularity=60 ->
    last bucket of the day is 15:30 (next would be 16:30 > 16:00).

    If you later decide PM-settlement ticks at 16:00 should always be
    included regardless of granularity, this test will fail and tell
    you to revisit the time-loop logic in get_datetimes_in_date_range.
    """
    chain = make_option_chain(
        data_frequency="intraday",
        minute_granularity=60,
        start_time="0930",
        end_time="1600",
        quote_datetime=datetime.datetime(2024, 3, 1, 9, 30),
        end_datetime=datetime.datetime(2024, 3, 8, 16, 0),
    )

    # 16:00 should NOT appear on any day
    end_times = [dt for dt in chain.datetimes if dt.time() == datetime.time(16, 0)]
    assert end_times == []

    # Last entry of the first day should be 15:30
    day1_entries = [d for d in chain.datetimes if d.date() == datetime.date(2024, 3, 1)]
    assert day1_entries[-1] == datetime.datetime(2024, 3, 1, 15, 30)


def test_construct_initializes_state_fields_empty(make_option_chain):
    chain = make_option_chain()

    assert chain.options == []
    assert chain.expirations == []
    assert chain.expiration_strikes == {}


def test_construct_uses_intraday_db_for_intraday_frequency(make_option_chain, mock_options_db):
    chain = make_option_chain(data_frequency="intraday")
    assert chain.db is mock_options_db


def test_construct_uses_daily_db_for_daily_frequency(make_option_chain, mock_options_db):
    chain = make_option_chain(data_frequency="daily")
    assert chain.db is mock_options_db


# ---------------------------------------------------------------------------
# on_next happy path: datetime exists in timeline, DB has data
# ---------------------------------------------------------------------------

def test_on_next_populates_state_when_datetime_has_data(make_option_chain, mock_options_db):
    chain = make_option_chain()
    valid_dt = chain.datetimes[2]

    chain.on_next(valid_dt)

    assert chain.quote_datetime == valid_dt
    assert chain.options == mock_options_db.get_chain_at.return_value
    assert chain.expirations == mock_options_db.get_expirations_at.return_value
    assert chain.expiration_strikes == mock_options_db.get_expiration_strikes_at.return_value


def test_on_next_calls_db_with_iso_datetime(make_option_chain, mock_options_db):
    chain = make_option_chain()
    valid_dt = chain.datetimes[2]

    chain.on_next(valid_dt)

    mock_options_db.get_chain_at.assert_called_with(valid_dt.isoformat())
    mock_options_db.get_expirations_at.assert_called_with(valid_dt.isoformat())
    mock_options_db.get_expiration_strikes_at.assert_called_with(valid_dt.isoformat())


def test_on_next_returns_none(make_option_chain):
    """Event handlers' returns are discarded by pydispatch; pin None."""
    chain = make_option_chain()
    result = chain.on_next(chain.datetimes[2])
    assert result is None


# ---------------------------------------------------------------------------
# on_next: datetime not in chain's timeline
# ---------------------------------------------------------------------------

def test_on_next_clears_state_when_datetime_not_in_set(make_option_chain):
    chain = make_option_chain()

    # First populate state
    chain.on_next(chain.datetimes[2])
    assert chain.options != []

    # Then tick at a datetime not in the timeline
    bogus_dt = datetime.datetime(2099, 1, 1, 12, 0)
    chain.on_next(bogus_dt)

    assert chain.options == []
    assert chain.expirations == []
    assert chain.expiration_strikes == {}
    # quote_datetime advances even on the no-data path
    assert chain.quote_datetime == bogus_dt


def test_on_next_does_not_call_db_when_datetime_not_in_set(make_option_chain, mock_options_db):
    chain = make_option_chain()
    bogus_dt = datetime.datetime(2099, 1, 1, 12, 0)

    chain.on_next(bogus_dt)

    mock_options_db.get_chain_at.assert_not_called()
    mock_options_db.get_expirations_at.assert_not_called()
    mock_options_db.get_expiration_strikes_at.assert_not_called()


# ---------------------------------------------------------------------------
# on_next: datetime in timeline but DB returns no options
# ---------------------------------------------------------------------------

def test_on_next_clears_state_when_db_returns_empty(make_option_chain, mock_options_db):
    chain = make_option_chain()
    mock_options_db.get_chain_at.return_value = []

    chain.on_next(chain.datetimes[2])

    assert chain.options == []
    assert chain.expirations == []
    assert chain.expiration_strikes == {}


def test_on_next_does_not_query_expirations_when_db_returns_no_chain(
    make_option_chain, mock_options_db,
):
    """When get_chain_at returns empty, skip the other DB calls."""
    chain = make_option_chain()
    mock_options_db.get_chain_at.return_value = []

    chain.on_next(chain.datetimes[2])

    mock_options_db.get_chain_at.assert_called_once()
    mock_options_db.get_expirations_at.assert_not_called()
    mock_options_db.get_expiration_strikes_at.assert_not_called()


# ---------------------------------------------------------------------------
# State invariants
# ---------------------------------------------------------------------------

def test_on_next_does_not_mutate_datetimes_list(make_option_chain):
    """Regression: original on_next sliced self.datetimes on every tick."""
    chain = make_option_chain()
    original = list(chain.datetimes)

    chain.on_next(chain.datetimes[2])
    chain.on_next(chain.datetimes[4])
    chain.on_next(datetime.datetime(2099, 1, 1, 12, 0))

    assert chain.datetimes == original


def test_on_next_works_at_same_datetime_twice(make_option_chain):
    """Regression: original code broke on repeated calls because it
    mutated self.datetimes."""
    chain = make_option_chain()
    valid_dt = chain.datetimes[2]

    chain.on_next(valid_dt)
    first_options = chain.options

    chain.on_next(valid_dt)

    assert chain.options == first_options


def test_on_next_works_with_non_monotonic_calls(make_option_chain, mock_options_db):
    """Regression: original code only worked if calls were in time order."""
    chain = make_option_chain()
    expected = mock_options_db.get_chain_at.return_value

    chain.on_next(chain.datetimes[5])
    chain.on_next(chain.datetimes[2])  # earlier datetime
    chain.on_next(chain.datetimes[5])  # back to later

    # All three calls populate state correctly
    assert chain.options == expected


def test_on_next_db_returning_empty_chain_clears_stale_expirations(
    make_option_chain, mock_options_db,
):
    """
    Tick 1 populates everything. Tick 2 has its datetime in the timeline
    but DB returns no chain. expirations and expiration_strikes from
    tick 1 must be cleared, not left stale.
    """
    chain = make_option_chain()
    chain.on_next(chain.datetimes[2])
    assert chain.expirations  # populated

    # Next tick: in the timeline, but no chain data
    mock_options_db.get_chain_at.return_value = []
    chain.on_next(chain.datetimes[3])

    assert chain.options == []
    assert chain.expirations == []
    assert chain.expiration_strikes == {}


def test_on_next_state_consistent_across_data_and_no_data_ticks(
    make_option_chain,
):
    """
    options, expirations, and expiration_strikes are always consistent —
    either all populated for the same datetime, or all empty. Never a
    mix of stale data from a previous tick.
    """
    chain = make_option_chain()

    chain.on_next(chain.datetimes[2])
    assert chain.options
    assert chain.expirations
    assert chain.expiration_strikes

    chain.on_next(datetime.datetime(2099, 1, 1))

    assert chain.options == []
    assert chain.expirations == []
    assert chain.expiration_strikes == {}