import datetime
from dataclasses import dataclass, field
from typing import Optional

from options_framework.option import Option
from options_framework.option_types import OptionType, OptionCombinationType
from options_framework.spreads.option_combo import OptionCombination

@dataclass(repr=False, slots=True)
class Single(OptionCombination):

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
        single = Single(options=[option])
        return single

    option: Optional[Option] = field(default=None)

    def __post_init__(self):
        self.option = self.options[0]
        self.option_combination_type = OptionCombinationType.SINGLE

    @property
    def expiration(self):
        return self.option.expiration

    @property
    def option_type(self):
        return self.option.option_type

    @property
    def strike(self):
        return self.option.strike

    def open_trade(self, *, quantity: int, **kwargs: dict):
        self.option.open_trade(quantity=quantity)

    def close_trade(self, *, quantity: int, **kwargs: dict):
        self.option.close_trade(quantity=quantity)
