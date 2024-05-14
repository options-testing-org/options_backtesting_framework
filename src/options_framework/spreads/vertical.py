from dataclasses import field

from options_framework.option_types import OptionPositionType, OptionType, OptionTradeType, OptionCombinationType, \
    TransactionType, OptionStatus
from options_framework.spreads.option_combo import OptionCombination
from options_framework.utils.helpers import decimalize_0, decimalize_2
from options_framework.option import Option
import datetime


class Vertical(OptionCombination):

    @classmethod
    def get_vertical(cls, *, option_chain: list[Option], expiration: datetime.date, option_type: OptionType,
                     long_strike: int | float,
                     short_strike: int | float,
                     quantity: int = 1):
        if long_strike < short_strike:
            option_position_type = OptionPositionType.LONG if option_type == OptionType.CALL else OptionPositionType.SHORT
        elif long_strike > short_strike:
            option_position_type = OptionPositionType.SHORT if option_type == OptionType.CALL else OptionPositionType.LONG
        else:
            ex = ValueError
            ex.message = "Long and short strikes cannot be the same"
            raise ex

        candidates = [o for o in option_chain if o.expiration == expiration
                      and o.option_type == option_type and o.strike >= long_strike]
        if not candidates:
            raise ValueError("No option was found for the first strike")

        long_option = candidates[0]
        long_option.quantity = quantity

        option_chain.sort(key=lambda x: x.strike, reverse=True)
        candidates = [o for o in option_chain if o.expiration == expiration
                      and o.option_type == option_type and o.strike <= (short_strike)]
        if not candidates or candidates[0].strike == long_option.strike:
            raise ValueError("No option was found for the second strike")

        short_option = candidates[0]
        short_option.quantity = quantity * -1

        vertical = Vertical(options=[long_option, short_option],
                            option_combination_type=OptionCombinationType.VERTICAL,
                            option_position_type=option_position_type)
        return vertical

    short_option: Option = field(init=False, default=None)
    long_option: Option = field(init=False, default=None)

    def __post_init__(self):
        if not sum(o.quantity for o in self.options) == 0:
            ex = ValueError
            ex.message = "Invalid quantities. A Vertical Spread must have an equal number of long and short options."
            raise ex
        if self.options[0].option_type != self.options[1].option_type:
            ex = ValueError
            ex.message = "Invalid option type. Both options must be either calls or puts."
            raise ex

        self.long_option = self.options[0] if self.options[0].quantity > 0 else self.options[1]
        self.short_option = self.options[0] if self.options[0].quantity < 0 else self.options[1]

    def open_trade(self, *, quantity: int = None, **kwargs: dict) -> None:
        quantity = quantity if quantity is not None else self.long_option.quantity
        self.long_option.open_trade(quantity=quantity)
        self.short_option.open_trade(quantity=quantity * -1)

    def close_trade(self, *, quantity: int = None, **kwargs: dict) -> None:
        quantity = quantity if quantity is not None else quantity == self.long_option.quantity
        self.long_option.close_trade(quantity=quantity)
        self.short_option.close_trade(quantity=quantity * -1)

    @property
    def max_profit(self) -> float | None:
        long_price = self.long_option.trade_price if OptionStatus.TRADE_IS_OPEN in self.long_option.status \
            else self.long_option.price
        short_price = self.short_option.trade_price if OptionStatus.TRADE_IS_OPEN in self.short_option.status \
            else self.short_option.price
        if self.option_position_type == OptionPositionType.LONG:
            max_profit = float((abs(decimalize_2(self.long_option.strike) - decimalize_2(self.short_option.strike))
                                - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100)
        else:
            max_profit = self.trade_value * -1

        return max_profit

    @property
    def max_loss(self) -> float | None:
        long_price = self.long_option.trade_price if OptionStatus.TRADE_IS_OPEN in self.long_option.status \
            else self.long_option.price
        short_price = self.short_option.trade_price if OptionStatus.TRADE_IS_OPEN in self.short_option.status \
            else self.short_option.price
        if self.option_position_type == OptionPositionType.SHORT:
            max_loss = float((abs(decimalize_2(self.long_option.strike) - decimalize_2(self.short_option.strike))
                              - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100)
        else:
            max_loss = self.trade_value

        return max_loss

    def get_trade_price(self) -> float | None:
        long_price = self.long_option.trade_price if OptionStatus.TRADE_IS_OPEN in self.long_option.status \
            else self.long_option.price
        short_price = self.short_option.trade_price if OptionStatus.TRADE_IS_OPEN in self.short_option.status \
            else self.short_option.price

        trade_price = decimalize_2(long_price) - decimalize_2(short_price)
        return float(trade_price)
