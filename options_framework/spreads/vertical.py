from options_framework.option_types import OptionPositionType, OptionType, OptionTradeType, OptionCombinationType
from options_framework.spreads.option_combo import OptionCombination
from options_framework.utils.helpers import decimalize_0, decimalize_2


class Vertical(OptionCombination):

    def __init__(self, long_option, short_option, *args, **kwargs):
        if not long_option.position_type == OptionPositionType.LONG:
            raise ValueError("The long_option parameter must be a long option.")
        if not short_option.position_type == OptionPositionType.SHORT:
            raise ValueError("The short_option parameter must be a short option.")
        if long_option.option_type != short_option.option_type:
            raise ValueError("A vertical spread must contain options of the same type. Both must be calls or puts.")
        if long_option.expiration != short_option.expiration:
            raise ValueError("All options in the spread must have the same expiration")
        if abs(long_option.quantity) != abs(short_option.quantity):
            raise ValueError("Both options must have the same absolute quantity for both long and short legs")
        if long_option.strike == short_option.strike:
            raise ValueError("The options provided do not form a vertical spread")

        self._option_combination_type = OptionCombinationType.VERTICAL
        self._option_type = long_option.option_type

        # determine if this is a debit or credit spread
        if self._option_type == OptionType.CALL:
            self._option_trade_type = OptionTradeType.DEBIT if long_option.strike < short_option.strike \
                else OptionTradeType.CREDIT
        elif self._option_type == OptionType.PUT:
            self._option_trade_type = OptionTradeType.DEBIT if long_option.strike > short_option.strike \
                else OptionTradeType.CREDIT

        super().__init__([long_option, short_option], args, kwargs)
        self._long_option = self._options[0]
        self._short_option = self._options[1]

    @property
    def option_trade_type(self):
        return self._option_trade_type

    @property
    def option_type(self):
        return self._option_type

    def max_profit(self):
        # call debit: Max profit = the spread between the strike prices - net premium paid.
        # call credit: Max profit = net premium received.
        # put debit: Max profit = the spread between the strike prices - net premium paid.
        # put credit: Max profit = net premium received.
        long_price = decimalize_2(self._long_option.trade_price)
        short_price = decimalize_2(self._short_option.trade_price)
        if self._option_trade_type == OptionTradeType.DEBIT:
            max_profit = ((self.spread_width() - (long_price-short_price)) * 100
                                * self._long_option.quantity)
        else:
            max_profit = (long_price-short_price)*100*self._short_option.quantity
        return float(max_profit)

    def max_loss(self):
        long_price = decimalize_2(self._long_option.trade_price)
        short_price = decimalize_2(self._short_option.trade_price)
        quantity = decimalize_0(self._long_option.quantity)
        if self._option_trade_type == OptionTradeType.DEBIT:
            max_loss = (long_price-short_price) * 100 * quantity
        else:
            max_loss = ((self.spread_width() - (short_price - long_price)) * 100 * quantity)

        return float(max_loss)

    def spread_width(self):
        return abs(self._long_option.strike - self._short_option.strike)

    def total_premium(self):
        # long_price = decimalize_2(self._long_option.trade_price)
        # short_price = decimalize_2(self._short_option.trade_price)
        # quantity = decimalize_0(self._long_option.quantity)
        # premium = (long_price-short_price) * 100 * quantity
        total_premium = self.premium() * 100 * self._long_option.quantity
        return total_premium

    def breakeven_price(self):
        long_price = decimalize_2(self._long_option.trade_price)
        short_price = decimalize_2(self._short_option.trade_price)
        breakeven_price = None
        # Call debit spread: Breakeven point = long call's strike price + net premium paid.
        if self._option_trade_type == OptionTradeType.DEBIT and self._option_type == OptionType.CALL:
            breakeven_price = self._long_option.strike + (long_price - short_price)
        # Call credit spread: Breakeven point = short call's strike price + net premium received.
        elif self._option_trade_type == OptionTradeType.CREDIT and self._option_type == OptionType.CALL:
            breakeven_price = self._short_option.strike + (short_price - long_price)
        # Put debit spread: Breakeven point = long put's strike price - net premium paid.
        elif self._option_trade_type == OptionTradeType.DEBIT and self._option_type == OptionType.PUT:
            breakeven_price = self._long_option.strike - (long_price - short_price)
        # Put credit spread: Breakeven point = short put's strike price - net premium received.
        elif self._option_trade_type == OptionTradeType.CREDIT and self._option_type == OptionType.PUT:
            breakeven_price = self._short_option.strike - (short_price - long_price)

        return float(breakeven_price)
