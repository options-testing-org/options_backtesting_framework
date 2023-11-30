from dataclasses import dataclass, field
from typing import Optional

from options_framework.option import Option, TradeOpenInfo, TradeCloseInfo
from options_framework.spreads.option_combo import OptionCombination


@dataclass
class OptionPortfolio:

    cash: float | int
    positions: Optional[list[OptionCombination]] = field(init=False, default_factory=list[OptionCombination])
    closed_positions: Optional[list[OptionCombination]] = field(init=False, default_factory=list[OptionCombination])
    portfolio_risk: float = field(init=False, default=0.0)

    def open_position(self, option_position: OptionCombination, quantity: int):
        self.positions.append(option_position)
        for option in option_position.options:
            option.bind(open_transaction_completed=self.on_option_open_transaction_completed,
                        close_transaction_completed=self.on_option_close_transaction_completed,
                        option_expired=self.on_option_expired,
                        option_values_updated=self.on_option_price_updated,
                        fees_incurred=self.on_fees_incurred)

        option_position.open_trade(quantity=quantity)

    @property
    def portfolio_value(self):
        current_value = sum(option.current_value for option in sum([x.options for x in self.positions], []))
        return self.cash + current_value

    def on_option_open_transaction_completed(self, trade_open_info: TradeOpenInfo):
        self.cash -= trade_open_info.premium
        print("portfolio: option position was opened")

    def on_option_close_transaction_completed(self, trade_close_info: TradeCloseInfo):
        print("portfolio: option position was closed")

    def on_option_expired(self, option_id):
        print("portfolio: option expired")

    def on_option_price_updated(self, option_id, new_values):
        print("portfolio: option updated")

    def on_fees_incurred(self, option_id, fees):
        self.cash -= fees
        print("portfolio: fees incurred")

