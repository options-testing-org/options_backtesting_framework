import os
import datetime
from abc import ABC, abstractmethod
from typing import List
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter
from options_framework.config import settings
from pathlib import Path
from pydispatch import Dispatcher

class DataLoader(ABC, Dispatcher):
    _events_ = ['option_chain_loaded']


    def __init__(self, start: datetime.datetime, end: datetime.datetime, select_filter: SelectFilter,
                 fields_list: list[str] = None, *args, **kwargs):
        self.start_datetime = start
        self.end_datetime = end
        self.select_filter = select_filter
        self.fields_list = settings.SELECT_FIELDS if fields_list is None else fields_list

    @abstractmethod
    def load_option_chain(self, *, quote_datetime: datetime.datetime):
        return NotImplemented

    def on_option_chain_loaded_loaded(self, quote_datetime: datetime.datetime, option_chain: list[Option]):
        self.emit('option_chain_loaded', quote_datetime=quote_datetime, option_chain=option_chain)

