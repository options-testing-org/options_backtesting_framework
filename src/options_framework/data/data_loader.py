import os
import datetime
from abc import ABC, abstractmethod
from typing import List
from options_framework.option import Option
from options_framework.option_chain import OptionChain
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

        super().__init__()


    @abstractmethod
    def load_option_chain_data(self, symbol: str, start: datetime.datetime) -> DataFrame:
        pass

    def on_option_chain_loaded(self, symbol: str, quote_datetime: datetime.datetime | datetime.date,
                               options_data : DataFrame):
        self.emit('option_chain_loaded', symbol=symbol, quote_datetime=quote_datetime, options_data=options_data)

    @abstractmethod
    def get_expirations(self, symbol: str) -> list:
        pass

    @abstractmethod
    def on_options_opened(self, portfolio, options: list[Option]) -> None:
        pass
