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
    start_date: datetime.datetime
    end_date: datetime.datetime
    current_datetime: datetime.datetime = field(init=False, default=None)
    positions: Optional[dict] = field(init=False, default_factory=lambda: {})
    closed_positions: Optional[dict] = field(init=False, default_factory=lambda: {})
    portfolio_risk: float = field(init=False, default=0.0)
    close_values: list = field(init=False, default_factory=lambda: [])

    def __post_init__(self):
        pass

    def __repr__(self) -> str:
        return f'OptionPortfolio(cash={self.cash: .2f}, portfolio_value={self.portfolio_value:.2f} open positions: {len(self.positions)}'

    def open_position(self, option_position: OptionCombination, quantity: int, **kwargs: dict):
        option_position.update_quantity(quantity)
        if option_position.option_position_type == OptionPositionType.SHORT:
            # check to see if we have enough margin to open this position
            new_margin = option_position.required_margin + self.portfolio_margin_allocation
            if new_margin > self.cash:
                raise ValueError(f'Insufficient margin available to open this position.')

        [option.bind(open_transaction_completed=self.on_option_open_transaction_completed,
                     close_transaction_completed=self.on_option_close_transaction_completed,
                     option_expired=self.on_option_expired,
                     fees_incurred=self.on_fees_incurred) for option in option_position.options]
        option_position.open_trade(quantity=quantity, **kwargs)
        self.positions[option_position.position_id] = option_position
        self.emit("new_position_opened", option_position.options)
        # for o in list(option_position.options):
        #     last_data_date = o.update_cache.iloc[-1].name.to_pydatetime()
        #     if last_data_date < self.end_date:
        #         last_data_date = last_data_date.date()
        #         if last_data_date < o.expiration:
        #             self.close_position(option_position)
        #             self.cash += option_position.get_fees()
        #             raise Exception(f'Missing data for option updates {o.symbol} {o.option_id}')

        # create hook for option update when next quote method is called
        self.bind(next=option_position.next_quote_date)
        [self.bind(next=o.next_update) for o in option_position.options]

    def close_position(self, option_position: OptionCombination, quantity: int = None, **kwargs: dict):
        quantity = quantity if quantity is not None else option_position.quantity
        option_position.close_trade(quantity=quantity, **kwargs)
        closing_value = sum(o.trade_close_records[-1].premium for o in option_position.options)
        raw_pnl = option_position.trade_value - closing_value
        raw_pnl = raw_pnl * -1 if option_position.option_position_type == OptionPositionType.SHORT else raw_pnl

        # Adjust portfolio cash if the closing value is greater than the max profit for this position
        if option_position.max_profit:
            if raw_pnl > option_position.max_profit:
                self.cash -= (raw_pnl - option_position.max_profit)
                print(f'corrected pnl > max profit: {(raw_pnl - option_position.max_profit)}')

        # Adjust portfolio cash if the closing value is less than the max loss for this position
        if option_position.max_loss:
            max_loss = option_position.max_loss * -1
            if raw_pnl < max_loss:
                self.cash += (raw_pnl - max_loss)
                print(f'corrected pnl < max loss: {(max_loss - raw_pnl)}')

        self.closed_positions[option_position.position_id] = option_position
        del self.positions[option_position.position_id]
        self.emit("position_closed", option_position)
        [option.unbind(self) for option in option_position.options]

    def next(self, quote_datetime: datetime.datetime, *args):
        self.current_datetime = quote_datetime
        self.emit('next', quote_datetime)
        values = [quote_datetime, self.portfolio_value] + list(args)
        self.close_values.append(values)

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
        open_premium = trade_open_info.premium
        self.cash = self.cash - open_premium
        #print(f'opened option. ${open_premium:,.2f} subtracted from cash')
        #print(f"portfolio: option position was opened {trade_open_info.option_id}")

    def on_option_close_transaction_completed(self, trade_close_info: TradeCloseInfo):
        close_premium = trade_close_info.premium
        self.cash = self.cash + close_premium
        #print(f'closed option. ${close_premium:,.2f} added to cash')
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
        self.cash = self.cash - fees
        #print(f'fees charged. ${fees:,.2f} subtracted from cash')
        #print("portfolio: fees incurred")

