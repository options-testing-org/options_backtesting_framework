import datetime

from dataclasses import dataclass, field
from typing import Optional

from options_framework.option import Option, TradeOpenInfo, TradeCloseInfo
from options_framework.option_types import OptionStatus, OptionPositionType
from options_framework.spreads.option_combo import OptionCombination
from options_framework.utils.helpers import decimalize_2
from pydispatch import Dispatcher

@dataclass(repr=False)
class OptionPortfolio(Dispatcher):

    _events_ = ['new_position_opened', 'position_closed', 'next', 'position_expired']

    cash: float | int
    positions: Optional[dict] = field(init=False, default_factory=lambda: {})
    closed_positions: Optional[dict] = field(init=False, default_factory=lambda: {})
    portfolio_risk: float = field(init=False, default=0.0)
    close_values: list = field(init=False, default_factory=lambda: [])

    def __post_init__(self):
        pass

    def __repr__(self) -> str:
        return f'OptionPortfolio(cash={self.cash: .2f}, portfolio_value={self.portfolio_value:.2f} open positions: {len(self.positions)}'

    def open_position(self, option_position: OptionCombination, quantity: int, **kwargs: dict):
        if option_position.option_position_type == OptionPositionType.SHORT:
            # check to see if we have enough margin to open this position
            new_margin = option_position.required_margin + self.portfolio_margin_allocation
            if new_margin > self.cash:
                raise ValueError(f'Insufficient margin available to open this position.')
        self.positions[option_position.position_id] = option_position
        [option.bind(open_transaction_completed=self.on_option_open_transaction_completed,
                     close_transaction_completed=self.on_option_close_transaction_completed,
                     option_expired=self.on_option_expired,
                     fees_incurred=self.on_fees_incurred) for option in option_position.options]
        option_position.open_trade(quantity=quantity, **kwargs)

        options = [option for position in self.positions.values() for option in position.options]
        for o in options:
            self.bind(next=o.next_update) # create hook for option update when next quote method is called
        self.emit("new_position_opened", self, option_position.options)

    def close_position(self, option_position: OptionCombination, quantity: int = None, **kwargs: dict):
        quantity = quantity if quantity is not None else option_position.quantity
        option_position.close_trade(quantity=quantity, **kwargs)
        self.closed_positions[option_position.position_id] = option_position
        del self.positions[option_position.position_id]
        self.emit("position_closed", option_position)
        [option.unbind(self) for option in option_position.options]

    def next(self, quote_datetime: datetime.datetime):
        self.emit('next', quote_datetime)
        self.close_values.append((quote_datetime, self.portfolio_value))

    @property
    def portfolio_value(self):
        current_value = sum(option.current_value for option in [option for position in self.positions.values()
                                                                for option in position.options])
        portfolio_value = decimalize_2(current_value) + decimalize_2(self.cash)
        return float(portfolio_value)

    @property
    def portfolio_margin_allocation(self):
        margin = sum(position.required_margin for position in self.positions.values())
        return margin

    def on_option_open_transaction_completed(self, trade_open_info: TradeOpenInfo):
        self.cash -= trade_open_info.premium
        #print(f"portfolio: option position was opened {trade_open_info.option_id}")

    def on_option_close_transaction_completed(self, trade_close_info: TradeCloseInfo):
        self.cash += trade_close_info.premium
        #print(f"portfolio: option position was closed {trade_close_info.option_id}")

    def on_option_expired(self, option_id):
        #print(f"portfolio: option expired {option_id}")
        ids = [position.position_id for position in self.positions.values()
               for option in position.options if option.option_id == option_id]
        if ids:
            position = self.positions[ids[0]]
            if all([OptionStatus.EXPIRED in option.status for option in position.options]):
                self.close_position(position, position.quantity)
                self.emit('position_expired', position)

    def on_fees_incurred(self, fees):
        self.cash -= fees
        #print("portfolio: fees incurred")

