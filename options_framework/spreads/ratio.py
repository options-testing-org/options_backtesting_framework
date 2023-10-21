from .option_combo import OptionCombination
from ..option_types import OptionCombinationType

class Ratio(OptionCombination):

    def __init__(self, long_option, short_option, *args, **kwargs):
        self._option_combination_type = OptionCombinationType.RATIO

        super().__init__([long_option, short_option], short_option, *args,)