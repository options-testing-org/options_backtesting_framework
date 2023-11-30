from .option_combo import OptionCombination
from ..option_types import OptionCombinationType

class Collar(OptionCombination):
    def __init__(self, put_option, call_option, *args, **kwargs):
        self._option_combination_type = OptionCombinationType.COLLAR
        super().__init__([put_option, call_option], *args, **kwargs)
