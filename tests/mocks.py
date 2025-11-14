import datetime
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from pandas import DataFrame
import test_data.test_option_daily as test_options_daily

from options_framework.config import settings
from options_framework.option import Option
from pydispatch import Dispatcher

from options_framework.option_types import SelectFilter


class MockIntegrationDataLoader(Dispatcher):
    _events_ = ['option_chain_loaded']
    def __init__(self, *, start: datetime.datetime | datetime.date, end: datetime.datetime | datetime.date,
                 select_filter: SelectFilter, extended_option_attributes: list[str] = None):
        self.start_datetime = start
        self.end_datetime = end
        self.select_filter = select_filter
        self.extended_option_attributes = extended_option_attributes if extended_option_attributes else []
        self.option_required_fields = ['option_id', 'symbol', 'strike', 'expiration', 'option_type', 'quote_datetime',
                              'spot_price', 'bid', 'ask', 'price']
        self.optional_fields = ['delta', 'gamma', 'theta', 'vega', 'rho', 'open_interest', 'volume',
                                'implied_volatility']

    def load_option_chain_data(self, symbol: str, start: datetime.datetime, end: datetime.datetime):
        self.option_chain_load_data_complete(symbol, start, None)
        pass

    def option_chain_load_data_complete(self, symbol: str, quote_datetime: datetime.datetime | datetime.date,
                               options_data : DataFrame| None):
        test_data_dir = settings['test_data_dir']
        pkl_file = Path(test_data_dir, 'data_files', f'{symbol}.pkl')
        df = pd.read_pickle(pkl_file)
        dates = [x.to_pydatetime() for x in df['quote_datetime'].unique()]
        self.emit('option_chain_loaded', quote_datetime=quote_datetime, pickle=pkl_file, datetimes=dates)

    def on_options_opened(self, options: list[Option]) -> None:
        symbol = options[0].symbol
        test_data_dir = settings['test_data_dir']
        pkl_file = Path(test_data_dir, 'data_files', f'{symbol}.pkl')
        df = pd.read_pickle(pkl_file)
        today = options[0].quote_datetime
        df = df[df['quote_datetime'] > today]
        for option in options:
            option_data = df[df['option_id'] == option.option_id]
            option.update_cache = option_data

class MockDataLoader:
    def __init__(self, *, start: datetime.datetime | datetime.date, end: datetime.datetime | datetime.date,
                 select_filter: SelectFilter, extended_option_attributes: list[str] = None):
        self.start_datetime = start
        self.end_datetime = end
        self.select_filter = select_filter

    def on_options_opened(self, options: list[Option]) -> None:
        pass


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
            self.bind(next=o.next_update)
        self.emit('new_position_opened', self, position.options)

    def next(self, quote_datetime: datetime.datetime, *args):
        self.emit('next', quote_datetime)


# class MockSPXOptionChain:
#     quote_datetime: datetime.datetime = datetime.datetime(2016, 3, 1, 9, 31)
#     option_chain: list = t1_options
#     expirations: list = expirations
#     expiration_strikes: dict = expiration_strikes


# class MockSPXDataLoader(DataLoader):
#
#     def load_option_chain_data(self, symbol: str, start: datetime.datetime):
#         if start == datetime.datetime(2016, 3, 1, 9, 31):
#             return t1_options
#         elif start == datetime.datetime(2016, 3, 1, 9, 32):
#             return t2_options
#         else:
#             return None
#
#     def get_expirations(self, symbol: str) -> list:
#         return expirations
#
#     def on_options_opened(self, portfolio, options: list[Option]) -> None:
#         for option in options:
#             data_file_name = Path(settings['test_data_dir'], f'option_{option.option_id}.csv')
#             cache = pd.read_csv(data_file_name.absolute(), parse_dates=True, index_col='quote_datetime')
#             option.update_cache = cache
