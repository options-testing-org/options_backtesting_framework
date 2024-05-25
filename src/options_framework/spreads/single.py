import datetime
from dataclasses import dataclass, field
from typing import Optional

from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionType, OptionCombinationType, OptionStatus, OptionPositionType
from options_framework.spreads.option_combo import OptionCombination
from options_framework.utils.helpers import decimalize_0, decimalize_2

@dataclass(repr=False, slots=True)
class Single(OptionCombination):

    @classmethod
    def get_single_position(cls, *, option_chain: OptionChain, expiration: datetime.date,
                                      option_type: OptionType,
                                      option_position_type: OptionPositionType,
                                      strike: float | int,
                                      quantity: int = 1) -> OptionCombination:

        options = [o for o in option_chain.option_chain if o.option_type == option_type]

        # Find nearest matching expiration
        expirations = [e for e in option_chain.expirations if e >= expiration]

        if not expirations:
            raise ValueError("No matching expiration was found in the option chain. Consider changing the selection filter.")
        expiration = expirations[0]

        # Find nearest matching strike for this expiration
        strikes = [s for s in option_chain.expiration_strikes[expiration] if s >= strike]

        if not strikes:
            raise ValueError("No matching strike was found in the option chain. Consider changing the selection filter.")
        strike = strikes[0]

        option = [o for o in options if o.expiration == expiration and o.strike == strike][0]

        if option.price == 0:
            raise Exception("Option price is zero. Cannot open this option.")

        quantity = abs(quantity) if option_position_type == OptionPositionType.LONG else abs(quantity) * -1
        single = Single(options=[option], option_combination_type=OptionCombinationType.SINGLE,
                        option_position_type=option_position_type, quantity=quantity)
        return single

    @classmethod
    def get_single_position_by_delta(cls, *, option_chain: OptionChain, expiration: datetime.date,
                                     option_type: OptionType,
                                     option_position_type: OptionPositionType,
                                     delta: float,
                                     quantity: int = 1) -> OptionCombination:

        # Find nearest matching expiration
        expirations = [e for e in option_chain.expirations if e >= expiration]

        if not expirations:
            raise ValueError(
                "No matching expiration was found in the option chain. Consider changing the selection filter.")
        expiration = expirations[0]

        # Find option with the nearest delta
        options = [o for o in option_chain.option_chain if o.option_type == option_type and o.expiration == expiration]
        if option_type == OptionType.CALL:
            options.sort(key=lambda x: x.delta, reverse=True)
            select_options = [o for o in options if o.option_type == OptionType.CALL
                              and o.delta <= delta]
        else:
            options.sort(key=lambda x: x.delta, reverse=False)
            options.sort(key=lambda x: x.delta)
            # Find nearest long put matching delta
            select_options = [o for o in options if o.option_type == OptionType.PUT
                              and o.delta >= delta]

        if not select_options:
            raise ValueError("No matching options were found for the delta value. Consider changing the selection filter.")

        option = select_options[0]

        if option.price == 0:
            raise Exception("Option price is zero. Cannot open this option.")

        quantity = abs(quantity) if option_position_type == OptionPositionType.LONG else abs(quantity) * -1
        single = Single(options=[option], option_combination_type=OptionCombinationType.SINGLE,
                        option_position_type=option_position_type, quantity=quantity)
        return single

    option: Option = field(default=None)

    def __post_init__(self):
        if len(self.options) > 1:
            raise ValueError("Single position can only have one option. Multiple options were given.")
        if self.option_position_type is None:
            raise ValueError("The parameter option_position_type: OptionPositionType must not be None")

        self.option = self.options[0]
        quantity = abs(self.quantity) if self.option_position_type == OptionPositionType.LONG \
            else abs(self.quantity)*-1
        self.quantity = quantity
        self.option.quantity = quantity
        self.option.position_type = self.option_position_type
        self.option_combination_type = OptionCombinationType.SINGLE

    @property
    def expiration(self) -> datetime.date:
        return self.option.expiration

    @property
    def option_type(self) -> OptionType:
        return self.option.option_type

    @property
    def strike(self) -> int | float:
        return self.option.strike

    @property
    def required_margin(self) -> float:
        if not OptionStatus.TRADE_IS_OPEN in self.option.status:
            return None
        elif self.option_position_type == OptionPositionType.LONG:
            return 0
        elif self.option_position_type == OptionPositionType.SHORT:
            """
            Short options:
            20% of the underlying price minus the out-of-money amount plus the option premium
            10% of the strike price plus the option premium
            $2.50
            """
            calc1 = decimalize_2(abs(((0.20 * self.option.spot_price) - (self.strike - self.option.spot_price)) * 100 * self.quantity))
            calc2 = decimalize_2(abs(((self.strike * 0.10) + self.option.price) * 100 * self.quantity))
            calc3 = decimalize_2(abs(2.5 * 100 * self.quantity))
            margin = max(calc1, calc2, calc3)
            return float(margin)

    def update_quantity(self, quantity: int):
        self.quantity = quantity
        self.option.quantity = quantity

    def open_trade(self, *, quantity: int | None = None, **kwargs: dict) -> None:
        quantity = quantity if quantity else self.option.quantity
        self.option_position_type = OptionPositionType.LONG if quantity > 0 else OptionPositionType.SHORT
        self.option.open_trade(quantity=quantity)
        self.quantity = quantity
        super().open_trade(quantity=quantity, **kwargs)

    def close_trade(self, *, quantity: int | None = None, **kwargs: dict) -> None:
        quantity = quantity if quantity is not None else self.option.quantity
        self.option.close_trade(quantity=quantity)
        self.quantity -= quantity
        super().close_trade(quantity=quantity, **kwargs)

    def get_trade_price(self):
        if OptionStatus.INITIALIZED ==  self.option.status:
            return None
        else:
            return self.option.trade_open_info.price
