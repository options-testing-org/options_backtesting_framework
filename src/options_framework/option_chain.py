import datetime

from pandas import DataFrame
from dataclasses import dataclass, field
from options_framework.option import Option
from options_framework.utils.helpers import distinct

@dataclass
class OptionChain:
    symbol: str
    quote_datetime: datetime.datetime = field(init=False)
    option_chain: list = field(init=False, default_factory=list, repr=False)
    expirations: list = field(init=False, default_factory=list, repr=False)
    expiration_strikes: dict = field(init=False, default_factory=lambda: {}, repr=False)
    data_cache: DataFrame | None = None
    last_loaded_date: datetime.datetime | None = None

    def get_option_chain(self, ):

    def on_option_chain_loaded(self, quote_datetime: datetime.datetime, options: list[Option]):
        self.quote_datetime = quote_datetime
        self.option_chain = option_chain
        self.expirations = list(distinct([option.expiration for option in option_chain]))
        self.expiration_strikes = {e: list(distinct([strike for strike in [option.strike
                                                                            for option in option_chain if
                                                                            option.expiration == e]])) for e in
                                                                            self.expirations}
        #print(f'option chain loaded {quote_datetime}')

    def get_option_by_id(self, option_id: str) -> Option:
        options = [option for option in self.option_chain if option.option_id == option_id]
        option = options[0] if options else None
        return option
