from .option_combo import OptionCombination
from ..option_types import OptionCombinationType

class Calendar(OptionCombination):

    def __init__(self, first_option, second_option, *args, **kwargs):
        self._option_combination_type = OptionCombinationType.CALENDAR

        super().__init__([first_option, second_option], *args, **kwargs)