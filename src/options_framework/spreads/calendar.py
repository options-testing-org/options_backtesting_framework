from typing import Self

from .spread_base import SpreadBase
from ..option_chain import OptionChain
from ..option_types import OptionSpreadType, OptionStatus


@dataclass(repr=False, slots=True)
class Calendar(SpreadBase):

    front_option: Option = field(default=None)
    back_option: Option = field(default=None)

    @classmethod
    def create(cls, option_chain: OptionChain,
               front_expiration: datetime.date,
               front_strike: float,
               back_expiration: datetime.date,
               back_strike: float,
               *args, **kwargs) -> Self:


        pass

    def __post_init__(self):
        pass

    def __repr__(self) -> str:
        return "calendar"

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
    def price(self) -> float:
        pass

    def get_dte(self) -> int | None:
        pass

    def get_trade_price(self) -> float | None:
        pass

