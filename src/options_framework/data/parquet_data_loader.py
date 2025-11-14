import datetime
from dateutil.relativedelta import relativedelta
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option_types import SelectFilter

ts_type = pa.timestamp('ms')


class ParquetDataLoader(DataLoader):
    def __init__(self, *, start: datetime.datetime, end: datetime.datetime, select_filter: SelectFilter,
                 extended_option_attributes: list[str] = None):
        super().__init__(start=start, end=end, select_filter=select_filter, extended_option_attributes=extended_option_attributes)
        self.options_folder = Path(settings['data_settings']['options_folder'])
        self.field_mapping = settings['data_settings']['field_mapping']
        self.columns = [self.field_mapping[f] for f in self.option_required_fields] + [self.field_mapping[f] for f in self.extended_option_attributes]


    def load_option_chain_data(self, symbol: str, start: datetime.datetime, end: datetime.datetime):
        folder = self.options_folder.joinpath(settings['data_settings']['folder_name_mask'].replace('{ticker}', symbol))
        file_name_mask = settings['data_settings']['file_name_mask'].replace('{ticker}', symbol)
        option_files_list = list(folder.glob(file_name_mask))

        #option_files = eval(file_list_statement) # (f for f in option_files if int(f.name[-12:-8]) >= self.start_datetime.year and int(f.name[-12:-8]) <= self.end_datetime.year)
        tables = []
        size = 0
        max_size = settings['data_settings']['max_pickle_file_size']
        qd_field = settings['data_settings']['field_mapping']['quote_datetime']
        interval = settings['data_settings']['file_interval']
        delta = "days=1" if interval == "day" else "years=1" if interval == "year" else "months=1"
        file_date = 'f\'' + settings['data_settings']['file_data_date'] + '\''
        file_date_format = settings['data_settings']['file_date_format']
        dts = pa.nulls(0, type=ts_type)
        start_date = start.date()
        end_date = end.date()
        for f in option_files_list:
            file_date_str = eval(file_date)
            file_first = eval(f'datetime.datetime.strptime(\'{file_date_str}\', \'{file_date_format}\')')
            file_last = eval(f'file_first + relativedelta({delta})')
            file_first, file_last = file_first.date(), file_last.date()
            size += f.stat().st_size * 1.5 # pandas is larger on disk than parquet - we don't want to overrun the space allowed

            if start_date <= file_last:
                if end_date >= file_first:
                    size += f.stat().st_size * 1.5  # pandas is larger on disk than parquet - we don't want to overrun the space allowed
                    if size < max_size:
                        tables.append(f)
                    ta = pq.read_table(f, columns=[qd_field])
                    datetimes = ta[qd_field].combine_chunks()
                    dts = pa.concat_arrays([dts, datetimes])
                else:
                    break

        # get table for test dates
        table = pq.read_table(tables, columns=self.columns)
        table = table.filter(pc.greater_equal(table[qd_field], start))
        table = table.filter(pc.less(table[qd_field], (end + datetime.timedelta(days=1))))

        # get testing dates in order
        dts = pc.unique(dts)
        dts = pc.filter(dts, pc.greater_equal(dts, start))
        dts = pc.filter(dts, pc.less(dts, (end + datetime.timedelta(days=1))))
        dts = dts.to_numpy()
        dts = dts.tolist()

        dts.sort()
        df = table.to_pandas()
        df = df.rename(columns={old:new for (new, old) in self.field_mapping.items()})
        df = df.sort_values(by=['quote_datetime', 'expiration', 'option_type', 'strike'])
        #df = df[(df['quote_datetime'] >= self.start_datetime) & (df['quote_datetime'] <= self.end_datetime)]
        df['expiration'] = df['expiration'].dt.date
        df['price'] = df['price'].round(2)
        # filter database
        ft = self.select_filter
        if ft.expiration_dte.low is not None and ft.expiration_dte.high is not None:
            df['exp'] = pd.to_datetime(df['expiration'])
            df['qd'] = df['quote_datetime'].dt.normalize()
            df['tdelta'] = df['exp'] - df['qd']
            df['tdelta'] = df['tdelta'].dt.days
            df = df[(df['tdelta'] >= ft.expiration_dte.low) & (df['tdelta'] <= ft.expiration_dte.high)]
            df = df.drop(['exp', 'qd','tdelta'], axis=1)
        start = df.iloc[0]['quote_datetime'].to_pydatetime()
        super().option_chain_load_data_complete(symbol=symbol, quote_datetime=start, options_data=df, datetimes=dts)


