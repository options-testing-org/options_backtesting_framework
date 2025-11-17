import datetime
import os
from options_framework.utils.helpers import temp_data_dir_cleanup
from dataclasses import dataclass, field

from options_framework.option_chain import OptionChain
from options_framework.option_portfolio import OptionPortfolio

from options_framework.config import settings


@dataclass(repr=False)
class OptionTestManager:
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    starting_cash: float

    option_chains: dict = field(default_factory=lambda: {})
    portfolio: OptionPortfolio = field(init=False, default=None)

    def __post_init__(self):
        temp_data_dir_cleanup() # remove any leftover temp files from a previous run
        self.portfolio = OptionPortfolio(self.starting_cash, start_date=self.start_datetime, end_date=self.end_datetime)

        self.portfolio.current_datetime = self.start_datetime
        #self.portfolio.bind(new_position_opened=self.data_loader.on_options_opened)


    def initialize_ticker(self, symbol: str, quote_datetime: datetime.datetime) :
        if symbol not in self.option_chains.keys():
            options_folder = settings['data_settings']['options_folder']
            option_chain = OptionChain(symbol=symbol, quote_datetime=quote_datetime, end_datetime=self.end_datetime,
                                       pickle_folder=options_folder)
            self.portfolio.bind(next=option_chain.on_next)
            self.portfolio.bind(new_position_opened=option_chain.on_options_opened)
            self.option_chains[symbol] = option_chain
