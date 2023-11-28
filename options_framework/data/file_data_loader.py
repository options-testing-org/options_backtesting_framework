import datetime
import io
from pathlib import Path
from pydispatch import Dispatcher

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType


class FileDataLoader(DataLoader):

    def __init__(self, settings_file: str, fields: list = None, *args, **kwargs):
        super().__init__(settings_file=settings_file, fields=fields, *args, **kwargs)
        self.field_mapping = self._map_data_file_fields()
        self.fields = list(self.field_mapping.keys())

    def load_data(self, quote_datetime: datetime.datetime, symbol: str, option_type_filter: OptionType = None,
                  range_filters: dict = None, file_path: str = None, **kwargs):
        if 'file_path' is None:
            raise ValueError('Must provide file_path')
        data_root_folder = settings.DATA_FILES_ROOT_FOLDER
        data_file_path = Path(data_root_folder, file_path)

        data_file = open(data_file_path, 'r')
        if settings.DATA_IMPORT_FILE_PROPERTIES.first_row_is_header:
            data_file.readline()

        option_data_reader = self._load_data_generator(data_file, symbol, option_type_filter, range_filters)
        options = [o for o in option_data_reader]
        data_file.close()

        super().on_data_loaded(quote_datetime=quote_datetime, option_chain=options)

    def _load_data_generator(self, f: io.TextIOWrapper, symbol: str, option_type_filter: OptionType = None,
                             range_filters: dict = None):
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

            if option_type_filter:
                if option_type != option_type_filter:
                    line = f.readline()
                    continue

            expiration = datetime.datetime.strptime(values[self.field_mapping['expiration']],
                                                    settings.DATA_IMPORT_FILE_PROPERTIES.expiration_date_format)
            if range_filters and 'expiration' in range_filters.keys():
                expiration_range = range_filters['expiration']
                if expiration < expiration_range['low'] or expiration > expiration_range['high']:
                    line = f.readline()
                    continue

            strike = float(values[self.field_mapping['strike']])
            if range_filters and 'strike' in range_filters.keys():
                strike_range = range_filters['strike']
                if strike < strike_range['low'] or strike > strike_range['high']:
                    line = f.readline()
                    continue

            delta = float(values[self.field_mapping['delta']]) if 'delta' in self.fields else None
            if range_filters and delta and 'delta' in range_filters.keys():
                delta_range = range_filters['delta']
                if delta < delta_range['low'] or delta > delta_range['high']:
                    line = f.readline()
                    continue
            gamma = float(values[self.field_mapping['gamma']]) if 'gamma' in self.fields else None
            if range_filters and gamma and 'gamma' in range_filters.keys():
                gamma_range = range_filters['gamma']
                if gamma < gamma_range['low'] or gamma > gamma_range['high']:
                    line = f.readline()
                    continue
            theta = float(values[self.field_mapping['theta']]) if 'theta' in self.fields else None
            if range_filters and theta and 'theta' in range_filters.keys():
                theta_range = range_filters['theta']
                if theta < theta_range['low'] or theta > theta_range['high']:
                    line = f.readline()
                    continue
            vega = float(values[self.field_mapping['vega']]) if 'vega' in self.fields else None
            if range_filters and vega and 'vega' in range_filters.keys():
                vega_range = range_filters['vega']
                if vega < vega_range['low'] or vega > vega_range['high']:
                    line = f.readline()
                    continue
            rho = float(values[self.field_mapping['rho']]) if 'rho' in self.fields else None
            if range_filters and rho and 'rho' in range_filters.keys():
                rho_range = range_filters['rho']
                if rho < rho_range['low'] or rho > rho_range['high']:
                    line = f.readline()
                    continue
            open_interest = float(values[self.field_mapping['open_interest']]) \
                if 'open_interest' in self.fields else None
            if range_filters and open_interest and 'open_interest' in range_filters.keys():
                open_interest_range = range_filters['open_interest']
                if open_interest < open_interest_range['low'] or open_interest > open_interest_range['high']:
                    line = f.readline()
                    continue
            implied_volatility = float(values[self.field_mapping['implied_volatility']]) \
                if 'implied_volatility' in self.fields else None
            if range_filters and implied_volatility and 'implied_volatility' in range_filters.keys():
                implied_volatility_range = range_filters['implied_volatility']
                if (implied_volatility < implied_volatility_range['low']
                        or implied_volatility > implied_volatility_range['high']):
                    line = f.readline()
                    continue

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
