import datetime
import os
import dill as pickle
import glob

import pandas as pd
from pandas import DataFrame, Series
from dataclasses import dataclass, field
from dateutil import relativedelta

from pydispatch import Dispatcher
from pathlib import Path

from options_framework.option import Option
from options_framework.utils.helpers import distinct
from typing import Optional
from options_framework.config import settings
from options_framework.utils.helpers import decimalize_0, decimalize_2, decimalize_4

@dataclass
class OptionChain():

    symbol: str
    quote_datetime: datetime.datetime
    end_datetime: datetime.datetime
    timeslots_folder: Path = field(init=False, default=None, repr=False)
    datetimes: list = field(init=False, default_factory=lambda: [], repr=False)
    expirations: list = field(init=False, default_factory=lambda: [], repr=False)
    options: list = field(init=False, default_factory=lambda: [], repr=False)
    expiration_strikes: dict = field(init=False, default_factory=lambda: {}, repr=False)

    def __post_init__(self):
        self.timeslots_folder = options_folder = Path(settings['options_directory'], settings['data_frequency'], self.symbol, 'timeslots')
        self.datetimes = datetimes = self.get_datetimes_in_date_range()

    def on_next(self, quote_datetime: datetime.datetime):
        # find quote datetime in datetimes list
        self.quote_datetime = quote_datetime
        try:
            dt = next(d for d in self.datetimes if d == quote_datetime)
        except StopIteration:
            # There are no matching timeslots for the quote given
            self.options = []
            self.expirations = []
            self.expiration_strikes = {}
            return

        options = self.load_timeslot(quote_datetime=quote_datetime)
        if options is None:
            return # no options for this time slot

        idx_quote = self.datetimes.index(quote_datetime)
        if len(self.datetimes) > 1:
            self.datetimes = self.datetimes[idx_quote + 1:]
        self.options = options

        expirations = [x['expiration'] for x in options]
        expirations = list(set(expirations))
        expirations.sort()
        self.expirations = expirations
        expiration_strikes = [(x['expiration'], x['strike']) for x in options]
        expiration_strikes = list(set(expiration_strikes))
        expiration_strikes = sorted(expiration_strikes,key=lambda x: (x[0], x[1]))
        expiration_strikes = {exp: [s for (e, s) in expiration_strikes if e == exp] for exp in expirations}
        self.expiration_strikes = expiration_strikes


    def load_timeslot(self, quote_datetime: datetime.datetime) -> list[Option]:
        ym_str = datetime.datetime.strftime(quote_datetime, '%Y_%m')
        folder = self.timeslots_folder.joinpath(ym_str)
        dt_str = datetime.datetime.strftime(quote_datetime, '%Y_%m_%d_%H_%M')
        find_timeslot = folder.glob(f'{dt_str}.pkl')
        try:
            ts_file = next(find_timeslot)
        except StopIteration:
            raise ValueError(f'Cannot find option chain for {self.symbol} on {quote_datetime}.')

        with open(ts_file, 'rb') as f:
            options_data = pickle.load(f)
        return options_data


    def get_folder_as_date(self, folder):
        return folder, datetime.datetime.strptime(folder.name, '%Y_%m').date()


    def get_datetimes_in_date_range(self):
        folders_list = self.timeslots_folder.glob('*')

        start_folder = datetime.date(self.quote_datetime.year, self.quote_datetime.month, 1)
        end_folder = datetime.date(self.end_datetime.year, self.end_datetime.month, 1)
        end = self.end_datetime + datetime.timedelta(days=1) # Need to add a day so we can capture all the times from that day.

        datetimes = []
        while True:
            try:
                fol, folder_dt = self.get_folder_as_date(next(folders_list))

                if folder_dt >= start_folder:
                    if folder_dt <= end_folder:
                        fol_dts = [datetime.datetime.strptime(f.stem, '%Y_%m_%d_%H_%M') for f in fol.iterdir()]
                        datetimes.extend(fol_dts)
                    else:
                        break
            except StopIteration:
                break

        datetimes.sort()
        datetimes = [x for x in datetimes if x >= self.quote_datetime and x <= self.end_datetime]
        return datetimes


    def on_next_options(self, options: list[Option]) -> list[dict] | None:
        for option in options:
            try:
                option_quote = next(q for q in self.options if q['option_id'] == option.option_id)
                option.next(option_quote)
            except StopIteration:
                continue




