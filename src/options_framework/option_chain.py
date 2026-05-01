import datetime

import pandas as pd
from dataclasses import dataclass, field

from pathlib import Path

from options_framework.utils.helpers import get_market_dates
from options_framework.utils.options_db import IntradayOptionsDB, OptionsDB
from typing import Optional
from options_framework.config import settings

@dataclass
class OptionChain():

    symbol: str
    quote_datetime: datetime.datetime
    end_datetime: datetime.datetime
    datetimes: list = field(init=False, default_factory=lambda: [], repr=False)
    expirations: list = field(init=False, default_factory=lambda: [], repr=False)
    options: list = field(init=False, default_factory=lambda: [], repr=False)
    expiration_strikes: dict = field(init=False, default_factory=lambda: {}, repr=False)

    def __post_init__(self):
        data_frequency = settings['data_frequency']
        if data_frequency == 'daily':
            self.db = OptionsDB.from_symbol(self.symbol)
        else:
            self.db = IntradayOptionsDB.from_symbol(self.symbol)
        self.datetimes = self.get_datetimes_in_date_range()

    def on_next(self, quote_datetime: datetime.datetime):
        # find quote datetime in datetimes list
        self.quote_datetime = quote_datetime
        #print(f'next {self.symbol} {quote_datetime}')

        if quote_datetime not in self.datetimes:
            self.options = []
            self.expirations = []
            self.expiration_strikes = {}
            return

        options = self.db.get_chain_at(self.quote_datetime.isoformat())
        if not options:
            self.options = []
            self.expirations = []
            self.expiration_strikes = {}
            return
        
        self.options = options
        self.expirations = self.db.get_expirations_at(self.quote_datetime.isoformat())
        self.expiration_strikes = self.db.get_expiration_strikes_at(self.quote_datetime.isoformat())

    def get_datetimes_in_date_range(self):
        datetimes = get_market_dates(self.quote_datetime.date(), self.end_datetime.date())
        datetimes = [datetime.datetime.combine(x, datetime.time(0,0)) for x in datetimes]
        data_frequency = settings['data_frequency']
        if data_frequency == 'daily':
            return datetimes

        elif data_frequency == 'intraday':
            minute_granularity = int(settings['minute_granularity'])
            start_time_setting =  settings['start_time']
            start_time = datetime.time(int(start_time_setting[:2]), int(start_time_setting[-2:]))
            end_time_setting = settings['end_time']
            end_time = datetime.time(int(end_time_setting[:2]), int(end_time_setting[-2:]))


            intra_datetimes = []

            for dt in datetimes:
                tm = start_time
                while tm <= end_time:
                    new_datetime = datetime.datetime.combine(dt, tm)
                    intra_datetimes.append(new_datetime)
                    new_datetime += datetime.timedelta(minutes=minute_granularity)
                    tm = new_datetime.time()

            return intra_datetimes

        return datetimes
