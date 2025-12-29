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
            if option_type == 'call':
                strike = next(s for s in strikes if s >= strike)
            else:
                strikes.sort(reverse=True)
                strike = next(s for s in strikes if s <= strike)

            option = next(o for o in option_chain.options if o['option_type'] == option_type
                          and o['expiration'] == expiration and o['strike'] == strike)
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

    @property
    def status(self) -> OptionStatus:
        return self.option.status


    @property
    def required_margin(self) -> float:
        margin = 0
        if self.position_type == OptionPositionType.SHORT:
            """
            Short options:
            20% of the spot price minus the out-of-money amount plus the option premium
            10% of the spot price plus the option premium
            $1 + option premium
            """
            pct_20 = decimalize_4(self.option.spot_price * 0.2)
            pct_10 = decimalize_4(self.option.spot_price * 0.1)
            otm_amount = decimalize_4(self.option.spot_price - self.option.strike) if self.option.otm() else decimalize_0(0)
            price = decimalize_2(self.option.trade_open_info.price)

            # three calculations - take the largest value
            calc1 = (pct_20 - otm_amount + price)
            calc2 = (pct_10 + price)
            calc3 = (Decimal(1) + price)
            margin = max(calc1, calc2, calc3)
            margin = float(margin) * 100 * abs(self.quantity)
            margin = round(margin, 2)

        return margin

    def open_trade(self, quantity: int = 1, *args, **kwargs: dict) -> None:
        self.option.open_trade(quantity=quantity)
        self.position_type = self.option.position_type
        self.quantity = self.option.quantity

        super(Single, self)._save_user_defined_values(self, **kwargs)

    def close_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        quantity = quantity if quantity is not None else self.option.quantity
        self.option.close_trade(quantity=quantity)
        self.quantity = self.option.quantity

        super(Single, self)._save_user_defined_values(self, **kwargs) # call super to set any kwargs

    def get_trade_price(self):
        if OptionStatus.INITIALIZED == self.option.status:
            return None
        else:
            return self.option.trade_open_info.price

    @property
    def max_profit(self) -> float | None:
        if self.position_type == OptionPositionType.SHORT:
            return self.get_trade_premium()
        else:
            return None

    @property
    def max_loss(self) -> float | None:
        if self.position_type == OptionPositionType.LONG:
            return self.get_trade_premium()
        else:
            return None

    def get_dte(self) -> int | None:
        return self.option.get_dte()