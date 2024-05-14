import datetime

from pydispatch import Dispatcher


class MockPortfolio(Dispatcher):
    _events_ = ['new_position_opened', 'next']

    def open_position(self, position):
        position.open_trade(quantity=1)
        for o in position.options:
            self.bind(next=o.next_update)
        self.emit('new_position_opened', self, position.options)

    def next(self, quote_datetime: datetime.datetime):
        self.emit('next', quote_datetime)