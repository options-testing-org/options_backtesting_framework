import datetime

from pandas import DataFrame, Series
from dataclasses import dataclass, field
from options_framework.option import Option
from options_framework.option_types import OptionType
from options_framework.utils.helpers import distinct

@dataclass
class OptionChain():

    symbol: str
    quote_datetime: datetime.datetime
    expirations: list #= field(init=False, default_factory=list, repr=False)
    last_loaded_date: datetime.datetime | None = field(init=False, default=None)
    data_cache: DataFrame | None = field(init=False, default=None)
    option_chain: list = field(init=False, default_factory=lambda: [], repr=False)
    expiration_strikes: dict = field(init=False, default_factory=lambda: {}, repr=False)

    def __post_init__(self):
        pass

    def next_option_chain(self, quote_datetime: datetime.datetime | datetime.date):
        pass


    def on_option_chain_loaded(self, symbol: str, quote_datetime: datetime.datetime, options_data: DataFrame):
        if symbol != self.symbol:
            return
        if len(options_data) == 0:
            self.last_loaded_date = quote_datetime
            return
        self.quote_datetime = quote_datetime
        self.data_cache = options_data
        self.last_loaded_date = options_data.iloc[-1].name.to_pydatetime()
        options = []
        if not quote_datetime in self.data_cache.index:
            return
        data = self.data_cache.loc[quote_datetime]

        # if only one row was returned, Pandas makes it a series
        if data.__class__.__name__ == 'Series':
            cols = data.index.tolist() + ['quote_datetime']
            data = DataFrame([data.values.tolist()], index=[data.name], columns=data.index.tolist())
        for i, row in data.iterrows():
            option = self.create_option(quote_datetime, row)
            options.append(option)
        self.option_chain = options
        data_expirations = list(distinct([option.expiration for option in self.option_chain]))
        self.expiration_strikes = {e: list(distinct([strike for strike in [option.strike
                                                                            for option in self.option_chain if
                                                                            option.expiration == e]])) for e in
                                                                            data_expirations}
        #print(f'option chain data loaded {symbol} {quote_datetime}')


    def create_option(self, quote_datetime: datetime.datetime | datetime.date, row: Series) -> Option:
        option = Option(
            option_id=row['option_id'],
            symbol=row['symbol'],
            expiration=row['expiration'].date(),
            strike=row['strike'],
            option_type=OptionType.CALL if row['option_type'] == 1 else OptionType.PUT,
            quote_datetime=row.name.to_pydatetime(),
            spot_price=row['spot_price'],
            bid=row['bid'],
            ask=row['ask'],
            price=row['price'],
            delta=row['delta'] if 'delta' in row.index else None,
            gamma=row['gamma'] if 'gamma' in row.index else None,
            theta=row['theta'] if 'theta' in row.index else None,
            vega=row['vega'] if 'vega' in row.index else None,
            rho=row['rho'] if 'rho' in row.index else None,
            open_interest=row['open_interest'] if 'open_interest' in row.index else None,
            implied_volatility=row['implied_volatility'] if 'implied_volatility' in row.index else None)
        return option
