from __future__ import annotations

import datetime
import itertools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, InitVar
from typing import Optional, Self

from ..option import Option
from ..option_chain import OptionChain
from ..option_types import OptionSpreadType, OptionStatus, OptionPositionType


@dataclass(repr=False, slots=True)
class SpreadBase(ABC):
    """
    OptionCombination is a base class an options trade that is constructed with one or more option types,
    quantities, and expirations.
    There are several pre-defined classes for popular options spreads, but you can create a
    custom class, or just pass a list of options that make up the trade
    """

    options: list[Option] = field(default=None)
    spread_type: OptionSpreadType = field(default=None)
    quantity: int = field(default=0)
    instance_id: int = field(init=False, default_factory=lambda counter=itertools.count(): next(counter))
    position_type: Optional[OptionPositionType] = field(default=None)
    user_defined: dict = field(default_factory=lambda: {}, compare=False)

    def __post_init__(self):
        # The OptionCombination object should not be instantiated directly, but only through subclasses.
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def create(cls, option_chain: OptionChain, *args, **kwargs) -> Self:
        raise NotImplementedError

    @abstractmethod
    def open_trade(self, quantity: int = 1, *args, **kwargs: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def close_trade(self, quantity: int | None = None, *args, **kwargs: dict) -> None:
        raise NotImplementedError

    @property
    def current_value(self) -> float:
        current_value = sum(o.current_value for o in self.options)
        return current_value

    @property
    def trade_value(self) -> float:
        opening_value = sum([o.trade_value for o in self.options])
        return opening_value

    @property
    def closed_value(self) -> float | None:
        if all(o for o in self.options if o.trade_close_info is not None):
            closed_value = sum(o.trade_close_info.premium for o in self.options if o.trade_close_info is not None)
            return closed_value
        else:
            return None

    @classmethod
    def _save_user_defined_values(cls, obj, **kwargs: dict) -> None:
        for arg, val in kwargs.items():
            obj.user_defined[arg] = val

    @property
    @abstractmethod
    def max_profit(self) -> float | None:
        raise NotImplementedError

    @property
    @abstractmethod
    def max_loss(self) -> float | None:
        raise NotImplementedError

    @property
    @abstractmethod
    def required_margin(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def status(self) -> OptionStatus:
        raise NotImplementedError

    @property
    def symbol(self) -> str:
        return self.options[0].symbol

    @property
    @abstractmethod
    def price(self) -> float:
        raise NotImplementedError

    @property
    def quote_datetime(self) -> datetime.datetime:
        return self.options[0].quote_datetime

    def get_profit_loss(self) -> float:
        pnl = sum(o.get_profit_loss() for o in self.options)
        return pnl

    def get_unrealized_profit_loss(self) -> float:
        pnl = sum(o.get_unrealized_profit_loss() for o in self.options)
        return pnl

    def get_trade_premium(self) -> float | None:
        if any(OptionStatus.INITIALIZED in o.status for o in self.options):
            return None
        else:
            return sum(o.trade_open_info.premium for o in self.options)

    def get_profit_loss_percent(self) -> float:
        pnl_pct = sum(o.get_profit_loss_percent() for o in self.options)
        return round(pnl_pct, 4)


    def get_unrealized_profit_loss_percent(self) -> float:
        pnl_pct = sum(o.get_unrealized_profit_loss_percent() for o in self.options)
        return round(pnl_pct, 4)

    def get_days_in_trade(self) -> int | None:
        if all(x.status == OptionStatus.INITIALIZED for x in self.options):
            return None
        options_days = [x.get_days_in_trade() for x in self.options]
        days_in_trade = max(options_days)
        return days_in_trade

    @abstractmethod
    def get_dte(self) -> int | None:
        return NotImplementedError

    @abstractmethod
    def get_trade_price(self) -> float | None:
        raise NotImplementedError

    def get_open_datetime(self) -> datetime.datetime | None:
        first_option = self.options[0]
        if (OptionStatus.TRADE_IS_OPEN & OptionStatus.TRADE_IS_CLOSED) not in first_option.status:
            return None
        open_date = first_option.trade_open_info.date
        return open_date

    def get_close_datetime(self):
        closed_options = [x for x in self.options if OptionStatus.TRADE_IS_CLOSED in x.status]
        if len(closed_options) > 0:
            close_dates = [x.trade_close_info.date for x in closed_options]
            max_close = max(close_dates)
        else:
            max_close = None

        return max_close

    def get_fees(self):
        fees = 0

        for o in self.options:
            if OptionStatus.TRADE_IS_OPEN in o.status:
                fees += o.trade_open_info.fees
            if OptionStatus.TRADE_PARTIALLY_CLOSED in o.status:
                fees += o.trade_close_info.fees
            if OptionStatus.TRADE_IS_CLOSED in o.status:
                fees += o.trade_open_info.fees
                fees += o.trade_close_info.fees

        return fees
