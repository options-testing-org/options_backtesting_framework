import datetime

from dataclasses import dataclass, field
from .option_types import OptionType, TransactionType
from .option import Option
from .spreads.single import Single
from .utils.helpers import distinct
from options_framework.config import settings


@dataclass
class OptionChain:
    quote_datetime: datetime.datetime = field(init=False)
    option_chain: list = field(init=False, default_factory=list, repr=False)
    expirations: list = field(init=False, default_factory=list, repr=False)
    expiration_strikes: list = field(init=False, default_factory=list, repr=False)

    def on_option_chain_loaded(self, quote_datetime: datetime.datetime, option_chain: list[Option]):
        self.quote_datetime = quote_datetime
        self.option_chain = option_chain
        self.expirations = list(distinct([option.expiration for option in option_chain]))
        self.expiration_strikes = [(e, list(distinct([strike for strike in [option.strike
                                                                            for option in option_chain if
                                                                            option.expiration == e]]))) for e in
                                   self.expirations]

    def get_single_option(self, expiration: datetime.date, option_type: OptionType, strike: float | int) -> Single:
        candidates = [o for o in self.option_chain if o.expiration == expiration
                      and o.option_type == option_type and o.strike == strike]
        if not candidates:
            raise ValueError("No option was found")
        if len(candidates) > 1:
            raise ValueError("Multiple options match the parameters provided.")
        single = Single(candidates[0])
        return single
