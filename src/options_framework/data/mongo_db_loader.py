import dataclasses
import datetime
from abc import ABC

import pandas as pd

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter

class MongoDbDataLoader(DataLoader):

    def on_options_opened(self, portfolio, options: list[Option]) -> None:
        pass

    def get_expirations(self):
        pass

    def get_option_chain(self, quote_datetime: datetime.datetime):
        pass

    def load_cache(self, quote_datetime: datetime.datetime):
        pass

    def __init__(self, *, start: datetime.datetime, end: datetime.datetime, select_filter: SelectFilter,
                 extended_option_attributes: list[str] = None):
        pass