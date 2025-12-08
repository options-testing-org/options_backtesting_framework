import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydispatch import Dispatcher

from options_framework.option import Option


# Emits the "next" event with a date, and the "new_position_opened" with the options
class MockEventDispatcher(Dispatcher):
    _events_ = ['next', 'next_options', 'new_position_opened']

    def do_next(self, quote_datetime: datetime.datetime):
        self.emit('next', quote_datetime)

    def do_next_options(self, options: list[Option]):
        self.emit('next_options', options)

    def open_option_position(self, options: list[Option]):
        self.emit('new_position_opened', options)

@dataclass
class MockOptionChain:
    symbol: str
    quote_datetime: datetime.datetime
    end_datetime: Optional[datetime.datetime] = field(default=None)
    timeslots_folder: Path = field(init=False, default=None, repr=False)
    datetimes: list = field(init=False, default_factory=lambda: [], repr=False)
    expirations: list = field(init=False, default_factory=lambda: [], repr=False)
    options: list = field(init=False, default_factory=lambda: [], repr=False)
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

