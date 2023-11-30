from .option_combo import OptionCombination
from ..option_types import OptionCombinationType

class Condor(OptionCombination):
    def __init__(self, option_strike_1, option_strike_2, option_strike_3, option_strike_4, *args, **kwargs):
        self._option_combination_type = OptionCombinationType.CONDOR
        super().__init__([option_strike_1, option_strike_2, option_strike_3, option_strike_4], *args, **kwargs)