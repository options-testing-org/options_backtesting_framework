import datetime
from dataclasses import dataclass, field

from options_framework.data.data_loader import DataLoader
from options_framework.option_chain import OptionChain
from options_framework.config import settings

@dataclass
class OptionTestManager():
    data_loader: DataLoader
    option_chain: OptionChain
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    symbols: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.data_loader.bind(option_chain_loaded=self.option_chain.on_option_chain_loaded)
