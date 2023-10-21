from options_framework.option_types import OptionType, OptionCombinationType, OptionPositionType, OptionTradeType
from options_framework.spreads.option_combo import OptionCombination
from options_framework.utils.helpers import decimalize_2

class Single(OptionCombination):

    def __init__(self, option, *args, **kwargs):
        self._option = option
        self._option_combination_type = OptionCombinationType.SINGLE
        super().__init__([option], args, kwargs)

    @property
    def option_trade_type(self):
        if self._option.position_type == OptionPositionType.LONG:
            return OptionTradeType.DEBIT
        else:
            return OptionTradeType.CREDIT

    def breakeven_price(self):
        trade_price = decimalize_2(self._option.trade_price)

        if self._option.option_type == OptionType.CALL:
            breakeven_price = self._option.strike + trade_price
        else:
            breakeven_price = self._option.strike - trade_price

        return float(breakeven_price)

