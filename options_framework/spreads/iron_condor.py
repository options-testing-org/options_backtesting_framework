from .option_combo import OptionCombination
from ..option_types import OptionCombinationType

class IronCondor(OptionCombination):
    def __init__(self, outside_put_option, center_put_option, center_call_option, outside_call_option, *args, **kwargs):
        self._option_combination_type = OptionCombinationType.CONDOR
        super().__init__([outside_put_option, center_put_option, center_call_option, outside_call_option], *args, **kwargs)