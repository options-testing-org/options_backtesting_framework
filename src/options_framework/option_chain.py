import datetime
import os

import pandas as pd
from pandas import DataFrame, Series
from dataclasses import dataclass, field

from pydispatch import Dispatcher
from pathlib import Path

from options_framework.option import Option
from options_framework.option_types import OptionType
from options_framework.utils.helpers import distinct
from typing import Optional
from options_framework.config import settings
from options_framework.utils.helpers import decimalize_0, decimalize_2, decimalize_4

@dataclass
class OptionChain(Dispatcher):
    _events_ = ['load_next_data']

    symbol: str
    quote_datetime: datetime.datetime
    end_datetime: datetime.datetime
    pickle_file: Optional[str] = None
    cache: pd.DataFrame = field(init=False, default=None)
    datetimes: list = field(init=False, default_factory=lambda: [], repr=False)
    expirations: list = field(init=False, default_factory=list, repr=False)
    option_chain: list = field(init=False, default_factory=lambda: [], repr=False)
    expiration_strikes: dict = field(init=False, default_factory=lambda: {}, repr=False)

    def __post_init__(self):
        pass

    def on_option_chain_loaded(self, quote_datetime: datetime.datetime, pickle: str, datetimes: list[datetime.datetime]):
        self.pickle_file = pickle
        self.datetimes = datetimes
        self.on_next(quote_datetime) # call this the first time to load current day's options chain

    def on_next(self, quote_datetime: datetime.datetime):
        self.quote_datetime = quote_datetime
        if self.cache is None:
            df = pd.read_pickle(self.pickle_file)
            self.cache = df
        else:
            df = self.cache
        df = df[df['quote_datetime'] == quote_datetime]

        idx_quote = self.datetimes.index(quote_datetime)
        if len(self.datetimes) > 1:
            self.datetimes = self.datetimes[idx_quote+1:]

        options = []
        for _, row in df.iterrows():
            option = self._create_option(row)
            options.append(option)
        self.option_chain = options
        self.expirations = list(df['expiration'].unique())
        expiration_strikes = df[['expiration', 'strike']].drop_duplicates().to_numpy().tolist()
        self.expiration_strikes = {exp: [s for (e, s) in expiration_strikes if e == exp] for exp in self.expirations}
        if quote_datetime >= self.cache.iloc[-1]['quote_datetime']:
            if Path(self.pickle_file).exists():
                os.unlink(self.pickle_file) # remove current pickle file
            self.cache = None
            self.emit('load_next_data', symbol=self.symbol, start=quote_datetime, end=self.end_datetime)

    def _create_option(self, row: Series) -> Option:
        option_id = row['option_id']
        option = Option(
            option_id=option_id,
            symbol=row['symbol'],
            expiration=row['expiration'],
            strike=row['strike'],
            option_type=OptionType.CALL if row['option_type'] == settings['data_settings']['call_value'] else OptionType.PUT,
            quote_datetime=row['quote_datetime'],
            spot_price=row['spot_price'],
            bid=row['bid'],
            ask=row['ask'],
            price=row['price'],
            delta=row['delta'] if 'delta' in row.index else None,
            gamma=row['gamma'] if 'gamma' in row.index else None,
            theta=row['theta'] if 'theta' in row.index else None,
            vega=row['vega'] if 'vega' in row.index else None,
            rho=row['rho'] if 'rho' in row.index else None,
            open_interest=row['open_interest'] if 'open_interest' in row.index else None,
            implied_volatility=row['implied_volatility'] if 'implied_volatility' in row.index else None)
        return option
