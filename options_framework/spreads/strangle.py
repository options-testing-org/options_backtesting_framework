from .option_combo import OptionCombination
from ..option_types import OptionCombinationType

class Strangle(OptionCombination):

    def __init__(self, call_option, put_option, *args, **kwargs):
        self._option_combination_type = OptionCombinationType.STRANGLE
        super().__init__([call_option, put_option], *args, **kwargs)
        