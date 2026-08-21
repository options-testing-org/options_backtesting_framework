import datetime
import pytest

from options_framework import Option, OptionStatus


def test_next_applies_update_at_expiration_timeslot(make_put_option_380):
    """At the expiration timeslot, ``next`` must apply the 16:00 update row so
    that ``spot_price`` is current, and the settlement price must be the
    intrinsic value at that spot — not stale pre-expiration data.

    Reproduces the bug where ``Option.next`` early-returns once ``is_expired``
    is True, skipping application of the 16:00 ``_updates`` row. That leaves
    ``spot_price`` pinned to the last pre-expiration timestamp and corrupts the
    expiration P&L.

    Parameters
    ----------
    make_put_option_380 : callable
        Factory producing a 380-strike put with a mocked ``_updates`` lookup.
    """
    # Two update rows: one mid-session (pre-expiration), one at settlement.
    # Spot moves between them. If next() honors the 16:00 row, intrinsic is
    # computed from the settlement spot; if it early-returns, it uses 375.0.
    expiration = datetime.date(2026, 3, 17)
    pre_exp_dt = datetime.datetime(2026, 3, 17, 15, 45)
    settle_dt = datetime.datetime(2026, 3, 17, 16, 0)

    pre_exp_spot = 375.0    # ITM by 5.00 at this point
    settle_spot = 378.5     # ITM by 1.50 at settlement — the CORRECT basis

    updates={
            pre_exp_dt: {"spot_price": pre_exp_spot, "bid": 5.10, "ask": 5.30, "price": 5.20},
            settle_dt:  {"spot_price": settle_spot,  "bid": 1.40, "ask": 1.60, "price": 1.50},
        }
    option = make_put_option_380(
        expiration=expiration
    )

    option._open_trade(quantity=1)
    option.updates = updates

    # Strategy advances to the last useful pre-expiration bar, then to 16:00.
    option._next(pre_exp_dt)
    option._next(settle_dt)

    # 1. next() must have applied the 16:00 row, not early-returned past it.
    assert option.spot_price == settle_spot, (
        f"spot_price is {option.spot_price}, expected {settle_spot}. "
        "next() skipped the expiration-timeslot update (early-return on "
        "is_expired) and left spot pinned to the pre-expiration bar."
    )

    # 2. Settlement price is intrinsic at the 16:00 spot, NOT the bid/ask and
    #    NOT intrinsic at the stale 375.0 spot.
    expected_intrinsic = max(380.0 - settle_spot, 0.0)   # 1.50
    stale_intrinsic = max(380.0 - pre_exp_spot, 0.0)     # 5.00 — the wrong answer

    closing_price = option.get_closing_price()
    assert closing_price == pytest.approx(expected_intrinsic), (
        f"settlement price is {option.get_closing_price()}, expected "
        f"{expected_intrinsic} (intrinsic at settle spot {settle_spot}). "
        f"Got the stale value {stale_intrinsic}? Then next() never updated spot."
    )