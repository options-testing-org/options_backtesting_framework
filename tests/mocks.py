import datetime
from dataclasses import dataclass, field

from pydispatch import Dispatcher
from test_data.spx_test_options import *


class MockPortfolio(Dispatcher):
    _events_ = ['new_position_opened', 'next']

    def open_position(self, position):
        position.open_trade(quantity=1)
        for o in position.options:
            self.bind(next=o.next_update)
        self.emit('new_position_opened', self, position.options)

    def next(self, quote_datetime: datetime.datetime):
        self.emit('next', quote_datetime)


#@dataclass
class MockSPXOptionChain:
    # quote_datetime: datetime.datetime = field(default=datetime.datetime(2016, 3, 1, 9, 31))
    # option_chain: list = field(init=False, default=t1_options)
    # expirations: list = field(init=False, default=expirations)
    # expiration_strikes: dict = field(init=False, default=expiration_strikes)
    quote_datetime: datetime.datetime = datetime.datetime(2016, 3, 1, 9, 31)
    option_chain: list = t1_options
    expirations: list = expirations
    expiration_strikes: dict = expiration_strikes