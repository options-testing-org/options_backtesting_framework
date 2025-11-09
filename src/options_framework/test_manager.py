import datetime
import os
from options_framework.utils.helpers import temp_data_dir_cleanup
from dataclasses import dataclass, field

from options_framework.data.data_loader import DataLoader

from options_framework.data.sql_data_loader import SQLServerDataLoader
from options_framework.data.csv_data_loader import CSVDataLoader
from options_framework.data.parquet_data_loader import ParquetDataLoader
from options_framework.option_chain import OptionChain
from options_framework.option_portfolio import OptionPortfolio

from options_framework.option_types import SelectFilter
from options_framework.config import settings


@dataclass(repr=False)
class OptionTestManager:
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    select_filter: SelectFilter
    starting_cash: float
    extended_option_attributes: list = field(default_factory=lambda: [])
    option_chains: dict = field(default_factory=lambda: {})
    data_loader: DataLoader = field(init=False, default=None)
    portfolio: OptionPortfolio = field(init=False, default=None)

    def __post_init__(self):
        temp_data_dir_cleanup() # remove any leftover temp files from a previous run
        self.portfolio = OptionPortfolio(self.starting_cash, start_date=self.start_datetime, end_date=self.end_datetime)
        if settings['data_loader_type'] == "csv_data_loader":
            #     self.data_loader = FileDataLoader(start=self.start_datetime, end=self.end_datetime,
            #                                       select_filter=self.select_filter, fields_list=self.fields_list)
            pass
        elif settings['data_loader_type'] == "parquet_data_loader":
            self.data_loader = ParquetDataLoader(start=self.start_datetime, end=self.end_datetime,
                                                 select_filter=self.select_filter,
                                                 extended_option_attributes=self.extended_option_attributes)

        elif settings['data_loader_type'] == "sql_data_loader":
            self.data_loader = SQLServerDataLoader(start=self.start_datetime, end=self.end_datetime,
                                                   select_filter=self.select_filter,
                                                   extended_option_attributes=self.extended_option_attributes)
        else:
            raise Exception("Data loader is not set in settings, or data loader is not found.")

        self.portfolio.bind(new_position_opened=self.data_loader.on_options_opened)


    def initialize_ticker(self, symbol: str, quote_datetime: datetime.datetime) :
        if symbol not in self.option_chains.keys():
            option_chain = OptionChain(symbol=symbol)
            self.portfolio.bind(next=option_chain.on_next)
            self.data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
            self.data_loader.load_option_chain_data(symbol, quote_datetime, self.end_datetime)
            self.option_chains[symbol] = option_chain

    # Removes all the temporary pickle files used to hold data during the test
    def de_initialize(self):
        for symbol, option_chain in self.option_chains.items():
            os.unlink(option_chain.pickle_file)
