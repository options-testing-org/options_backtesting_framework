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

    def __init__(self, start: datetime.datetime | datetime.date, end: datetime.datetime | datetime.date,
                 select_filter: SelectFilter,
                 fields_list: list[str] = None, *args, **kwargs):
        settings.load_file(settings.DATA_FORMAT_SETTINGS)
        self.start_datetime = start
        self.end_datetime = end
        self.select_filter = select_filter
        self.fields_list = settings.SELECT_FIELDS if not fields_list else fields_list
        self.data_cache: DataFrame | None = None
        self.last_loaded_date: datetime.datetime | None = None

    def next_option_chain(self, quote_datetime: datetime.datetime | datetime.date):
        if isinstance(quote_datetime, datetime.date):
            # the date must be in datetime format to compare
            quote_datetime = datetime.datetime(year=quote_datetime.year, month=quote_datetime.month,
                                               day=quote_datetime.day)

        if quote_datetime > self.last_loaded_date:
            self.load_cache(quote_datetime)
        self.get_next_option_chain(quote_datetime)

    @abstractmethod
    def load_cache(self, quote_datetime: datetime.datetime):
        pass

    def on_option_chain_loaded_loaded(self, quote_datetime: datetime.datetime | datetime.date,
                                      option_chain: list[Option]):
        self.emit('option_chain_loaded', quote_datetime=quote_datetime, option_chain=option_chain)

    @abstractmethod
    def get_next_option_chain(self, quote_datetime):
        pass

