from __future__ import annotations

import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from abc import ABC, abstractmethod
from options_framework.option import Option
from options_framework.option_types import SelectFilter
from options_framework.config import settings
import options_framework.config as config
from pydispatch import Dispatcher
import pandas as pd

class DataLoader(ABC, Dispatcher):
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

        super().__init__()


    @abstractmethod
    def load_option_chain_data(self, symbol: str, start: datetime.datetime, end: datetime.datetime):
        pass

    def option_chain_load_data_complete(self, symbol: str, quote_datetime: datetime.datetime | datetime.date,
                               options_data : pd.DataFrame):
        prefix = f'{symbol}-'
        with NamedTemporaryFile(delete=False, dir='./temp_data', prefix=prefix, suffix='.pkl') as pkl:
            pickle_file = Path(pkl.name)
        options_data.to_pickle(pickle_file)
        self.emit('option_chain_loaded', symbol=symbol, quote_datetime=quote_datetime, pickle=pickle_file)


    def on_options_opened(self, options: list[Option]) -> None:
        symbol = options[0].symbol
        pickle_file_path = Path("temp_data")
        pkl_file = next(pickle_file_path.glob(f'{symbol}*.pkl'))
        df = pd.read_pickle(pkl_file)
        today = options[0].quote_datetime
        df = df[df['quote_datetime'] > today]
        for option in options:
            option_data = df[df['option_id'] == option.option_id]
            option.update_cache = option_data
