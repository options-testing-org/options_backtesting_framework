from dataclasses import dataclass
import datetime
from options_framework.option import Option
from options_framework.option_types import OptionType
from options_framework.spreads.option_combo import OptionCombination

@dataclass(repr=False, slots=True)
class Butterfly(OptionCombination):

    @classmethod
    def get_butterfly_position(cls, *, options: list[Option], expiration: datetime.date, option_type: OptionType,
                               center_strike: int | float, wing_width: int | float) -> OptionCombination:
        return None

    # def __init__(self, first_option, center_option, third_option, *args, **kwargs):
    #     options = [first_option, center_option, third_option]
    #     if not all(o.expiration == first_option[0].expiration for o in options):
    #         raise ValueError("All options in the spread must have the same expiration")
    #     if not first_option.strike < center_option.strike < third_option.strike:
    #         raise ValueError("The options provided do not form a butterfly spread")
    
