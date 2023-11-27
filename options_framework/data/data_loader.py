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

    def __init__(self, settings_file: str, *args, **kwargs):
        path_to_settings = Path(settings.data_file_settings_folder, settings_file)
        settings.load_file(path_to_settings)

    @abstractmethod
    def load_data(self, quote_datetime: datetime.datetime, symbol: str, option_type_filter: OptionType = None,
                  range_filters: dict = None, *args, **kwargs) -> List[Option]:
        return NotImplemented

    def on_data_loaded(self, quote_datetime: datetime.datetime, option_chain: list[Option]):
        self.emit('option_chain_loaded', quote_datetime=quote_datetime, option_chain=option_chain)

class SQLServerDataLoader(DataLoader):

    def __init__(self, settings_file: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_data(self, quote_datetime: datetime.datetime, option_type_filter: OptionType = None,
                  range_filters: dict = None, *args, **kwargs) -> List[Option]:
        pass
