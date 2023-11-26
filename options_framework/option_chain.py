import datetime

from dataclasses import dataclass, field
from .option_types import OptionType, TransactionType
from .option import Option
from .utils.helpers import distinct
from options_framework.config import settings
from options_framework.data.data_loader import DataLoader


@dataclass(slots=True, kw_only=True)
class OptionChain:

    quote_datetime: datetime.datetime
    data_loader: DataLoader
    option_chain: list = field(init=False, default_factory=list, repr=False)
    expirations: list = field(init=False, default_factory=list, repr=False)
    strikes: list = field(init=False, default_factory=list, repr=False)

