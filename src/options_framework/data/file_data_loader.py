import datetime
import io
from pathlib import Path
from pydispatch import Dispatcher

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType


class FileDataLoader(DataLoader):

    def __init__(self, select_fields: list = None,
                 order_by_fields: list = None, *args, **kwargs):
        settings.load_file(settings.DATA_FILE_FORMAT_SETTINGS)
        self.field_mapping = self._map_data_file_fields()
        self.fields = list(self.field_mapping.keys())
        super().__init__(select_fields=select_fields, order_by_fields=order_by_fields, *args, **kwargs)

    def load_option_chain(self, *, quote_datetime: datetime.datetime, symbol: str,
                          filters: dict = None, data_file_name: str = None):
        # if file_path is None:
        #     raise ValueError('Must provide file_path')
        if filters and not all([f in self.select_fields for f in filters.keys()]):
            raise ValueError('Filter fields must be included in the select fields.')
        if filters is None:
            filters = {}
        data_root_folder = settings.DATA_FILES_FOLDER

        data_file_path = Path(data_root_folder, data_file_name)

        data_file = open(data_file_path, 'r')
        if settings.DATA_IMPORT_FILE_PROPERTIES.first_row_is_header:
            data_file.readline()

        option_data_reader = self._load_data_generator(data_file, symbol, filters)
        options = [o for o in option_data_reader]
        data_file.close()

        super().on_option_chain_loaded_loaded(quote_datetime=quote_datetime, option_chain=options)

    def _load_data_generator(self, f: io.TextIOWrapper, symbol: str, filters: dict = None):
        line = f.readline()
        while line:
            values = line.split(settings.DATA_IMPORT_FILE_PROPERTIES.column_delimiter)

            data_symbol = values[self.field_mapping['symbol']]
            if data_symbol < symbol:
                line = f.readline()
                continue
            elif data_symbol > symbol:
                return

            option_type_value = values[self.field_mapping['option_type']]
            if option_type_value == settings.DATA_IMPORT_FILE_PROPERTIES.call_value_in_data:
                option_type = OptionType.CALL
            elif option_type_value == settings.DATA_IMPORT_FILE_PROPERTIES.put_value_in_data:
                option_type = OptionType.PUT
            else:
                raise ValueError("Data import file properties option type settings do not match data")

            if 'option_type' in filters and option_type != filters['option_type']:
                line = f.readline()
                continue

            expiration = datetime.datetime.strptime(values[self.field_mapping['expiration']],
                                                    settings.DATA_IMPORT_FILE_PROPERTIES.expiration_date_format)
            if 'expiration' in filters.keys():
                if expiration.date() < filters['expiration']['low'] or expiration.date() > filters['expiration']['high']:
                    line = f.readline()
                    continue
            strike = float(values[self.field_mapping['strike']])
            if 'strike' in filters.keys():
                if strike < filters['strike']['low'] or strike > filters['strike']['high']:
                    line = f.readline()
                    continue
            if 'delta' in self.select_fields:
                delta = float(values[self.field_mapping['delta']]) if 'delta' in self.fields else None
                if 'delta' in filters.keys():
                    if delta < filters['delta']['low'] or delta > filters['delta']['high']:
                        line = f.readline()
                        continue
            else:
                delta = None
            if 'gamma' in self.select_fields:
                gamma = float(values[self.field_mapping['gamma']]) if 'gamma' in self.fields else None
                if 'gamma' in filters.keys():
                    if gamma < filters['gamma']['low'] or gamma > filters['gamma']['high']:
                        line = f.readline()
                        continue
            else:
                gamma = None
            if 'theta' in self.select_fields:
                theta = float(values[self.field_mapping['theta']]) if 'theta' in self.fields else None
                if 'theta' in filters.keys():
                    if theta < filters['theta']['low'] or theta > filters['theta']['high']:
                        line = f.readline()
                        continue
            else:
                theta = None
            if 'vega' in self.select_fields:
                vega = float(values[self.field_mapping['vega']]) if 'vega' in self.fields else None
                if 'vega' in filters.keys():
                    if vega < filters['vega']['low'] or vega > filters['vega']['high']:
                        line = f.readline()
                        continue
            else:
                vega = None
            if 'rho' in self.select_fields:
                rho = float(values[self.field_mapping['rho']]) if 'rho' in self.fields else None
                if 'rho' in filters.keys():
                    if rho < filters['rho']['low'] or rho > filters['rho']['high']:
                        line = f.readline()
                        continue
            else:
                rho = None
            if 'open_interest' in self.select_fields:
                open_interest = float(values[self.field_mapping['open_interest']]) \
                    if 'open_interest' in self.fields else None
                if 'open_interest' in filters.keys():
                    if open_interest < filters['open_interest']['low'] or open_interest > filters['open_interest']['high']:
                        line = f.readline()
                        continue
            else:
                open_interest = None
            if 'implied_volatility' in self.select_fields:
                implied_volatility = float(values[self.field_mapping['implied_volatility']]) \
                    if 'implied_volatility' in self.fields else None
                if 'implied_volatility' in filters.keys():
                    if (implied_volatility < filters['implied_volatility']['low']
                            or implied_volatility > filters['implied_volatility']['high']):
                        line = f.readline()
                        continue
            else:
                implied_volatility = None

            option_id = ''.join([values[idx] for idx in self.field_mapping['option_id']])

            option = Option(option_id=option_id, symbol=symbol, strike=strike, expiration=expiration,
                            option_type=option_type, delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho,
                            open_interest=open_interest, implied_volatility=implied_volatility)
            yield option
            line = f.readline()

    def _map_data_file_fields(self) -> dict:
        columns_idx = settings.COLUMN_ORDER
        column_field_mapping = settings.FIELD_MAPPING
        field_mapping = {field_name:column_idx for field_name, column_map in column_field_mapping.items()
                         for column_name, column_idx in columns_idx.items() if column_map == column_name}
        option_id_columns = settings.DATA_IMPORT_FILE_PROPERTIES.option_id_columns
        option_id_mapping = [column_idx for option_id_col_name in option_id_columns
                             for column_name, column_idx in columns_idx.items() if column_name == option_id_col_name]
        field_mapping['option_id'] = option_id_mapping
        return field_mapping
