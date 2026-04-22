from typing import Self

from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionStatus
from spread_base import SpreadBase

class Custom(SpreadBase):
    @classmethod
    def create(cls, option_chain: OptionChain, *args, **kwargs) -> Self:
        pass

    def open_trade(self, quantity: int = 1, *args, **kwargs: dict) -> None:
        pass

    def close_trade(self, quantity: int | None = None, *args, **kwargs: dict) -> None:
        pass

    @property
    def max_profit(self) -> float | None:
        pass

    @property
    def max_loss(self) -> float | None:
        pass

    def get_required_margin(self, quantity: int) -> float:
        pass

    @property
    def status(self) -> OptionStatus:
        pass

    @property
    def symbol(self) -> str:
        pass

    @property
    def price(self) -> float:
        pass

    def get_dte(self) -> int | None:
        pass

    def get_trade_price(self) -> float | None:
        pass

    def get_closed_price(self) -> float | None:
        pass

    def get_price_history(self) -> list[tuple]:
        pass

