from options_framework.spreads.option_combo import OptionCombination
from options_framework.option_types import OptionCombinationType

class TestCombo(OptionCombination):

    def __post_init__(self):
        print('init test class')

    def open_trade(self, *, quantity: int, **kwargs: dict) -> None:
        pass

    def close_trade(self, *, quantity: int, **kwargs: dict) -> None:
        pass

    def max_profit(self) -> float | None:
        return None

    def max_loss(self) -> float | None:
        return None

    def get_trade_price(self) -> float | None:
        pass

def test_test():
    test_combo = TestCombo(options=[], option_combination_type=OptionCombinationType.CUSTOM)

    assert test_combo.quantity == 1
