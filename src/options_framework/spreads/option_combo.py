import datetime
import itertools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..option import Option
from ..option_types import OptionCombinationType, OptionStatus


@dataclass(repr=False, slots=True)
class OptionCombination(ABC):
    """
    OptionCombination is a base class an options trade that is constructed with one or more option types,
    quantities, and expirations.
    There are several pre-defined classes for popular options spreads, but you can create a
    custom class, or just pass a list of options that make up the trade
    """

    options: list[Option]
    option_combination_type: OptionCombinationType
    position_id: int = field(init=False, default_factory=lambda counter=itertools.count(): next(counter))
    quantity: int = field(default=1)

    def __post_init__(self):
        # The OptionCombination object should not be instantiated directly, but only through subclasses.
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'<{self.option_combination_type.name}({self.position_id}) Quantity: {len(self.options)} options>'

    def advance_to_next(self, quote_datetime: datetime.datetime) -> None:
        """
        Notifies the options that the quote date has changed. They need to update their values to the current quote
        :param quote_datetime:
        :return: None
        """
        for option in self.options:
            option.next_update(quote_datetime=quote_datetime)

    @property
    def current_value(self) -> float:
        current_value = sum([o.current_value for o in self.options])
        return current_value

    @abstractmethod
    def open_trade(self, *, quantity: int, **kwargs: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def close_trade(self, *, quantity: int, **kwargs: dict) -> None:
        raise NotImplementedError

    @property
    def max_profit(self) -> float | None:
        """
        If there is a determinate max profit, that is returned by the parent class.
        If there is an infinite max profit, as is the case for a naked option type, returns None
        :return: None or the max profit of the spread
        """
        return None

    @property
    def max_loss(self) -> float | None:
        """
        If there is a determinate max loss, that is returned by the parent class.
        If there is an infinite max loss, as is the case for a naked option type, returns None
        :return: None or the max loss of the spread
        """
        return None

    #
    # def premium(self):
    #     """
    #
    #     :return:
    #     """
    #     if not all(o.trade_open_date is not None for o in self._options):
    #         raise ValueError("Premium cannot be calculated unless a trade has been opened for all options")
    #     premium = sum(decimalize_2(o.price) * (decimalize_2(o.quantity)/abs(decimalize_2(o.quantity)))
    #                   for o in self._options)
    #     return float(premium)
    #
    # def trade_cost(self):
    #     """
    #     The net premium to open the trade
    #     :return: A positive number indicates a debit, and a negative number indicates a credit
    #     """
    #     if not all(o.trade_open_date is not None for o in self._options):
    #         raise ValueError("Trade cost cannot be calculated unless a trade has been opened for all options")
    #     return sum(o.total_premium() for o in self._options)
    #
    # def current_gain_loss(self):
    #     """
    #     The current gain or loss. This is the unrealized gain or loss unless the trade is closed.
    #     :return: sum of the current value of all options in the trade
    #     """
    #     if not all(o.trade_open_date is not None for o in self._options):
    #         raise ValueError("Current value cannot be calculated unless a trade has been opened for all options")
    #     return sum(o.current_gain_loss() for o in self._options)
    #
    # def profit_loss_percent(self):
    #     """
    #     The current gain or loss percentage. This is the unrealized gain or loss unless the trade is closed.
    #     :return:
    #     """
    #     starting_value = decimalize_2(self.trade_cost())
    #     total_current_value = starting_value + decimalize_2(self.current_gain_loss())
    #     percent_gain_loss = (total_current_value - starting_value) / starting_value
    #     return float(decimalize_4(percent_gain_loss))



    # @property
    # def option_combination_type(self):
    #     """
    #     Returns the type of spread of the parent class.
    #     The different types of spreads are defined in the OptionCombinationType enum.
    #     :return: The option combination type of the parent class
    #     """
    #     return self._option_combination_type
    #
    # @property
    # def option_trade_type(self):
    #     """
    #     Determines whether the premium is positive or negative.
    #     If net positive, the trader paid to purchase the options, and the spread is a debit
    #     If net negative, the trader received premium, and the spread is a credit
    #     :return: OptionTradeType.CREDIT or OptionTradeType.DEBIT
    #     """
    #     return OptionTradeType.CREDIT if self.premium() < 0 else OptionTradeType.DEBIT
