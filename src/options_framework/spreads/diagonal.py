from collections import namedtuple
from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase
from typing import Self


RollRecord = namedtuple('RollRecord', 'date old_option new_option credit')


@dataclass(repr=False, slots=True)
class Diagonal(SpreadBase):

    near_option: Option          = field(init=False, default=None)
    far_option: Option           = field(init=False, default=None)
    roll_records: list           = field(init=False, default_factory=list)
    net_cost_basis: float | None = field(init=False, default=None)

    def __post_init__(self):
        self.near_option = self.options[0]
        self.far_option  = self.options[1]

    def __repr__(self) -> str:
        return (
            f'<{self.spread_type.name}({self.instance_id}) '
            f'{self.option_type} '
            f'{self.near_option.strike}/{self.near_option.expiration} '
            f'{self.far_option.strike}/{self.far_option.expiration}>'
        )

    @classmethod
    def create(cls,
               option_chain: OptionChain,
               near_expiration: datetime.date = None,
               far_expiration: datetime.date = None,
               option_type: str = None,
               near_strike: int | float = None,
               far_strike: int | float = None,
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

        resolved_near_strike = min(near_strikes, key=lambda x: abs(x - near_strike))
        resolved_far_strike  = min(far_strikes,  key=lambda x: abs(x - far_strike))

        all_options = option_chain.options
        near_option_data = next(
            o for o in all_options
            if o['option_type'] == option_type
            and o['expiration'] == near_expiration
            and o['strike'] == resolved_near_strike
        )
        far_option_data = next(
            o for o in all_options
            if o['option_type'] == option_type
            and o['expiration'] == far_expiration
            and o['strike'] == resolved_far_strike
        )

        near_option = Option(**near_option_data)
        far_option  = Option(**far_option_data)

        resolved_position_type = position_type if position_type is not None else OptionPositionType.LONG

        diagonal = Diagonal(
            options=[near_option, far_option],
            spread_type=OptionSpreadType.DIAGONAL,
            position_type=resolved_position_type,
        )

        super(Diagonal, diagonal)._save_user_defined_values(diagonal, **kwargs)
        return diagonal

    @property
    def option_type(self) -> str:
        return self.near_option.option_type

    @property
    def near_strike(self) -> int | float:
        return self.near_option.strike

    @property
    def far_strike(self) -> int | float:
        return self.far_option.strike

    def open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        qty = abs(quantity)
        if self.position_type == OptionPositionType.LONG:
            near_qty = -qty
            far_qty  =  qty
        else:
            near_qty =  qty
            far_qty  = -qty

        self.near_option.open_trade(quantity=near_qty)
        self.far_option.open_trade(quantity=far_qty)

        self.quantity = self.far_option.quantity
        self.net_cost_basis = self.get_trade_price()
        self.user_defined['roll_records'] = self.roll_records

        super(Diagonal, self)._save_user_defined_values(self, **kwargs)

    def close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        self.near_option.close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.far_option.close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.quantity = self.far_option.quantity
        super(Diagonal, self)._save_user_defined_values(self, **kwargs)

    def roll_near(self, *, quote_datetime: datetime.datetime, new_near_option: Option) -> None:
        if new_near_option.expiration >= self.far_option.expiration:
            raise ValueError("New near expiration must be earlier than the far option expiration.")

        if OptionStatus.TRADE_IS_OPEN not in self.near_option.status:
            raise RuntimeError("Cannot roll: near leg is not open.")

        old_near = self.near_option
        qty = old_near.quantity

        old_near.close_trade(quantity=None, quote_datetime=quote_datetime)
        new_near_option.open_trade(quantity=qty)

        if self.position_type == OptionPositionType.LONG:
            credit = float(decimalize_2(new_near_option.price) - decimalize_2(old_near.price))
        else:
            credit = float(decimalize_2(old_near.price) - decimalize_2(new_near_option.price))

        self.net_cost_basis = float(decimalize_2(self.net_cost_basis) - decimalize_2(credit))

        record = RollRecord(
            date=quote_datetime,
            old_option=old_near,
            new_option=new_near_option,
            credit=credit,
        )
        self.roll_records.append(record)

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

    def get_required_margin(self, quantity: int) -> float:
        if self.position_type == OptionPositionType.LONG:
            return 0.0
        return float(decimalize_2(abs(self.price))) * 100 * abs(quantity)

    def _get_near_segments(self) -> list[tuple]:
        if not self.roll_records:
            return [(self.near_option, self.net_cost_basis)]

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

    def get_price_history(self) -> list[dict]:
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