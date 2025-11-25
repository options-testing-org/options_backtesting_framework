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
    pickle_folder: Path
    cache: pd.DataFrame = field(init=False, default=None)
    datetimes: list = field(init=False, default_factory=lambda: [], repr=False)
    expirations: list = field(init=False, default_factory=lambda: [], repr=False)
    option_chain: list = field(init=False, default_factory=lambda: [], repr=False)
    expiration_strikes: dict = field(init=False, default_factory=lambda: {}, repr=False)
    _timelost_fn_format: str = field(init=False, default=None)

    def __post_init__(self):
        self._timelost_fn_format = settings['timeslot_filename_format']
        self.datetimes = datetimes = self.get_datetimes_in_date_range(self.pickle_folder, self.quote_datetime, self.end_datetime)

    def on_next(self, quote_datetime: datetime.datetime):
        # find quote datetime in datetimes list
        self.quote_datetime = quote_datetime
        try:
            dt = next(d for d in self.datetimes if d == quote_datetime)
        except StopIteration:
            # There are no matching timeslots for the quote given
            self.option_chain = []
            self.expirations = []
            self.expiration_strikes = {}
            return

        options = self.load_timeslot(quote_datetime=quote_datetime)
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

    def load_timeslot(self, quote_datetime: datetime.datetime) -> list[Option]:
        timeslots_root = self.pickle_folder / 'timeslot_pkl'
        ym_str = datetime.datetime.strftime(quote_datetime, '%Y_%m')
        timeslots_folder = timeslots_root.joinpath(ym_str)
        dt_str = datetime.datetime.strftime(quote_datetime, '%Y_%m_%d_%H_%M')
        find_timeslot = timeslots_folder.glob(f'{dt_str}.pkl')
        try:
            ts_file = next(find_timeslot)
        except StopIteration:
            raise ValueError(f'Cannot find option chain for {self.symbol} on {quote_datetime}.')

        with open(ts_file, 'rb') as f:
            options_data = pickle.load(f)
        options = [Option(**data) for data in options_data]
        return options

    def get_folder_as_date(self, folder):
        return folder, datetime.datetime.strptime(folder.name, '%Y_%m').date()

    def get_datetimes_in_date_range(self, folder, start_dt, end_dt):
        timeslot_folder = folder / 'timeslot_pkl'
        folders_list = timeslot_folder.glob('*')

        start_folder = datetime.date(start_dt.year, start_dt.month, 1)
        end_folder = datetime.date(end_dt.year, end_dt.month, 1)
        end = end_dt + datetime.timedelta(days=1) # Need to add a day so we can capture all the times from that day.

        datetimes = []
        while True:
            fol, folder_dt = self.get_folder_as_date(next(folders_list))

            if folder_dt >= start_folder:
                if folder_dt <= end_folder:
                    fol_dts = [datetime.datetime.strptime(f.stem, '%Y_%m_%d_%H_%M') for f in fol.iterdir()]
                    datetimes.extend(fol_dts)
                    #fol, folder_dt = self.get_folder_as_date(next(folders_list))
                else:
                    break



                # if start_date <
                #
                # if fol_dt < end_date:
                #     pass
                # if fol_dt >= start_date and fol_dt <= end_date:
                #     fol_dts = [datetime.datetime.strptime(f.stem, '%Y_%m_%d_%H_%M') for f in fol.iterdir()]
                #     datetimes.extend(fol_dts)
                # if fol_dt > end_date:
                #     break

        datetimes.sort()
        datetimes = [x for x in datetimes if x >= start_dt and x <= end]
        return datetimes


    def parse_folder_name_to_date(self, folder_name: str) -> datetime.date:
        dt = datetime.datetime.strptime(folder_name, '%Y_%m_%d').date()
        return dt


    def on_options_opened(self, options: list[Option]) -> list[dict] | None:
        option_pickle_folder = self.pickle_folder / 'option_pkl'
        for option in options:
            pkl_file = option_pickle_folder / f'{option.option_id}.pkl'
            if not pkl_file.exists():
                raise ValueError(f'Cannot find updates for option {option.option_id} : {str(option)}')
            with open(pkl_file, 'rb') as f:
                option_dicts = pickle.load(f)

            # get all updates past the current quote
            option.update_cache = [d for d in option_dicts if d['quote_datetime'] > self.quote_datetime]


