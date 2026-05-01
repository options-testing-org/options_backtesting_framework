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

    _events_ = ['position_closed', 'next', 'position_expired']

    cash: float | int
    start_date: datetime.datetime
    end_date: datetime.datetime
    current_datetime: datetime.datetime = field(init=False, default=None)
    positions: list = field(init=False, default_factory=lambda: [])
    closed_positions: list = field(init=False, default_factory=lambda: [])
    portfolio_risk: float = field(init=False, default=0.0)
    close_values: list = field(init=False, default_factory=lambda: [])
    option_chains: dict = field(init=False, default_factory=lambda: {})
    check_margin_on_open: bool = field(default=True)

    def __post_init__(self):
        pass


    def __repr__(self) -> str:
        return f'<OptionPortfolio cash=${self.cash:,.2f} portfolio_value=${self.current_value:,.2f}>'


    def open_position(self, option_spread: SpreadBase, quantity: int, margin_percent: float = None, *args, **kwargs: dict):
        try:
            if option_spread.symbol not in self.option_chains.keys():
                self._initialize_ticker(option_spread.symbol, self.current_datetime)
            for option in option_spread.options:
                option.bind(open_transaction_completed=self.on_option_open_transaction_completed,
                            close_transaction_completed=self.on_option_close_transaction_completed,
                            option_expired=self.on_option_expired,
                            fees_incurred=self.on_fees_incurred)
            for option in option_spread.options:
                self.bind(next=option.next)

            option_spread.open_trade(quantity=quantity,*args, **kwargs)
            if option_spread.position_type == OptionPositionType.SHORT and self.check_margin_on_open:

                # check to see if we have enough margin to open this position
                new_margin = option_spread.get_required_margin(quantity) + self.portfolio_margin_allocation
                allowed_margin = self.cash if margin_percent is None else self.current_value * margin_percent
                allowed_margin = allowed_margin if allowed_margin <= self.cash else self.cash
                if new_margin >= allowed_margin:
                    raise ValueError(f'Insufficient margin available to open this position.')
            self.positions.append(option_spread)
        except Exception as e:
            # back out of any transactions that may have completed, add back any premium that was subtracted from cash.
            for o in option_spread.options:
                if OptionStatus.TRADE_IS_OPEN in o.status:
                    premium = o.trade_open_info.premium
                    fees = o.trade_open_info.fees
                    self.cash += (premium + fees)
                    #print(f'Exception occurred: {premium + fees:.2f} subtracted from cash. {e}')
            raise


    def close_position(self, option_spread: SpreadBase, quantity: int = None, **kwargs: dict):

        try:
            instance_id = option_spread.instance_id
            to_close = next(x for x in self.positions if x.instance_id == instance_id)
        except StopIteration:
            raise ValueError(f'Position {instance_id} not in open positions list.')

        quantity = to_close.quantity if quantity is None else quantity

        try:
            to_close.close_trade(quote_datetime=self.current_datetime, quantity=quantity, **kwargs)
            self.closed_positions.append(to_close)
            self.positions.remove(to_close)
            self.emit("position_closed", to_close)
            for option in to_close.options:
                self.unbind(option.next)

        except Exception as e:
            raise Exception(str(e)) from e


    def next(self, quote_datetime: datetime.datetime, symbols: str | list[str] = None, *args, **kwargs):
        self.current_datetime = quote_datetime
        symbols = [] if symbols is None else symbols
        symbols = [symbols] if isinstance(symbols, str) else symbols
        open_position_symbols = [x.symbol for x in self.positions]
        symbols = list(dict.fromkeys(symbols + open_position_symbols))
        del_symbols = [s for s in list(self.option_chains.keys()) if s not in symbols]
        self._remove_symbols(del_symbols)
        for symbol in symbols:
            self._initialize_ticker(symbol=symbol, quote_datetime=quote_datetime)

        self.emit('next', quote_datetime)

        values = [quote_datetime, self.current_value] + list(args)
        self.close_values.append(values)


    @property
    def current_value(self):
        options_value = sum(option.current_value for option in [option for position in self.positions
                                                                for option in position.options])
        portfolio_value = decimalize_2(options_value) + decimalize_2(self.cash)
        return float(portfolio_value)


    @property
    def portfolio_margin_allocation(self):
        margin = sum(position.get_required_margin(position.quantity) for position in self.positions)
        return margin


    def on_option_open_transaction_completed(self, trade_open_info: TradeOpenInfo):
        open_premium = trade_open_info.premium
        self.cash = self.cash - open_premium
        #print(f'opened option. ${open_premium:,.2f} subtracted from cash')
        # print(f"portfolio: option position was opened {trade_open_info.option_id}")


    def on_option_close_transaction_completed(self, trade_close_info: TradeCloseInfo):
        close_premium = trade_close_info.premium
        self.cash = self.cash + close_premium
        #print(f'closed option. ${close_premium:,.2f} added to cash')
        # print(f"portfolio: option position was closed {trade_close_info.option_id}")


    def on_option_expired(self, instance_id: int):
        #print(f"portfolio: option expired {instance_id}")
        try:
            expired_position = next(pos for pos in self.positions for o in pos.options if o.instance_id == instance_id)
        except StopIteration:
            raise ValueError(f'Cannot find expired option {instance_id} in open positions list.')

        if all(OptionStatus.EXPIRED in option.status for option in expired_position.options):
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

        # self.bind(next_options=option_chain.on_next_options)
        self.option_chains[symbol] = option_chain


    def _remove_symbols(self, symbols: list[str]) -> None:
        for symbol in symbols:
            self._uninitialize_ticker(symbol)

    # stop emitting events to option chain that does not have any options currently
    def _uninitialize_ticker(self, symbol: str):
        if symbol in self.option_chains.keys():
            option_chain = self.option_chains[symbol]

            self.unbind(option_chain.on_next)
            del self.option_chains[symbol]
