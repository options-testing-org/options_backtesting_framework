import os
import datetime
from abc import ABC, abstractmethod
from typing import List
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter
from options_framework.config import settings
from pathlib import Path
from pydispatch import Dispatcher
from pandas import DataFrame

class DataLoader(ABC, Dispatcher):
    _events_ = ['option_chain_loaded']

    def __init__(self, *, start: datetime.datetime | datetime.date, end: datetime.datetime | datetime.date,
                 select_filter: SelectFilter, extended_option_attributes: list[str] = None):

        settings.load_file(settings.DATA_FORMAT_SETTINGS)
        self.start_datetime = start
        self.end_datetime = end
        self.select_filter = select_filter
        self.extended_option_attributes = extended_option_attributes if extended_option_attributes else []
        self.data_cache: DataFrame | None = None
        self.last_loaded_date: datetime.datetime | None = None
        super().__init__()

    def next_option_chain(self, quote_datetime: datetime.datetime | datetime.date):
        if self.last_loaded_date < quote_datetime:
            self.load_cache(quote_datetime)
        self.get_option_chain(quote_datetime)

    @abstractmethod
    def load_cache(self, quote_datetime: datetime.datetime):
        pass

    def on_option_chain_loaded(self, quote_datetime: datetime.datetime | datetime.date,
                               option_chain: list[Option]):
        self.emit('option_chain_loaded', quote_datetime=quote_datetime, option_chain=option_chain)

    @abstractmethod
    def get_option_chain(self, quote_datetime: datetime.datetime):
        pass

    @abstractmethod
    def get_expirations(self):
        pass

    @abstractmethod
    def on_options_opened(self, portfolio, options: list[Option]) -> None:
        pass
