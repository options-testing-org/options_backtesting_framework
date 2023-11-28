import os
import datetime
from abc import ABC, abstractmethod
from typing import List
from options_framework.option import Option
from options_framework.option_types import OptionType
from options_framework.config import settings
from pathlib import Path
from pydispatch import Dispatcher

class DataLoader(ABC, Dispatcher):
    _events_ = ['option_chain_loaded']
    _default_fields = ['symbol', 'expiration', 'strike', 'option_type', 'spot_price', 'bid', 'ask', 'price']

    def __init__(self, settings_file: str, fields: list = None, *args, **kwargs):
        path_to_settings = Path(os.getcwd(), settings.data_file_settings_folder, settings_file)
        settings.load_file(path_to_settings)
        self.select_fields = self._default_fields if fields is None else fields

    @abstractmethod
    def load_data(self, quote_datetime: datetime.datetime, symbol: str, option_type_filter: OptionType = None,
                  range_filters: dict = None, *args, **kwargs):
        return NotImplemented

    def on_data_loaded(self, quote_datetime: datetime.datetime, option_chain: list[Option]):
        self.emit('option_chain_loaded', quote_datetime=quote_datetime, option_chain=option_chain)

