from .spread_base import SpreadBase
from ..option_types import OptionSpreadType, OptionStatus


class Strangle(SpreadBase):
    def update_quantity(self, quantity: int):
        pass

    def open_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        pass

    def close_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        pass

    @property
    def required_margin(self) -> float:
        pass

    @property
    def status(self) -> OptionStatus:
        pass

    @property
    def symbol(self) -> OptionStatus:
        pass

    def get_trade_price(self) -> float | None:
        pass
        