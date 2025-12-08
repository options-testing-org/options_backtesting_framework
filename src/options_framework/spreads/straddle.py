import datetime
from typing import Self

from .option_combo import OptionCombination
from ..option import Option
from ..option_chain import OptionChain
from ..option_types import OptionCombinationType, OptionStatus, OptionPositionType


class Straddle(OptionCombination):



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
            options = next(o for o in option_chain.options if o['expiration'] == expiration and o['strike'] == strike)
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


    def update_quantity(self, quantity: int):
        pass

    def open_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        pass

    def close_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        pass

    @property
    def required_margin(self) -> float:
        pass

    @property
    def status(self) -> OptionStatus:
        pass

    @property
    def symbol(self) -> OptionStatus:
        pass

    @property
    def price(self) -> float:
        pass

    def get_trade_price(self) -> float | None:
        pass
