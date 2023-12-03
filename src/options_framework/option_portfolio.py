import itertools

from dataclasses import dataclass, field
from typing import Optional

from options_framework.option import Option, TradeOpenInfo, TradeCloseInfo
from options_framework.option_types import OptionStatus
from options_framework.spreads.option_combo import OptionCombination

@dataclass(repr=False)
class OptionPortfolio:
    cash: float | int
    positions: Optional[dict] = field(init=False, default_factory=lambda: {})
    closed_positions: Optional[dict] = field(init=False, default_factory=lambda: {})
    portfolio_risk: float = field(init=False, default=0.0)

    def __repr__(self) -> str:
        return f'OptionPortfolio(cash={self.cash: .2f}, portfolio_value={self.portfolio_value:.2f} open positions: {len(self.open_positions)}'

    def open_position(self, option_position: OptionCombination, quantity: int):
        self.positions[option_position.position_id] = option_position
        [option.bind(open_transaction_completed=self.on_option_open_transaction_completed,
                     close_transaction_completed=self.on_option_close_transaction_completed,
                     option_expired=self.on_option_expired,
                     fees_incurred=self.on_fees_incurred) for option in option_position.options]
        option_position.open_trade(quantity=quantity)

    def close_position(self, option_position: OptionCombination, quantity: int):
        option_position.close_trade(quantity=quantity)
        self.closed_positions[option_position.position_id] = option_position
        del self.positions[option_position.position_id]
        [option.unbind(self) for option in option_position.options]

    @property
    def portfolio_value(self):
        current_value = sum(option.current_value for option in [option for position in self.positions.values()
                                                                for option in position.options])
        return self.cash + current_value

    def on_option_open_transaction_completed(self, trade_open_info: TradeOpenInfo):
        self.cash -= trade_open_info.premium
        print("portfolio: option position was opened")

    def on_option_close_transaction_completed(self, trade_close_info: TradeCloseInfo):
        self.cash += trade_close_info.premium
        print("portfolio: option position was closed")

    def on_option_expired(self, option_id):
        ids = [position.position_id for position in self.positions.values()
               for option in position.options if option.option_id == option_id]
        if ids:
            position = self.positions[ids[0]]
            if all([OptionStatus.EXPIRED in option.status for option in position.options]):
                self.close_position(position, position.quantity)
        print("portfolio: option expired")

    def on_fees_incurred(self, fees):
        self.cash -= fees
        print("portfolio: fees incurred")
