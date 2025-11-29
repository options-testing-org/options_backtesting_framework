import datetime
from dataclasses import dataclass, field
from typing import Optional

from pydispatch import Dispatcher

from options_framework.option import Option


# Emits the "next" event with a date, and the "new_position_opened" with the options
class MockEventDispatcher(Dispatcher):
    _events_ = ['next', 'new_position_opened']

    def do_next(self, quote_datetime: datetime.datetime):
        self.emit('next', quote_datetime)

    def open_option_position(self, options: list[Option]):
        self.emit('new_position_opened', options)

@dataclass
class MockOptionChain:
    symbol: str
    quote_datetime: Optional[datetime.datetime] = None
    pickle_file: Optional[str] = None
    expirations: list = field(init=False, default_factory=list, repr=False)
    option_chain: list = field(init=False, default_factory=lambda: [], repr=False)
    expiration_strikes: dict = field(init=False, default_factory=lambda: {}, repr=False)


class MockPortfolio(Dispatcher):
    _events_ = ['new_position_opened', 'next']

    def open_position(self, position):
        position.open_trade(quantity=1)
        for o in position.options:
            self.bind(next=o.next)
        self.emit('new_position_opened', self, position.options)

    def next(self, quote_datetime: datetime.datetime, *args):
        self.emit('next', quote_datetime)

