import datetime
import io
from pathlib import Path

from options_framework.config import settings
from options_framework.data.data_loader import DataLoader
from options_framework.option import Option
from options_framework.option_types import OptionType, SelectFilter

def map_data_file_fields() -> dict:
    columns_idx = settings.COLUMN_ORDER
    column_field_mapping = settings.FIELD_MAPPING
    field_mapping = {field_name:column_idx for field_name, column_map in column_field_mapping.items()
                     for column_name, column_idx in columns_idx.items() if column_map == column_name}
    option_id_columns = settings.DATA_IMPORT_FILE_PROPERTIES.option_id_columns
    option_id_mapping = [column_idx for option_id_col_name in option_id_columns
                         for column_name, column_idx in columns_idx.items() if column_name == option_id_col_name]
    field_mapping['option_id'] = option_id_mapping
    return field_mapping


class FileDataLoader(DataLoader):

    def load_cache(self, quote_datetime: datetime.datetime):
        pass # not used for file data loader. Each option chain is loaded from a file each time it is needed

    def __init__(self, *, start: datetime.datetime, end: datetime.datetime, select_filter: SelectFilter,
                 fields_list: list[str] = None):
        super().__init__(start=start, end=end, select_filter=select_filter, fields_list=fields_list)
        self.field_mapping = map_data_file_fields()
        self.data_root_folder = settings.DATA_IMPORT_FILE_PROPERTIES.data_files_folder
        self.last_loaded_date = start

    def get_option_chain(self, quote_datetime: datetime.datetime):
        filename = settings.DATA_IMPORT_FILE_PROPERTIES.data_file_name_format.replace('{year}', str(quote_datetime.year)) \
            .replace('{month}', str(quote_datetime.month).zfill(2)) \
            .replace('{day}', str(quote_datetime.day).zfill(2)) \
            .replace('{hour}', str(quote_datetime.hour).zfill(2)) \
            .replace('{minute}', str(quote_datetime.minute).zfill(2))

        data_file_path = Path(self.data_root_folder, filename)
        data_file = open(data_file_path, 'r')

        if settings.DATA_IMPORT_FILE_PROPERTIES.first_row_is_header:
            data_file.readline()

        option_data_reader = self._load_data_generator(data_file)
        options = [o for o in option_data_reader]
        data_file.close()
        self.last_loaded_date = quote_datetime

        super().on_option_chain_loaded_loaded(quote_datetime=quote_datetime, option_chain=options)

    def on_options_opened(self, options: list[Option]) -> None:
        pass

    def _load_data_generator(self, f: io.TextIOWrapper):
        line = f.readline()

        while line:
            values = line.split(settings.DATA_IMPORT_FILE_PROPERTIES.column_delimiter)

            data_symbol = values[self.field_mapping['symbol']]
            if data_symbol < self.select_filter.symbol:
                line = f.readline()
                continue
            elif data_symbol > self.select_filter.symbol:
                return

            option_type_value = values[self.field_mapping['option_type']]
            if option_type_value == settings.DATA_IMPORT_FILE_PROPERTIES.call_value_in_data:
                option_type = OptionType.CALL
            elif option_type_value == settings.DATA_IMPORT_FILE_PROPERTIES.put_value_in_data:
                option_type = OptionType.PUT
            else:
                raise ValueError("Data import file properties option type settings do not match data")

            if self.select_filter.option_type and self.select_filter.option_type != option_type:
                line = f.readline()
                continue

            expiration = datetime.datetime.strptime(values[self.field_mapping['expiration']],
                                                    settings.DATA_IMPORT_FILE_PROPERTIES.expiration_date_format).date()
            strike = float(values[self.field_mapping['strike']])
            quotedate = datetime.datetime.strptime(values[self.field_mapping['quote_datetime']],
                                                   settings.DATA_IMPORT_FILE_PROPERTIES.quote_date_format)
            spot_price = float(values[self.field_mapping['spot_price']])
            bid = float(values[self.field_mapping['bid']])
            ask = float(values[self.field_mapping['ask']])
            price = ((ask - bid) / 2) + bid

            if self.select_filter.expiration_dte:
                if self.select_filter.expiration_dte.low:
                    low_date = quotedate + datetime.timedelta(days=self.select_filter.expiration_dte.low)
                    if expiration < low_date.date():
                        line = f.readline()
                        continue
                if self.select_filter.expiration_dte.high:
                    high_date = quotedate + datetime.timedelta(days=self.select_filter.expiration_dte.high)
                    if expiration > high_date.date():
                        line = f.readline()
                        continue

            if self.select_filter.strike_offset:
                if self.select_filter.strike_offset.low:
                    low_strike = spot_price - self.select_filter.strike_offset.low
                    if strike < low_strike:
                        line = f.readline()
                        continue
                    high_strike = spot_price + self.select_filter.strike_offset.high
                    if strike > high_strike:
                        line = f.readline()
                        continue

            if 'delta' in self.fields_list:
                delta = float(values[self.field_mapping['delta']]) if 'delta' in settings.FIELD_MAPPING else None
                if self.select_filter.delta_range.low and self.select_filter.delta_range.high:
                    if delta < self.select_filter.delta_range.low or delta > self.select_filter.delta_range.high:
                        line = f.readline()
                        continue
            else:
                delta = None
            if 'gamma' in self.fields_list:
                gamma = float(values[self.field_mapping['gamma']]) if 'gamma' in settings.FIELD_MAPPING else None
                if self.select_filter.gamma_range.low and self.select_filter.gamma_range.high:
                    if delta < self.select_filter.gamma_range.low or delta > self.select_filter.gamma_range.high:
                        line = f.readline()
                        continue
            else:
                gamma = None
            if 'theta' in self.fields_list:
                theta = float(values[self.field_mapping['theta']]) if 'theta' in settings.FIELD_MAPPING else None
                if self.select_filter.theta_range.low and self.select_filter.theta_range.high:
                    if delta < self.select_filter.theta_range.low or delta > self.select_filter.theta_range.high:
                        line = f.readline()
                        continue
            else:
                theta = None
            if 'vega' in self.fields_list:
                vega = float(values[self.field_mapping['vega']]) if 'vega' in settings.FIELD_MAPPING else None
                if self.select_filter.vega_range.low and self.select_filter.vega_range.high:
                    if delta < self.select_filter.vega_range.low or delta > self.select_filter.vega_range.high:
                        line = f.readline()
                        continue
            else:
                vega = None
            if 'rho' in self.fields_list:
                rho = float(values[self.field_mapping['rho']]) if 'rho' in settings.FIELD_MAPPING else None
                if self.select_filter.rho_range.low and self.select_filter.rho_range.high:
                    if delta < self.select_filter.rho_range.low or delta > self.select_filter.rho_range.high:
                        line = f.readline()
                        continue
            else:
                rho = None
            if 'open_interest' in self.fields_list:
                open_interest = float(values[self.field_mapping['open_interest']]) \
                    if 'open_interest' in settings.FIELD_MAPPING else None
                if self.select_filter.open_interest_range.low and self.select_filter.open_interest_range.high:
                    if delta < self.select_filter.open_interest_range.low or delta > self.select_filter.open_interest_range.high:
                        line = f.readline()
                        continue
            else:
                open_interest = None
            if 'implied_volatility' in self.fields_list:
                implied_volatility = float(values[self.field_mapping['implied_volatility']]) \
                    if 'implied_volatility' in settings.FIELD_MAPPING else None
                if self.select_filter.implied_volatility_range.low and self.select_filter.implied_volatility_range.high:
                    if delta < self.select_filter.implied_volatility_range.low or delta > self.select_filter.implied_volatility_range.high:
                        line = f.readline()
                        continue
            else:
                implied_volatility = None

            option_id = ''.join([values[idx] for idx in self.field_mapping['option_id']])

            option = Option(option_id=option_id, symbol=self.select_filter.symbol, strike=strike, expiration=expiration,
                            option_type=option_type, quote_datetime=quotedate, spot_price=spot_price,
                            bid=bid, ask=ask, price=price,
                            delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho,
                            open_interest=open_interest, implied_volatility=implied_volatility)
            yield option
            line = f.readline()
