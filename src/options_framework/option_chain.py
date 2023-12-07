import datetime

from dataclasses import dataclass, field
from .option import Option
from .utils.helpers import distinct

@dataclass
class OptionChain:
    quote_datetime: datetime.datetime = field(init=False)
    option_chain: list = field(init=False, default_factory=list, repr=False)
    expirations: list = field(init=False, default_factory=list, repr=False)
    expiration_strikes: dict = field(init=False, default_factory=lambda: {}, repr=False)

    def on_option_chain_loaded(self, quote_datetime: datetime.datetime, option_chain: list[Option]):
        self.quote_datetime = quote_datetime
        self.option_chain = option_chain
        self.expirations = list(distinct([option.expiration for option in option_chain]))
        self.expiration_strikes = {e: list(distinct([strike for strike in [option.strike
                                                                            for option in option_chain if
                                                                            option.expiration == e]])) for e in
                                                                            self.expirations}
        print(f'option chain loaded {quote_datetime}')

    def get_option_by_id(self, option_id: str) -> Option:
        option = [option for option in self.option_chain if option.option_id == option_id]
        return option