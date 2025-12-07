from dataclasses import field

from options_framework.option_types import OptionPositionType, OptionCombinationType, OptionStatus
from options_framework.option_chain import OptionChain
from options_framework.spreads.option_combo import OptionCombination
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
import datetime


class Vertical(OptionCombination):

    @classmethod
    def get_vertical(cls, option_chain: OptionChain, expiration: datetime.date, option_type: str,
                     long_strike: int | float,
                     short_strike: int | float,
                     quantity: int = 1) -> OptionCombination:

        if long_strike < short_strike:
            option_position_type = OptionPositionType.LONG if option_type == 'call' \
                else OptionPositionType.SHORT
        elif long_strike > short_strike:
            option_position_type = OptionPositionType.SHORT if option_type == 'call' \
                else OptionPositionType.LONG
        else:
            raise ValueError("Long and short strikes cannot be the same")

            # Find nearest matching expiration
            try:
                expiration = next(e for e in option_chain.expirations if e >= expiration)
            except StopIteration:
                message = "No matching expiration was found in the option chain. Consider changing the selection filter."
                raise ValueError(message)

        expiration_strikes = option_chain.expiration_strikes[expiration].copy()
        options = [o for o in option_chain.option_chain if o['option_type'] == option_type and o['expiration'] == expiration].copy()
        try:
            # Find nearest strikes
            if option_type == 'call':
                long_strike = next(s for s in expiration_strikes if s >= long_strike)
                short_strike = next(s for s in expiration_strikes if s >= short_strike)
            else:
                expiration_strikes.sort(reverse=True)
                long_strike = next(s for s in expiration_strikes if s <= long_strike)
                short_strike = next(s for s in expiration_strikes if s <= short_strike)
        except StopIteration as ex:
            message = "No matching strike was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)

        long_dict = next(o for o in options if o['strike'] == long_strike)
        long_option = Option(**long_dict)
        long_option.quantity = quantity
        short_dict = next(o for o in options if o['strike'] == short_strike)
        short_option = Option(**short_dict)
        short_option.quantity = quantity * -1

        vertical = Vertical(options=[long_option, short_option],
                            option_combination_type=OptionCombinationType.VERTICAL,
                            option_position_type=option_position_type, quantity=quantity)
        return vertical

    @classmethod
    def get_vertical_by_delta(cls, option_chain: OptionChain, expiration: datetime.date, option_type: str,
                     long_delta: float,
                     short_delta: float,
                     quantity: int = 1) -> OptionCombination:

        long_delta, short_delta = abs(long_delta), abs(short_delta)
        if abs(long_delta) > abs(short_delta):
            option_position_type = OptionPositionType.LONG if option_type == 'call' \
                else OptionPositionType.SHORT
        elif abs(long_delta) < abs(short_delta):
            option_position_type = OptionPositionType.SHORT if option_type == 'call' \
                else OptionPositionType.LONG
        else:
            raise ValueError("Long and short strikes cannot be the same")

        # if option_type == OptionType.PUT:
        #     long_delta, short_delta = abs(long_delta)*-1, abs(short_delta)*-1

        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)

        options = [o for o in option_chain.option_chain if o.option_type == option_type and o.expiration == expiration].copy()
        if not options:
            message = "No matching expiration was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)
        try:
            if option_type == 'call':
                long_option = next(o for o in options if o.delta <= long_delta)
                short_option = next(o for o in options if o.delta <= short_delta)
            else:
                options.sort(key=lambda x: x.delta, reverse=False)
                long_option = next(o for o in options if o.delta >= -long_delta)
                short_option = next(o for o in options if o.delta >= -short_delta)
        except StopIteration:
            message = "No matching delta value was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)

        # Set quantities
        long_option.quantity = abs(quantity)
        short_option.quantity = abs(quantity) * -1
        quantity = abs(quantity) if option_position_type == OptionPositionType.LONG else abs(quantity)*-1

        long_option.position_type = OptionPositionType.LONG
        short_option.position_type = OptionPositionType.SHORT

        if long_option.strike < short_option.strike:
            option_position_type = OptionPositionType.LONG if option_type == 'call' \
                else OptionPositionType.SHORT
        elif long_option.strike > short_option.strike:
            option_position_type = OptionPositionType.SHORT if option_type == 'call' \
                else OptionPositionType.LONG
        else:
            raise ValueError("Long and short strikes cannot be the same")

        vertical = Vertical(options=[long_option, short_option],
                            option_combination_type=OptionCombinationType.VERTICAL,
                            option_position_type=option_position_type, quantity=quantity)
        return vertical

    @classmethod
    def get_vertical_by_delta_and_spread_width(cls, option_chain: OptionChain, expiration: datetime.date,
                                               option_type: str,
                                               option_position_type: OptionPositionType,
                                               delta: float,
                                               spread_width: int |float,
                                               quantity: int = 1) -> OptionCombination:

        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)

        options = [o for o in option_chain.option_chain if o.option_type == option_type and o.expiration == expiration].copy()
        strikes = [s for s in option_chain.expiration_strikes[expiration]].copy()
        try:
            if option_type == 'call':
                option = next(o for o in options if o.delta <= delta)
                target_strike = option.strike + spread_width
                strike = next(s for s in strikes if s >= target_strike)

            else:
                options.sort(key=lambda x: x.delta, reverse=False)
                option = next(o for o in options if o.delta >= -delta)
                target_strike = option.strike - spread_width
                strikes.sort(reverse=True)
                strike = next(s for s in strikes if s <= target_strike)

            next_option = next(o for o in options if o.strike == strike)

        except StopIteration:
            message = "Vertical could not be created with the delta value. Consider changing the selection filter."
            raise ValueError(message)

        long_option = option if option_position_type == OptionPositionType.LONG else next_option
        short_option = option if option_position_type == OptionPositionType.SHORT else next_option

        long_option.quantity = abs(quantity)
        long_option.option_position_type = OptionPositionType.LONG
        short_option.quantity = abs(quantity)*-1
        short_option.option_position_type = OptionPositionType.SHORT

        quantity = abs(quantity) if option_position_type == OptionPositionType.LONG else abs(quantity)*-1

        vertical = Vertical(options=[long_option, short_option],
                            option_combination_type=OptionCombinationType.VERTICAL,
                            option_position_type=option_position_type, quantity=quantity)
        return vertical

    short_option: Option = field(init=False, default=None)
    long_option: Option = field(init=False, default=None)

    def __post_init__(self):
        message = None
        if any(o for o in self.options if o.quantity == 0):
            message = "Quantity must be set for each option. Short options should have a negative quantity, and long options should have a positive quantity."
        if not sum(o.quantity for o in self.options) == 0:
            message = "Invalid quantities. A Vertical Spread must have an equal number of long and short options."
        if self.options[0].option_type != self.options[1].option_type:
            message = "Invalid option type. Both legs must be either calls or puts."
        if self.options[0].expiration != self.options[0].expiration:
            message = "Invalid option expirations. Both legs must have the same expiration."
        # if self.option_position_type is None:
        #     message = "The parameter option_position_type: OptionPositionType must not be None"
        if self.options[0].strike == self.options[1].strike:
            message = "Long and short option strikes must not be the same option."
        if message is not None:
            raise ValueError(message)

        self.long_option = self.options[0] if self.options[0].quantity > 0 else self.options[1]
        self.long_option.position_type = OptionPositionType.LONG
        self.short_option = self.options[0] if self.options[0].quantity < 0 else self.options[1]
        self.short_option.position_type = OptionPositionType.SHORT
        self.option_combination_type = OptionCombinationType.VERTICAL

    def __repr__(self) -> str:
        strikes = [self.long_option.strike, self.short_option.strike]
        if self.option_type == 'call':
            strikes.sort()
        else:
            strikes.sort(reverse=True)
        s = f'<{self.option_combination_type.name}({self.position_id}) {self.option_type.upper()} {self.option_position_type.name} ' \
                + f'{self.symbol} {strikes[0]}/{strikes[1]} ' \
                + f'Expiring {self.expiration}>'
        return s

    def update_quantity(self, quantity: int):
        self.quantity = quantity
        self.long_option.quantity = abs(quantity)
        self.short_option.quantity = abs(quantity) * -1

    def open_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        self.quantity = quantity if quantity is not None else self.long_option.quantity
        self.long_option.open_trade(quantity=self.quantity)
        self.short_option.open_trade(quantity=self.quantity * -1)
        super(Vertical, self).open_trade(quantity=quantity, **kwargs)

    def close_trade(self, *, quantity: int | None = None, **kwargs: dict) -> None:
        quantity = quantity if quantity is not None else quantity == self.long_option.quantity
        self.long_option.close_trade(quantity=quantity)
        self.short_option.close_trade(quantity=quantity * -1)
        self.quantity -= quantity
        super(Vertical, self).close_trade(quantity=quantity, **kwargs)

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
    def option_type(self) -> str:
        return self.long_option.option_type

    @property
    def symbol(self):
        return self.long_option.symbol

    @property
    def status(self) -> OptionStatus:
        return self.long_option.status

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED ==  self.long_option.status:
            return None
        else:
            long_price = decimalize_2(self.long_option.trade_open_info.price)
            short_price = decimalize_2(self.short_option.trade_open_info.price)
            trade_price = long_price - short_price
            return float(trade_price)

    @property
    def closed_value(self) -> float | None:
        closed_value = super(Vertical, self).closed_value
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            if closed_value > self.max_profit:
                closed_value = self.max_profit
            elif closed_value < self.max_loss * -1:
                closed_value = self.max_loss * -1

        return closed_value

    def get_profit_loss(self) -> float:
        profit_loss = super(Vertical, self).get_profit_loss()
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            closed_value = self.closed_value
            if closed_value > self.max_profit or closed_value < self.max_loss * -1:
                fees = self.get_fees()
                profit_loss = closed_value + fees

        return profit_loss
