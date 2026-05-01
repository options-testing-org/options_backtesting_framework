from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from typing import Self

from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionStatus, OptionPositionType
from options_framework.spreads.spread_base import SpreadBase
from options_framework.utils.helpers import decimalize_0, decimalize_2, decimalize_4

@dataclass(repr=False, slots=True)
class Single(SpreadBase):
    option: Option = field(default=None)

    @classmethod
    def create(cls, option_chain: OptionChain,
               expiration: datetime.date = None,
               strike: float | int = None,
               option_type: str = None,
               *args, **kwargs) -> Self:

        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain."
            raise ValueError(message)

        # Find nearest matching strike for this expiration
        strikes = [s for s in option_chain.expiration_strikes[expiration]].copy()
        try:
            selected_strike = min(strikes, key=lambda x: abs(x - strike))
            option = next(o for o in option_chain.options if o['option_type'] == option_type
                          and o['expiration'] == expiration and o['strike'] == selected_strike)
        except StopIteration:
            raise ValueError("No matching strike was found in the option chain.")

        if option['price'] == 0:
            raise Exception(f"Option price is zero ({option['symbol']}). Cannot open this option.")

        single = Option(**option)

        single = Single(options=[single], spread_type=OptionSpreadType.SINGLE)

        # save any kwargs that were sent to user_defined
        super(Single, single)._save_user_defined_values(single, **kwargs)

        return single


    def __post_init__(self):
        if len(self.options) > 1:
            raise ValueError("Single position can only have one option. Multiple options were given.")
        if self.spread_type != OptionSpreadType.SINGLE:
            raise ValueError("Single must have spread type of SINGLE")

        self.option = self.options[0]


    def __repr__(self) -> str:
        long_short = '' if self.position_type is None else f' {self.position_type.name}'
        return f'<{self.spread_type.name}({self.instance_id}) {self.option.symbol} {self.option_type.upper()} {self.strike} {self.expiration}{long_short}>'

    @property
    def expiration(self) -> datetime.date:
        return self.option.expiration

    @property
    def option_type(self) -> str:
        return self.option.option_type

    @property
    def strike(self) -> int | float:
        return self.option.strike

    @property
    def price(self) -> float:
        return self.option.price

    def get_required_margin(self, quantity: int) -> float:
        margin = 0
        position_type = OptionPositionType.LONG if quantity > 0 else OptionPositionType.SHORT
        if position_type == OptionPositionType.SHORT:
            """
            Short options:
            20% of the spot price minus the out-of-money amount plus the option premium
            10% of the spot price plus the option premium
            $1 + option premium
            """
            pct_20 = decimalize_4(self.option.spot_price * 0.2)
            pct_10 = decimalize_4(self.option.spot_price * 0.1)
            otm_amount = decimalize_4(self.option.spot_price - self.option.strike) if self.option.otm() else decimalize_0(0)
            price = decimalize_2(self.option.price)

            # three calculations - take the largest value
            calc1 = (pct_20 - otm_amount + price)
            calc2 = (pct_10 + price)
            calc3 = (Decimal(1) + price)
            margin = max(calc1, calc2, calc3)
            margin = float(margin) * 100 * abs(quantity)
            margin = round(margin, 2)

        return margin

    def open_trade(self, quantity: int = 1, *args, **kwargs: dict) -> None:
        self.option.open_trade(quantity=quantity)
        self.position_type = self.option.position_type
        self.quantity = self.option.quantity

        super(Single, self)._save_user_defined_values(self, **kwargs)

    def close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        self.option.close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.quantity = self.option.quantity

        super(Single, self)._save_user_defined_values(self, **kwargs) # call super to set any kwargs

    def get_trade_price(self):
        if OptionStatus.INITIALIZED == self.option.status:
            return None
        else:
            return self.option.trade_open_info.price

    @property
    def max_profit(self) -> float | None:
        if self.position_type is None:
            raise RuntimeError("Cannot calculate max profit: trade has not been opened.")
        if self.position_type == OptionPositionType.LONG:
            if self.option.option_type == 'call':
                return None  # unlimited
            else:  # put
                return (self.option.strike * 100 * abs(self.quantity)) - abs(self.get_trade_premium())
        else:  # SHORT
            return abs(self.get_trade_premium())

    @property
    def max_loss(self) -> float | None:
        if self.position_type is None:
            raise RuntimeError("Cannot calculate max loss: trade has not been opened.")
        if self.position_type == OptionPositionType.SHORT:
            if self.option.option_type == 'call':
                return None  # unlimited
            else:  # put
                return (self.option.strike * 100 * abs(self.quantity)) - abs(self.get_trade_premium())
        else:  # LONG
            return abs(self.get_trade_premium())

    def get_dte(self) -> int | None:
        return self.option.get_dte()


    def get_price_history(self) -> list[tuple]:
        if OptionStatus.TRADE_IS_OPEN not in self.option.status and OptionStatus.TRADE_IS_CLOSED not in self.option.status:
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        if OptionStatus.TRADE_IS_CLOSED in self.option.status:
            last_date = self.option.trade_close_info.date
        else:
            last_date = self.option.quote_datetime

        open_price = self.option.trade_open_info.price
        open_qty = self.option.trade_open_info.quantity  # signed
        close_records = self.option.trade_close_records

        keys = [k for k in self.option.updates.keys() if k <= last_date]

        history = []
        for k in keys:
            update = self.option.updates[k]

            # reconstruct signed open quantity at this point in time
            closes_so_far = sum(r.quantity for r in close_records if r.date <= k)
            remaining = abs(open_qty) - closes_so_far
            signed_remaining = remaining * (1 if open_qty > 0 else -1)

            current_price = round(float(update['price']), 2)
            pnl = round((current_price - open_price) * 100 * signed_remaining, 2)
            open_premium_allocated = open_price * 100 * remaining
            pnl_pct = round(pnl / open_premium_allocated, 4) if open_premium_allocated != 0 else 0.0

            history.append({
                'quote_datetime': k,
                'price': current_price,
                'spot_price': update.get('spot_price'),
                'bid': update.get('bid'),
                'ask': update.get('ask'),
                'delta': update.get('delta'),
                'gamma': update.get('gamma'),
                'theta': update.get('theta'),
                'vega': update.get('vega'),
                'rho': update.get('rho'),
                'iv': update.get('implied_volatility'),
                'pnl': pnl,
                'pnl_pct': pnl_pct,
            })

        return history


    def get_closed_price(self) -> float | None:
        if OptionStatus.TRADE_IS_CLOSED not in self.option.status:
            return None
        price = decimalize_2(self.option.trade_close_info.price)
        return float(price)
