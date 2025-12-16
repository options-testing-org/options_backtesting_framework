import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Self

from .spread_base import SpreadBase
from ..option import Option
from ..option_chain import OptionChain
from ..option_types import OptionCombinationType, OptionStatus, OptionPositionType
from ..utils.helpers import decimalize_4, decimalize_2, decimalize_0


@dataclass(repr=False, slots=True)
class Straddle(SpreadBase):

    call: Option = field(default=None)
    put: Option = field(default=None)

    @classmethod
    def create(cls, option_chain: OptionChain, strike: int | float, expiration: datetime.date,
               option_position_type : OptionPositionType, *args) -> Self:
        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain."
            raise ValueError(message)

        # Find nearest matching strike for this expiration
        strikes = [s for s in option_chain.expiration_strikes[expiration]].copy()
        try:
            strike = next(s for s in strikes if s >= strike)
            options = [o for o in option_chain.options if o['expiration'] == expiration and o['strike'] == strike]
        except StopIteration:
            raise ValueError(
                "No matching strike was found in the option chain.")

        try:
            put_data = next(o for o in options if o['option_type'] == 'put')
            call_data = next(o for o in options if o['option_type'] == 'call')
        except StopIteration:
            raise ValueError("Cannot create straddle with this strike and expiration.")

        put_option = Option(**put_data)
        call_option = Option(**call_data)

        quantity = 1 if option_position_type == OptionPositionType.LONG else -1

        straddle = Straddle([put_option, call_option], OptionCombinationType.STRADDLE,
                            option_position_type=option_position_type, quantity=quantity)
        
        return straddle

    def __post_init__(self):
        if len(self.options) != 2:
            raise ValueError("A Straddle must have two options.")
        if self.options[0].option_type == self.options[1].option_type:
            raise ValueError("A Straddle must have one put and one call option.")
        call_option = next(o for o in self.options if o.option_type == 'call')
        put_option = next(o for o in self.options if o.option_type == 'put')
        if call_option.strike != put_option.strike:
            raise ValueError("Straddle options must have the same strike.")
        if call_option.quantity != put_option.quantity:
            raise ValueError("Straddle options must have the same quantity")
        if self.quantity == 0:
            raise ValueError("Quantity cannot be zero.")
        if self.quantity < 0 and self.option_position_type == OptionPositionType.LONG:
            raise ValueError("Quantity must be positive for a long position")
        if self.quantity > 0 and self.option_position_type == OptionPositionType.SHORT:
            raise ValueError("Quantity must be negative for a short position")
        if call_option.symbol != put_option.symbol:
            raise ValueError("Straddle options must be for the same equity")
        if call_option.expiration != put_option.expiration:
            raise ValueError("Straddle options must have the same expiration")

        self.call = call_option
        self.put = put_option

    def __repr__(self):
        return f'<{self.option_combination_type.name}({self.position_id}) {self.symbol} {self.strike} {self.expiration} {self.option_position_type.name}>'

    def _update_quantity(self, quantity: int):
        if self.option_position_type == OptionPositionType.LONG and quantity < 0:
            raise ValueError(f'Cannot set a negative quantity on a long position.')
        elif self.option_position_type == OptionPositionType.SHORT and quantity > 0:
            raise ValueError(f'Cannot set a positive quantity on a short position.')
        self.quantity = quantity
        self.call.quantity = quantity
        self.put.quantity = quantity


    def open_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        self._update_quantity(quantity)
        self.call.open_trade(quantity=quantity)
        self.put.open_trade(quantity=quantity)
        super(Straddle, self).open_trade(quantity=quantity, **kwargs)

    def close_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        quantity = quantity if quantity is not None else self.call.quantity
        self.call.close_trade(quantity=quantity)
        self.put.close_trade(quantity=quantity)
        self._update_quantity(quantity=quantity)

    @property
    def required_margin(self) -> float:
        if self.option_position_type == OptionPositionType.LONG:
            return 0
        elif self.option_position_type == OptionPositionType.SHORT:
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
                _margin = float(margin) * 100 * abs(self.quantity)
                margin += _margin
            return round(margin, 2)

    @property
    def status(self) -> OptionStatus:
        return self.call.status

    @property
    def symbol(self) -> str:
        return self.call.symbol

    @property
    def price(self) -> float:
        return self.call.price + self.put.price

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED == self.option.status:
            return None
        else:
            return self.call.trade_open_info.price + self.put.trade_open_info.price

    @property
    def strike(self) -> int | float:
        return self.call.strike

    @property
    def expiration(self) -> datetime.date:
        return self.call.expiration

    @property
    def max_profit(self) -> float | None:
        if self.option_position_type == OptionPositionType.SHORT:
            return self.get_trade_price()
        else:
            return None

    @property
    def max_loss(self) -> float | None:
        if self.option_position_type == OptionPositionType.LONG:
            return self.get_trade_premium()
        else:
            return None