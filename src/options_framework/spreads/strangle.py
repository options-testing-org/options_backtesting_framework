from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Self

from .spread_base import SpreadBase
from ..option import Option
from ..option_chain import OptionChain
from ..option_types import OptionSpreadType, OptionStatus, OptionPositionType
from ..utils.helpers import decimalize_0, decimalize_4, decimalize_2


class Strangle(SpreadBase):
    @classmethod
    def create(cls, option_chain: OptionChain,
               expiration: datetime.date = None,
               call_strike: float | int = None,
               put_strike: float | int = None,
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
            call_strike = min(strikes, key=lambda x: abs(x - call_strike))
            put_strike = min(strikes, key=lambda x: abs(x - put_strike))

        except StopIteration:
            raise ValueError(
                "No matching strike was found in the option chain.")

        options = [o for o in option_chain.options if o['expiration'] == expiration]
        try:
            put_data = next(o for o in options if o['option_type'] == 'put' and o['strike'] == put_strike)
            call_data = next(o for o in options if o['option_type'] == 'call' and o['strike'] == call_strike)
        except StopIteration:
            raise ValueError("Cannot create straddle with this strike and expiration.")

        put_option = Option(**put_data)
        call_option = Option(**call_data)

        strangle = Strangle([put_option, call_option], OptionSpreadType.STRANGLE)

        # save any kwargs that were sent to user_defined dict
        super(Strangle, strangle)._save_user_defined_values(strangle, **kwargs)

        return strangle

    def __repr__(self) -> str:
        long_short = '' if self.position_type is None else f' {self.position_type.name}'
        return f'<{self.spread_type.name}({self.instance_id}) {self.symbol} {self.call.strike}/{self.put.strike} {self.expiration}{long_short}>'

    def __post_init__(self):
        if len(self.options) != 2:
            raise ValueError("A Strangle must have two options.")
        if self.options[0].option_type == self.options[1].option_type:
            raise ValueError("A Strangle must have one put and one call option.")
        call_option = next(o for o in self.options if o.option_type == 'call')
        put_option = next(o for o in self.options if o.option_type == 'put')
        if put_option.strike >= call_option.strike:
            raise ValueError("Strangle call option strike must be greater than the put option strike.")
        if call_option.position_type is not None and put_option.position_type is not None:
            if call_option.position_type != put_option.position_type:
                raise ValueError("Strangle options must both be long or short.")
        if call_option.quantity != put_option.quantity:
            raise ValueError("Strangle options must have the same quantity")
        if call_option.symbol != put_option.symbol:
            raise ValueError("Strangle options must be for the same equity")
        if call_option.expiration != put_option.expiration:
            raise ValueError("Strangle options must have the same expiration")
        if self.spread_type != OptionSpreadType.STRANGLE:
            raise ValueError("Strangle must have spread type of STRANGLE")

        self.call = call_option
        self.put = put_option

    def open_trade(self, quantity: int = 1, *args, **kwargs: dict) -> None:
        self.call.open_trade(quantity=quantity)
        self.put.open_trade(quantity=quantity)
        self.position_type = self.call.position_type
        self.quantity = self.call.quantity

        super(Strangle, self)._save_user_defined_values(self, **kwargs)


    def close_trade(self, quantity: int | None = None, *args, **kwargs: dict) -> None:
        quantity = quantity if quantity is not None else self.call.quantity
        self.call.close_trade(quantity=quantity)
        self.put.close_trade(quantity=quantity)
        self.quantity = self.call.quantity

        super(Strangle, self)._save_user_defined_values(self, **kwargs)

    @property
    def max_profit(self) -> float | None:
        if self.position_type == OptionPositionType.SHORT:
            return self.get_trade_premium() * -1
        else:
            return None

    @property
    def max_loss(self) -> float | None:
        if self.position_type == OptionPositionType.LONG:
            return self.get_trade_premium() * -1
        else:
            return None

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
            margin = 0
            for option in self.options:
                pct_20 = decimalize_4(option.spot_price * 0.2)
                pct_10 = decimalize_4(option.spot_price * 0.1)
                otm_amount = decimalize_4(
                    option.spot_price - option.strike) if option.otm() else decimalize_0(0)
                price = decimalize_2(option.trade_open_info.price)

                # three calculations - take the largest value
                calc1 = (pct_20 - otm_amount + price)
                calc2 = (pct_10 + price)
                calc3 = (Decimal(1) + price)
                _margin = max(calc1, calc2, calc3)
                _margin = float(_margin) * 100 * abs(self.quantity)
                margin += _margin
            margin = round(margin, 2)
        return round(margin, 2)


    @property
    def status(self) -> OptionStatus:
        return self.call.status

    @property
    def price(self) -> float:
        return self.call.price + self.put.price

    def get_dte(self) -> int | None:
        return self.call.get_dte()

    def get_trade_price(self) -> float | None:
        if all(o.status == OptionStatus.INITIALIZED for o in self.options):
            return None
        else:
            return self.call.trade_open_info.price + self.put.trade_open_info.price

    @property
    def expiration(self) -> datetime.date:
        return self.call.expiration