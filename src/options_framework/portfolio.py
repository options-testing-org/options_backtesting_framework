import datetime
from dataclasses import dataclass, field

from pydispatch import Dispatcher

from options_framework.option import TradeOpenInfo, TradeCloseInfo
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionStatus, OptionPositionType
from options_framework.spreads.spread_base import SpreadBase
from options_framework.utils.helpers import decimalize_2


@dataclass(repr=False)
class OptionPortfolio(Dispatcher):

    _events_ = ['position_closed', 'next', 'next_options', 'position_expired']

    cash: float | int
    start_date: datetime.datetime
    end_date: datetime.datetime
    current_datetime: datetime.datetime = field(init=False, default=None)
    positions: list = field(init=False, default_factory=lambda: [])
    closed_positions: list = field(init=False, default_factory=lambda: [])
    portfolio_risk: float = field(init=False, default=0.0)
    close_values: list = field(init=False, default_factory=lambda: [])
    option_chains: dict = field(default_factory=lambda: {})
    uninitialize_closed_positions: bool = field(init=False, default=False)

    def __post_init__(self):
        pass

    def __repr__(self) -> str:
        return f'<OptionPortfolio cash=${self.cash:,.2f} portfolio_value=${self.current_value:,.2f}>'

    def open_position(self, option_spread: SpreadBase, quantity: int, *args, **kwargs: dict):
        try:
            if option_spread.symbol not in self.option_chains.keys():
                self.initialize_ticker(option_spread.symbol, self.current_datetime)
            [option.bind(open_transaction_completed=self.on_option_open_transaction_completed,
                         close_transaction_completed=self.on_option_close_transaction_completed,
                         option_expired=self.on_option_expired,
                         fees_incurred=self.on_fees_incurred) for option in option_spread.options]
            option_spread.open_trade(quantity=quantity, *args, **kwargs)
            if option_spread.position_type == OptionPositionType.SHORT:
                # check to see if we have enough margin to open this position
                new_margin = option_spread.required_margin + self.portfolio_margin_allocation
                if new_margin > self.cash:
                    raise ValueError(f'Insufficient margin available to open this position.')
        except ValueError as e:
            raise ValueError(str(e)) from e

        self.positions.append(option_spread)


    def close_position(self, position_id: int, quantity: int = None, **kwargs: dict):

        try:
            to_close = next(x for x in self.positions if x.position_id == position_id)
        except StopIteration:
            raise ValueError(f'Position {position_id} not in open positions list.')

        try:
            to_close.close_trade(quantity=quantity, **kwargs)
            closing_value = sum(o.trade_close_records[-1].premium for o in to_close.options)
            raw_pnl = to_close.trade_value - closing_value
            raw_pnl = raw_pnl * -1 if to_close.position_type == OptionPositionType.SHORT else raw_pnl

            # Adjust portfolio cash if the closing value is greater than the max profit for this position
            if to_close.max_profit:
                if raw_pnl > to_close.max_profit:
                    self.cash -= (raw_pnl - to_close.max_profit)
                    print(f'corrected pnl > max profit: {(raw_pnl - to_close.max_profit)}')

            # Adjust portfolio cash if the closing value is less than the max loss for this position
            if to_close.max_loss:
                max_loss = to_close.max_loss * -1
                if raw_pnl < max_loss:
                    self.cash += (raw_pnl - max_loss)
                    print(f'corrected pnl < max loss: {(max_loss - raw_pnl)}')

            self.closed_positions.append(to_close)
            self.positions.remove(to_close)
            self.emit("position_closed", to_close)

            # if self._uninitialize_closed_positions:
            #     symbol = to_close.symbol
            #     open_symbols = [o.symbol for pos in self.positions for o in pos.options]
            #     if symbol not in open_symbols:
            #         self.uninitialize_ticker(symbol)

        except Exception as e:
            raise Exception(str(e)) from e

    def next(self, quote_datetime: datetime.datetime, symbols: list[str] = None, *args):
        self.current_datetime = quote_datetime
        symbols = [] if symbols is None else symbols
        try:
            del_symbols = [s for s in list(self.option_chains.keys()) if s not in symbols]
            self._remove_symbols(del_symbols)
            for symbol in symbols:
                self._initialize_ticker(symbol=symbol, quote_datetime=quote_datetime)

            self.emit('next', quote_datetime)
            options = [o for pos in self.positions for o in pos.options]
            self.emit('next_options', options)
            values = [quote_datetime, self.current_value] + list(args)
            self.close_values.append(values)
        except Exception as e:
            raise Exception(str(e)) from e

    def get_open_position_by_id(self, position_id: int) -> SpreadBase:
        pass

    def get_closed_position_by_id(self, position_id: int) -> SpreadBase:
        pass

    @property
    def current_value(self):
        current_value = sum(option.current_value for option in [option for position in self.positions
                                                                for option in position.options])
        portfolio_value = decimalize_2(current_value) + decimalize_2(self.cash)
        return float(portfolio_value)

    @property
    def portfolio_margin_allocation(self):
        margin = sum(position.required_margin for position in self.positions)
        return margin

    def on_option_open_transaction_completed(self, trade_open_info: TradeOpenInfo):
        open_premium = trade_open_info.premium
        self.cash = self.cash - open_premium
        print(f'opened option. ${open_premium:,.2f} subtracted from cash')
        print(f"portfolio: option position was opened {trade_open_info.option_id}")

    def on_option_close_transaction_completed(self, trade_close_info: TradeCloseInfo):
        close_premium = trade_close_info.premium
        self.cash = self.cash + close_premium
        print(f'closed option. ${close_premium:,.2f} added to cash')
        print(f"portfolio: option position was closed {trade_close_info.option_id}")

    def on_option_expired(self, instance_id: int):
        print(f"portfolio: option expired {instance_id}")
        try:
            expired_position = next(pos for pos in self.positions for o in pos.options if o.instance_id == instance_id)
        except StopIteration:
            raise ValueError(f'Cannot find expired option {instance_id} in open positions list.')

        if all([OptionStatus.EXPIRED in option.status for option in expired_position.options]):
                self.close_position(expired_position, expired_position.quantity)
                self.emit('position_expired', expired_position)

    def on_fees_incurred(self, fees):
        self.cash = self.cash - fees
        #print(f'fees charged. ${fees:,.2f} subtracted from cash')
        #print("portfolio: fees incurred")

    # Bind events to option chain so it stays in sync with portfolio
    def _initialize_ticker(self, symbol: str, quote_datetime: datetime.datetime) :
        if symbol in self.option_chains.keys():
            return
        option_chain = OptionChain(symbol=symbol, quote_datetime=quote_datetime, end_datetime=self.end_date)
        self.bind(next=option_chain.on_next)
        self.bind(next_options=option_chain.on_next_options)
        self.option_chains[symbol] = option_chain

    def _remove_symbols(self, symbols: list[str]) -> None:
        for symbol in symbols:
            self._uninitialize_ticker(symbol)

    # stop emitting events to option chain that does not have any options currently
    def _uninitialize_ticker(self, symbol: str):
        if symbol in self.option_chains.keys():
            option_chain = self.option_chains[symbol]
            if any(o.symbol == symbol for pos in self.positions for o in pos.options):
                return

            self.unbind(option_chain.on_next)
            self.unbind(option_chain.on_next_options)
            del self.option_chains[symbol]
