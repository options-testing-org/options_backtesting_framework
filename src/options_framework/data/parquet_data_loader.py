import pandas as pd

from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import SelectFilter
from pandas import DataFrame
import datetime
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from options_framework.config import settings


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
        file_list_statement = (settings['data_settings']['file_list_generator']
                               .replace('{ticker}', symbol)
                               .replace('{start.year}', str(start.year))
                               .replace('{start.month}', str(start.month))
                               .replace('{start.day}', str(start.day))
                               .replace('{end.year}', str(end.year))
                               .replace('{end.month}', str(end.month))
                               .replace('{end.day}', str(end.day)))

        option_files = eval(file_list_statement) # (f for f in option_files if int(f.name[-12:-8]) >= self.start_datetime.year and int(f.name[-12:-8]) <= self.end_datetime.year)
        tables = []
        for of in option_files:
            ta = pq.read_table(source=of)
            tables.append(ta)
        tas = pa.concat_tables(tables)
        df = tas.to_pandas()
        df = df[self.columns]
        df = df.rename(columns={old:new for (new, old) in self.field_mapping.items()})
        df = df.sort_values(by=['quote_datetime', 'expiration', 'option_type', 'strike'])
        df = df[(df['quote_datetime'] >= self.start_datetime) & (df['quote_datetime'] <= self.end_datetime)]
        df['expiration'] = df['expiration'].dt.date
        df['price'] = df['price'].round(2)
        super().option_chain_load_data_complete(symbol=symbol, quote_datetime=start, options_data=df)


    # # Get option rows starting from the current quote date
    # def on_options_opened(self, options: list[Option]) -> None:
    #     temp_data_path = Path.cwd().joinpath('temp_data')
    #     symbol = options[0].symbol
    #     pickle_file = next((x for x in temp_data_path.iterdir() if x.is_file() and x.name.startswith(symbol)))
    #     df = pd.read_pickle(pickle_file)
    #     quote_datetime = options[0].quote_datetime
    #     df = df[df.index > quote_datetime]
    #     for option in options:
    #         option_data = df[df['option_id'] == option.option_id]
    #         option.update_cache = option_data

