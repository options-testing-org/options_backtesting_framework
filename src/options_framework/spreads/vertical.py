from dataclasses import field

from options_framework.option_types import OptionPositionType, OptionType, OptionCombinationType, OptionStatus
from options_framework.option_chain import OptionChain
from options_framework.spreads.option_combo import OptionCombination
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
import datetime


class Vertical(OptionCombination):

    @classmethod
    def get_vertical(cls, *, option_chain: OptionChain, expiration: datetime.date, option_type: OptionType,
                     long_strike: int | float,
                     short_strike: int | float,
                     quantity: int = 1) -> OptionCombination:

        if long_strike < short_strike:
            option_position_type = OptionPositionType.LONG if option_type == OptionType.CALL \
                else OptionPositionType.SHORT
        elif long_strike > short_strike:
            option_position_type = OptionPositionType.SHORT if option_type == OptionType.CALL \
                else OptionPositionType.LONG
        else:
            raise ValueError("Long and short strikes cannot be the same")

        # Find nearest matching expiration
        expirations = [e for e in option_chain.expirations if e >= expiration]

        if not expirations:
            message = "No matching expiration was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)
        expiration = expirations[0]

        # Find nearest long strike
        strikes = [s for s in option_chain.expiration_strikes[expiration] if s >= long_strike]
        if not strikes:
            message = "No matching strike was found for the long strike. Consider changing the selection filter."
            raise ValueError(message)
        long_strike = strikes[0]

        # Find nearest short strike
        strikes = [s for s in option_chain.expiration_strikes[expiration] if s >= short_strike]
        if not strikes:
            message = "No matching strike was found for the short strike. Consider changing the selection filter."
            raise ValueError(message)
        short_strike = strikes[0]

        long_option = [o for o in option_chain.option_chain if o.expiration == expiration
                       and o.strike == long_strike][0]
        long_option.quantity = quantity
        short_option = [o for o in option_chain.option_chain if o.expiration == expiration
                        and o.strike == short_strike][0]
        short_option.quantity = quantity * -1

        vertical = Vertical(options=[long_option, short_option],
                            option_combination_type=OptionCombinationType.VERTICAL,
                            option_position_type=option_position_type, quantity=quantity)
        return vertical

    @classmethod
    def get_vertical_by_delta(cls, *, option_chain: OptionChain, expiration: datetime.date, option_type: OptionType,
                     long_delta: float,
                     short_delta: float,
                     quantity: int = 1) -> OptionCombination:

        if long_delta > short_delta:
            option_position_type = OptionPositionType.LONG if option_type == OptionType.CALL \
                else OptionPositionType.SHORT
        elif long_delta < short_delta:
            option_position_type = OptionPositionType.SHORT if option_type == OptionType.CALL \
                else OptionPositionType.LONG
        else:
            raise ValueError("Long and short strikes cannot be the same")

        # Find nearest matching expiration
        expirations = [e for e in option_chain.expirations if e >= expiration]

        if not expirations:
            message = "No matching expiration was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)
        expiration = expirations[0]

        options = [o for o in option_chain.option_chain if o.option_type == option_type and o.expiration == expiration]
        if option_type == OptionType.CALL :
            options.sort(key=lambda x: x.delta, reverse=True)
            select_options = [o for o in options if o.option_type == OptionType.CALL
                              and o.delta <= long_delta]
        else:
            options.sort(key=lambda x: x.delta, reverse=False)
            select_options = [o for o in options if o.option_type == OptionType.PUT
                              and o.delta >= -long_delta]

        if not select_options:
            message = "No option was found for the long delta value. Consider changing the selection filter."
            raise ValueError(message)

        long_option = select_options[0]
        long_option.quantity = abs(quantity)

        if option_type == OptionType.CALL:
            select_options = [o for o in options if o.option_type == OptionType.CALL
                              and o.delta <= short_delta]
        else:
            select_options = [o for o in options if o.option_type == OptionType.PUT
                              and o.delta >= -short_delta]

        if not select_options:
            message = "No option was found for the short delta value. Consider changing the selection filter."
            raise ValueError(message)

        short_option = select_options[0]
        short_option.quantity = abs(quantity) * -1

        if long_option.strike < short_option.strike:
            option_position_type = OptionPositionType.LONG if option_type == OptionType.CALL \
                else OptionPositionType.SHORT
        elif long_option.strike > short_option.strike:
            option_position_type = OptionPositionType.SHORT if option_type == OptionType.CALL \
                else OptionPositionType.LONG
        else:
            raise ValueError("Long and short strikes cannot be the same")

        vertical = Vertical(options=[long_option, short_option],
                            option_combination_type=OptionCombinationType.VERTICAL,
                            option_position_type=option_position_type, quantity=quantity)
        return vertical

    @classmethod
    def get_vertical_by_delta_and_spread_width(cls, *, option_chain: OptionChain, expiration: datetime.date,
                                               option_type: OptionType,
                                               option_position_type: OptionPositionType,
                                               delta: float,
                                               spread_width: int |float,
                                               quantity: int = 1) -> OptionCombination:

        # Find nearest matching expiration
        expirations = [e for e in option_chain.expirations if e >= expiration]

        if not expirations:
            message = "No matching expiration was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)
        expiration = expirations[0]

        options = [o for o in option_chain.option_chain if o.option_type == option_type and o.expiration == expiration]
        if option_type == OptionType.CALL:
            options.sort(key=lambda x: x.delta, reverse=True)
            select_options = [o for o in options if o.option_type == OptionType.CALL
                              and o.delta <= delta]
        else:
            options.sort(key=lambda x: x.delta, reverse=False)
            select_options = [o for o in options if o.option_type == OptionType.PUT
                              and o.delta >= -delta]

        if not select_options:
            message = "No option was found for the long delta value. Consider changing the selection filter."
            raise ValueError(message)

        option = options[0]
        option.option_position_type = option_position_type
        option.quantity = abs(quantity) if option_position_type == OptionPositionType.LONG else abs(quantity)*-1

        strikes = [s for s in option_chain.expiration_strikes[expiration]]
        if option_type == OptionType.CALL and option_position_type == OptionPositionType.LONG:
            strike = next(s for s in strikes if s >= option.strike + spread_width)
            next_option = [o for o in options if o.strike == strike]
        elif option_type == OptionType.CALL and option_position_type == OptionPositionType.SHORT:
            strikes.sort(reverse=True)
            strikes = [s for s in strikes if s <= option.strike - spread_width]
            strike = strikes[0]
        elif option_type == OptionType.PUT and option_position_type == OptionPositionType.LONG:
            strike = option.strike - spread_width
        elif option.option_type == OptionType.PUT and option_position_type == OptionPositionType.SHORT:
            strike = option.strike + spread_width

        pass


    short_option: Option = field(init=False, default=None)
    long_option: Option = field(init=False, default=None)

    def __post_init__(self):
        if not sum(o.quantity for o in self.options) == 0:
            message = "Invalid quantities. A Vertical Spread must have an equal number of long and short options."
            raise ValueError(message)
        if self.options[0].option_type != self.options[1].option_type:
            message = "Invalid option type. Both legs must be either calls or puts."
            raise ValueError(message)
        if self.options[0].expiration != self.options[0].expiration:
            message = "Invalid option expirations. Both legs must have the same expiration."
            raise ValueError(message)
        if self.option_position_type is None:
            raise ValueError("The parameter option_position_type: OptionPositionType must not be None")

        self.long_option = self.options[0] if self.options[0].quantity > 0 else self.options[1]
        self.short_option = self.options[0] if self.options[0].quantity < 0 else self.options[1]
        self.option_combination_type = OptionCombinationType.VERTICAL

    def update_quantity(self, quantity: int):
        self.quantity = quantity
        self.long_option.quantity = abs(quantity)
        self.short_option.quantity = abs(quantity) * -1

    def open_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        self.quantity = quantity if quantity is not None else self.long_option.quantity
        self.long_option.open_trade(quantity=self.quantity)
        self.short_option.open_trade(quantity=self.quantity * -1)
        super().open_trade(quantity=quantity, **kwargs)

    def close_trade(self, *, quantity: int | None = None, **kwargs: dict) -> None:
        quantity = quantity if quantity is not None else quantity == self.long_option.quantity
        self.long_option.close_trade(quantity=quantity)
        self.short_option.close_trade(quantity=quantity * -1)
        self.quantity -= quantity
        super().close_trade(quantity=quantity, **kwargs)

    @property
    def max_profit(self) -> float | None:
        if self.option_position_type == OptionPositionType.LONG:
            long_price = self.long_option.price if self.long_option.status == OptionStatus.INITIALIZED \
                else self.long_option.trade_price
            short_price = self.short_option.price if self.short_option.status == OptionStatus.INITIALIZED \
                else self.short_option.trade_price
            max_profit = float((abs(decimalize_2(self.long_option.strike) - decimalize_2(self.short_option.strike))
                                - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100)
        else:
            max_profit = self.trade_value * -1

        return max_profit

    @property
    def max_loss(self) -> float | None:
        if self.option_position_type == OptionPositionType.LONG:
            max_loss = self.trade_value
        else:
            long_price = self.long_option.trade_price
            short_price = self.short_option.trade_price
            quantity = self.long_option.trade_open_info.quantity \
                if OptionStatus.TRADE_IS_CLOSED in self.long_option.status \
                else self.quantity
            max_loss = float((abs(decimalize_2(self.long_option.strike) - decimalize_2(self.short_option.strike))
                              - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100 * abs(quantity))

        return max_loss

    @property
    def required_margin(self) -> float:
        if OptionStatus.TRADE_IS_OPEN not in self.long_option.status:
            return 0
        elif self.option_position_type == OptionPositionType.LONG:
            return 0
        elif self.option_position_type == OptionPositionType.SHORT:
            return abs((self.short_option.strike - self.long_option.strike) * 100 * self.quantity)

    @property
    def price(self) -> float:
        long_price = decimalize_2(self.long_option.price)
        short_price = decimalize_2(self.short_option.price)
        price = long_price - short_price
        return float(price)

    @property
    def expiration(self) -> datetime.date:
        return self.long_option.expiration

    @property
    def option_type(self) -> OptionType:
        return self.long_option.option_type

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED ==  self.long_option.status:
            return None
        else:
            long_price = decimalize_2(self.long_option.trade_open_info.price)
            short_price = decimalize_2(self.short_option.trade_open_info.price)
            trade_price = long_price - short_price
            return float(trade_price)
