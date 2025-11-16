import datetime
import os
import dill as pickle
import glob

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
class OptionChain():

    symbol: str
    quote_datetime: datetime.datetime
    end_datetime: datetime.datetime
    pickle_folder: str
    cache: pd.DataFrame = field(init=False, default=None)
    datetimes: list = field(init=False, default_factory=lambda: [], repr=False)
    expirations: list = field(init=False, default_factory=list, repr=False)
    option_chain: list = field(init=False, default_factory=lambda: [], repr=False)
    expiration_strikes: dict = field(init=False, default_factory=lambda: {}, repr=False)

    def __post_init__(self):
        self.datetimes = self.get_datetimes_from_pickle_files(self.quote_datetime, self.end_datetime)

    def on_next(self, quote_datetime: datetime.datetime):
        self.quote_datetime = quote_datetime
        options = self.load_pickled_options(quote_datetime=quote_datetime)
        if options is None:
            return # no options for this time slot

        idx_quote = self.datetimes.index(quote_datetime)
        if len(self.datetimes) > 1:
            self.datetimes = self.datetimes[idx_quote + 1:]
        self.option_chain = options

        expirations = [x.expiration for x in options]
        expirations = list(set(expirations))
        expirations.sort()
        self.expirations = expirations
        expiration_strikes = [(x.expiration, x.strike) for x in options]
        expiration_strikes = list(set(expiration_strikes))
        expiration_strikes = sorted(expiration_strikes,key=lambda x: (x[0], x[1]))
        expiration_strikes = {exp: [s for (e, s) in expiration_strikes if e == exp] for exp in expirations}
        self.expiration_strikes = expiration_strikes

    def on_options_opened(self, options: list[Option]) -> None:
        symbol = options[0].symbol

        pickle_file_path = Path(self.pickle_folder).parent / 'option_pkl'
        for o in options:
            pickle_file = pickle_file_path / f'{o.option_id}.pkl'
            with open(pickle_file, 'rb') as f:
                o_dict = pickle.load(f)
            updates = [x for x in o_dict if x['quote_datetime'] > o.quote_datetime and x['quote_datetime'] <= self.end_datetime]
            o.update_cache = updates

    def get_folders_in_date_range(self, folders, start_dt, end_dt):

        match_folders = []
        for x in folders:
            n = x.name
            date_from_folder = datetime.datetime.strptime(f'{n[-10:-6]}-{n[-5:-3]}-{n[-2:]}', '%Y-%m-%d').date()
            if date_from_folder >= start_dt and date_from_folder <= end_dt:
                match_folders.append(x)
            if date_from_folder > end_dt:
                break
        return match_folders

    def get_pickle_files_in_folder(self, folders):
        all_files = []
        for f in folders:
            files = f.glob('*.pkl')
            all_files.extend(list(files))
        return all_files

    def parse_pickle_file_name(self, pickle_files):
        datetimes = []
        for pf in pickle_files:
            f = pf.parent.stem # WindowsPath('D:/options_data/intraday_pkl/spx_2016_03_01')
            fn = pf.stem # '09_31'
            dt_str = f'{f}_{fn}'
            dt = datetime.datetime.strptime(dt_str, '%Y_%m_%d_%H_%M')
            datetimes.append(dt)

        return datetimes


    def get_datetimes_from_pickle_files(self, start: datetime.datetime, end: datetime.datetime) -> list[datetime.datetime]:
        folder = Path(self.pickle_folder)
        folders = self.get_folders_in_date_range(folder.iterdir(), start.date(), end.date())
        files = self.get_pickle_files_in_folder(folders)
        datetimes = self.parse_pickle_file_name(files)
        datetimes = [d for d in datetimes if d >= start and d <= end]
        return datetimes


    def load_pickled_options(self, quote_datetime: datetime.datetime) -> list[Option] | None:
        day_folder = Path(self.pickle_folder,
                          f'{quote_datetime.year}_{quote_datetime.month:0{2}}_{quote_datetime.day:0{2}}')
        pkl_file = day_folder / f'{quote_datetime.hour:0{2}}_{quote_datetime.minute:0{2}}.pkl'
        if not pkl_file.exists():
            return None
        with open(pkl_file, 'rb') as f:
            while True:
                try:
                    option_dicts = pickle.load(f)
                except EOFError:
                    break

        options = [Option(**d) for d in option_dicts]
        return options
