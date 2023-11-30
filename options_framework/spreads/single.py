import datetime
import weakref

from options_framework.option import Option
from options_framework.option_types import OptionType, OptionCombinationType
from options_framework.spreads.option_combo import OptionCombination

class Single(OptionCombination):

    def __init__(self, option: Option, *args, **kwargs):
        self.option = option
        self.expiration = option.expiration
        self.option_type = option.option_type
        self.strike = option.strike
        self._option_combination_type = OptionCombinationType.SINGLE
        super().__init__([option], args, kwargs)

    @classmethod
    def get_single_option(cls, *, options: list[Option], expiration: datetime.date, option_type: OptionType,
                          strike: float | int):

        candidates = [o for o in options if o.expiration == expiration
                      and o.option_type == option_type and o.strike == strike]
        if not candidates:
            raise ValueError("No option was found")
        if len(candidates) > 1:
            raise ValueError("Multiple options match the parameters provided.")
        option = candidates[0]
        single = Single(option)
        return single

    def open_trade(self, *, quantity: int, **kwargs: dict):
        self.option.open_trade(quantity=quantity)

