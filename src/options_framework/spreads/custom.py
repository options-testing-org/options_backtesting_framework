from option_combo import OptionCombination

class CustomOptionSpread(OptionCombination):

    def __init__(self, options, *args, **kwargs):
        super().__init__(options, *args, **kwargs)