from collections import namedtuple
from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase
from typing import Self


# Recorded each time the near leg is rolled.
# credit: net credit received from the roll (positive = credit, negative = additional debit).
#   LONG calendar:  credit = new_near.price - old_near.price
#   SHORT calendar: credit = old_near.price - new_near.price
RollRecord = namedtuple('RollRecord', 'date old_option new_option credit')


@dataclass(repr=False, slots=True)
class Calendar(SpreadBase):

    near_option: Option             = field(init=False, default=None)
    far_option: Option              = field(init=False, default=None)
    roll_records: list              = field(init=False, default_factory=list)
    net_cost_basis: float | None    = field(init=False, default=None)

    def __post_init__(self):
        self.near_option = self.options[0]
        self.far_option  = self.options[1]

    def __repr__(self) -> str:
        return (
            f'<{self.spread_type.name}({self.instance_id}) '
            f'{self.option_type} {self.strike} '
            f'{self.near_option.expiration}/{self.far_option.expiration}>'
        )

    @classmethod
    def create(cls,
               option_chain: OptionChain,
               near_expiration: datetime.date = None,
               far_expiration: datetime.date = None,
               option_type: str = None,
               strike: int | float = None,
               position_type: OptionPositionType = None,
               *args, **kwargs) -> Self:

        if near_expiration >= far_expiration:
            raise ValueError("near_expiration must be earlier than far_expiration.")

        try:
            near_expiration = next(e for e in option_chain.expirations if e >= near_expiration)
        except StopIteration:
            raise ValueError("No matching near expiration was found in the option chain.")

        try:
            far_expiration = next(e for e in option_chain.expirations if e >= far_expiration)
        except StopIteration:
            raise ValueError("No matching far expiration was found in the option chain.")

        near_strikes = option_chain.expiration_strikes[near_expiration]
        far_strikes  = option_chain.expiration_strikes[far_expiration]

        near_strike = min(near_strikes, key=lambda x: abs(x - strike))
        far_strike  = min(far_strikes,  key=lambda x: abs(x - strike))

        all_options = option_chain.options
        near_option_data = next(
            o for o in all_options
            if o['option_type'] == option_type
            and o['expiration'] == near_expiration
            and o['strike'] == near_strike
        )
        far_option_data = next(
            o for o in all_options
            if o['option_type'] == option_type
            and o['expiration'] == far_expiration
            and o['strike'] == far_strike
        )

        near_option = Option(**near_option_data)
        far_option  = Option(**far_option_data)

        resolved_position_type = position_type if position_type is not None else OptionPositionType.LONG

        calendar = Calendar(
            options=[near_option, far_option],
            spread_type=OptionSpreadType.CALENDAR,
            position_type=resolved_position_type,
        )

        super(Calendar, calendar)._save_user_defined_values(calendar, **kwargs)
        return calendar

    @property
    def strike(self) -> int | float:
        return self.near_option.strike

    @property
    def option_type(self) -> str:
        return self.near_option.option_type

    def _open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        qty = abs(quantity)
        if self.position_type == OptionPositionType.LONG:
            # LONG calendar: short near, long far
            near_qty = -qty
            far_qty  =  qty
        else:
            # SHORT calendar: long near, short far
            near_qty =  qty
            far_qty  = -qty

        self.near_option._open_trade(quantity=near_qty)
        self.far_option._open_trade(quantity=far_qty)

        self.quantity = self.far_option.quantity
        self.net_cost_basis = self.get_trade_price()

        # Initialise roll_records entry in user_defined so callers
        # always find the same list reference there.
        self.user_defined['roll_records'] = self.roll_records

        super(Calendar, self)._save_user_defined_values(self, **kwargs)

    def _close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        self.near_option._close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.far_option._close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.quantity = self.far_option.quantity
        super(Calendar, self)._save_user_defined_values(self, **kwargs)

    def roll_near(self, *, quote_datetime: datetime.datetime, new_near_option: Option) -> None:
        """
        Close the current near leg and open a new one, collecting or paying the
        difference as a credit/debit adjustment to net_cost_basis.

        The new_near_option must have an expiration strictly before the far leg's
        expiration.  Only full rolls are supported — the entire near quantity is
        rolled at once.
        """
        if new_near_option.expiration >= self.far_option.expiration:
            raise ValueError("New near expiration must be earlier than the far option expiration.")

        if OptionStatus.TRADE_IS_OPEN not in self.near_option.status:
            raise RuntimeError("Cannot roll: near leg is not open.")

        old_near = self.near_option
        qty = old_near.quantity  # signed — negative for LONG calendar near leg

        # Close the old near leg
        old_near._close_trade(quantity=None, quote_datetime=quote_datetime)

        # Open the new near leg with the same signed quantity
        new_near_option._open_trade(quantity=qty)

        # Compute the credit received from the roll.
        # LONG calendar (near is short, qty < 0):
        #   We buy back old near (pay old_near.price) and sell new near (receive new_near.price).
        #   credit = new_near_option.price - old_near.price
        # SHORT calendar (near is long, qty > 0):
        #   We sell old near (receive old_near.price) and buy new near (pay new_near.price).
        #   credit = old_near.price - new_near_option.price
        if self.position_type == OptionPositionType.LONG:
            credit = float(decimalize_2(new_near_option.price) - decimalize_2(old_near.price))
        else:
            credit = float(decimalize_2(old_near.price) - decimalize_2(new_near_option.price))

        # Positive credit reduces our net cost; negative means we paid extra debit.
        self.net_cost_basis = float(decimalize_2(self.net_cost_basis) - decimalize_2(credit))

        record = RollRecord(
            date=quote_datetime,
            old_option=old_near,
            new_option=new_near_option,
            credit=credit,
        )
        self.roll_records.append(record)
        # roll_records in user_defined is the same list reference — no explicit append needed.

        # Swap in the new near leg
        self.options[0] = new_near_option
        self.near_option = new_near_option

    def _calculate_price(self, *, near_price: float, far_price: float) -> float:
        n = decimalize_2(near_price)
        f = decimalize_2(far_price)
        if self.position_type == OptionPositionType.LONG:
            price = f - n
        else:
            price = n - f
        return float(price)

    @property
    def price(self) -> float:
        return self._calculate_price(
            near_price=self.near_option.price,
            far_price=self.far_option.price,
        )

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED in self.near_option.status:
            return None
        return self._calculate_price(
            near_price=self.near_option.trade_open_info.price,
            far_price=self.far_option.trade_open_info.price,
        )

    def get_closed_price(self) -> float | None:
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            return self._calculate_price(
                near_price=self.near_option.trade_close_info.price,
                far_price=self.far_option.trade_close_info.price,
            )
        return None

    def get_dte(self) -> int | None:
        return self.near_option.get_dte()

    @property
    def max_profit(self) -> float | None:
        return None

    @property
    def max_loss(self) -> float | None:
        return None

    @property
    def status(self) -> OptionStatus:
        return self.far_option.status

    def get_required_margin(self, quantity: int) -> float:
        if self.position_type == OptionPositionType.LONG:
            return 0.0
        return float(decimalize_2(abs(self.price))) * 100 * abs(quantity)

    def _get_near_segments(self) -> list[tuple]:
        """
        Returns a list of (near_option, cost_basis) tuples in chronological order,
        one per near leg that has existed on this calendar (original + each rolled leg).
        """
        if not self.roll_records:
            return [(self.near_option, self.net_cost_basis)]

        # Reconstruct the original near option and its cost basis
        original_near = self.roll_records[0].old_option
        original_cost = self._calculate_price(
            near_price=original_near.trade_open_info.price,
            far_price=self.far_option.trade_open_info.price,
        )

        segments = [(original_near, original_cost)]
        cumulative_credit = 0.0
        for record in self.roll_records:
            cumulative_credit += record.credit
            segments.append((record.new_option, original_cost - cumulative_credit))

        return segments

    def get_history(self) -> list[dict]:
        if (OptionStatus.TRADE_IS_OPEN not in self.far_option.status
                and OptionStatus.TRADE_IS_CLOSED not in self.far_option.status):
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        far_updates = self.far_option.updates
        segments    = self._get_near_segments()
        history     = []

        for near_opt, cost_basis in segments:
            close_records = near_opt.trade_close_records
            open_qty      = abs(near_opt.trade_open_info.quantity)

            if OptionStatus.TRADE_IS_CLOSED in near_opt.status:
                last_date = near_opt.trade_close_info.date
            else:
                last_date = near_opt.quote_datetime

            near_updates = near_opt.updates
            keys = sorted(k for k in near_updates if k <= last_date)

            for k in keys:
                nu = near_updates[k]
                fu = far_updates[k]

                price = self._calculate_price(
                    near_price=round(float(nu['price']), 2),
                    far_price=round(float(fu['price']), 2),
                )

                closes_so_far          = sum(r.quantity for r in close_records if r.date <= k)
                remaining_qty          = open_qty - closes_so_far
                open_premium_allocated = abs(cost_basis) * 100 * remaining_qty

                pnl     = round((price - cost_basis) * 100 * remaining_qty, 2)
                pnl_pct = round(pnl / open_premium_allocated, 4) if open_premium_allocated != 0 else 0.0

                def _net_greek(near_val, far_val):
                    if near_val is None or far_val is None:
                        return None
                    if self.position_type == OptionPositionType.LONG:
                        return far_val - near_val
                    else:
                        return near_val - far_val

                def _avg_iv(near_val, far_val):
                    vals = [v for v in (near_val, far_val) if v is not None]
                    return sum(vals) / len(vals) if vals else None

                history.append({
                    'quote_datetime': k,
                    'price':      price,
                    'spot_price': nu.get('spot_price'),
                    'pnl':        pnl,
                    'pnl_pct':    pnl_pct,
                    'delta': _net_greek(nu.get('delta'), fu.get('delta')),
                    'gamma': _net_greek(nu.get('gamma'), fu.get('gamma')),
                    'theta': _net_greek(nu.get('theta'), fu.get('theta')),
                    'vega':  _net_greek(nu.get('vega'),  fu.get('vega')),
                    'rho':   _net_greek(nu.get('rho'),   fu.get('rho')),
                    'iv':    _avg_iv(nu.get('implied_volatility'), fu.get('implied_volatility')),
                })

        return history

    def get_updates(self) -> list[dict]:
        pass
