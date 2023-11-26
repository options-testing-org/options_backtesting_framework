from abc import ABC, abstractmethod
from typing import List
from options_framework.option import Option
from options_framework.option_types import OptionType
from options_framework.config import settings
from pathlib import Path


class DataLoader(ABC):

    def __init__(self, settings_file: str, *args, **kwargs):
        path_to_settings = Path(settings.data_file_settings_folder, settings_file)
        settings.load_file(path_to_settings)

    @abstractmethod
    def load_data(self, symbol: str, option_type_filter: OptionType = None,
                  range_filters: dict = None, *args, **kwargs) -> List[Option]:
        return NotImplemented


class SQLServerDataLoader(DataLoader):

    def __init__(self, settings_file: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_data(self, settings_file: str, option_type_filter: OptionType = None,
                  range_filters: dict = None, *args, **kwargs) -> List[Option]:
        pass
