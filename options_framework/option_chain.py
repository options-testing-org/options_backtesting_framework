import datetime

from options_framework.option_types import OptionType, TransactionType
from options_framework.option import Option
from options_framework.utils.helpers import distinct

# Delta Neutral options file headers
dn_headers = ['AKA', 'UnderlyingSymbol', 'UnderlyingPrice', 'Exchange', 'OptionSymbol', 'OptionExt', 'Type', 'Expiration',
           'DataDate', 'Strike', 'Last', 'Bid', 'Ask', 'Volume', 'OpenInterest', 'IV', 'Delta', 'Gamma', 'Theta',
           'Vega']

# get column indices
dni_id, dni_symbol, dni_spot_price, dni_exp, dni_strike, dni_type, dni_date, dni_bid, dni_ask, dni_oi, dni_iv, dni_delta, dni_gamma, \
    dni_theta, dni_vega = dn_headers.index('AKA'), dn_headers.index('UnderlyingSymbol'), dn_headers.index('UnderlyingPrice'), \
    dn_headers.index('Expiration'), dn_headers.index('Strike'), dn_headers.index('Type'), \
    dn_headers.index('DataDate'), dn_headers.index('Bid'), dn_headers.index('Ask'), \
    dn_headers.index('OpenInterest'), dn_headers.index('IV'), dn_headers.index('Delta'), \
    dn_headers.index('Gamma'), dn_headers.index('Theta'), dn_headers.index('Vega')

# CBOE options file headers
cboe_headers = ['underlying_symbol', 'quote_datetime', 'root', 'expiration', 'strike', 'option_type', 'open', 'high',
                 'low', 'close', 'trade_volume', 'bid_size', 'bid', 'ask_size', 'ask', 'underlying_bid',
                 'underlying_ask', 'implied_underlying_price', 'active_underlying_price', 'implied_volatility',
                 'delta', 'gamma', 'theta', 'vega', 'rho', 'open_interest']

# get cboe column indices
i_symbol, i_exp, i_strike, i_type, i_date, i_spot_price, i_bid, i_ask, i_delta, i_gamma, i_theta, i_vega, i_rho, i_oi, \
    i_iv = cboe_headers.index('root'), cboe_headers.index('expiration'), cboe_headers.index('strike'), \
    cboe_headers.index('option_type'), cboe_headers.index('quote_datetime'), cboe_headers.index('active_underlying_price'), \
    cboe_headers.index('bid'), cboe_headers.index('ask'), cboe_headers.index('delta'), cboe_headers.index('gamma'), \
    cboe_headers.index('theta'), cboe_headers.index('vega'), cboe_headers.index('rho'), \
    cboe_headers.index('open_interest'), cboe_headers.index('implied_volatility')


class OptionChain:

    def __init__(self):
        self._chain = []

    @property
    def option_chain(self):
        return self._chain

    def get_expirations(self):
        if not self._chain:
            raise ValueError("You must load the options data.")
        distinct_expirations = list(distinct([x.expiration for x in self._chain]))
        return distinct_expirations

    def get_strikes_for_expiration(self, expiration_date):
        if not self._chain:
            raise ValueError("You must load the options data.")
        distinct_strikes = list(distinct([x.strikes for x in self._chain if x.expiration.date() == expiration_date.date()]))
        return distinct_strikes

    def load_delta_neutral_data_from_file(self, file_path, option_type_filter=None, strike_range=None,
                                        expiration_range=None, delta_range=None, *args, **kwargs):
        """
        Loads data for one ticker, one day.
        To filter the data, use the select parameters:
        :param file_path: The absolute path to the data file
        :param option_type_filter: set to OptionType.PUT or OptionType.CALL to filter for option type. Default is None.
        :param strike_range: None for all strikes.
                Dictionary for strike range: {'low': <low value>, 'high': <high value>}
        :param expiration_range: None for all expirations
                Dictionary for expiration range: {"low": <first exp>, "high": <last exp>}
        :param delta_range: None for all deltas.
                Dictionary for delta range: {'low': <low value>, 'high': <high value>}
        :param args:
        :param kwargs:
        """
        data_file = open(file_path, 'r')
        data_file.readline()  # read header line and ignore
        opt_gen = self._delta_neutral_generator(data_file, option_type_filter, strike_range,
                                                       expiration_range, delta_range)

        options = [o for o in opt_gen]

        data_file.close()

        self._chain = options

    def _delta_neutral_generator(self, f, option_type_filter=None, strike_range=None,
                                        expiration_range=None,
                                        delta_range=None):

        line = f.readline()  # get next record
        while line:

            values = line.split(',')

            expiration = datetime.datetime.strptime(values[dni_exp], "%m/%d/%Y")
            if expiration_range:
                if expiration < expiration_range['low']:
                    line = f.readline()  # get next record
                    continue  # don't process this record if it's not the correct expiration
                if expiration > expiration_range['high']:
                    return  # stop processing all records when out of expiration range

            strike = float(values[dni_strike])
            if strike_range:
                if strike < strike_range['low']:
                    line = f.readline()  # get next record
                    continue # don't process if it's not within the strike range
                if strike > strike_range['high']:
                    if expiration_range and expiration == expiration_range['high']:
                        return  # high strike in expiration range was reached. Stop processing the file.
                    else:
                        line = f.readline()  # get next record
                        continue

            delta = float(values[dni_delta])
            if delta_range:
                if delta < delta_range['low'] or delta > delta_range['high']:
                    line = f.readline()  # get next record
                    continue

            option_type = OptionType.CALL if values[dni_type] == 'call' else OptionType.PUT
            if option_type_filter:
                if not option_type == option_type_filter:
                    line = f.readline()
                    continue

            option_id, symbol = values[dni_id], values[dni_symbol]
            quote_date, spot_price, bid, ask = datetime.datetime.strptime(values[dni_date], "%m/%d/%Y"), \
                float(values[dni_spot_price]), float(values[dni_bid]), float(values[dni_ask])
            price = ((ask - bid)/2) + bid
            gamma, theta, vega = float(values[dni_gamma]), float(values[dni_theta]), \
                float(values[dni_vega])
            open_interest, implied_volatility = int(values[dni_oi]), float(values[dni_iv])

            option = Option(option_id, symbol, strike, expiration, option_type, quote_date, spot_price, bid, ask,
                            price, delta=delta, gamma=gamma, theta=theta, vega=vega,
                            open_interest=open_interest, implied_volatility=implied_volatility)
            yield option
            line = f.readline()  # get next record

    def load_cboe_options_from_file(self, file_path, option_type_filter=None, strike_range=None,
                                        expiration_range=None,
                                        delta_range=None):
        """
        Loads intraday data for one ticker, one day.
        To filter the data, use the select parameters:
        :param file_path: The absolute path to the data file
        :param option_type_filter: set to OptionType.PUT or OptionType.CALL to filter for option type. Default is None.
        :param strike_range: None for all strikes.
                Dictionary for strike range: {'low': <low value>, 'high': <high value>}
        :param expiration_range: None for all expirations
                Dictionary for expiration range: {"low": <first exp>, "high": <last exp>}
        :param delta_range: None for all deltas.
                Dictionary for delta range: {'low': <low value>, 'high': <high value>}
        :param args:
        :param kwargs:
        """
        data_file = open(file_path, 'r')
        data_file.readline()  # read header line and ignore
        opt_gen = self._cboe_generator(data_file, option_type_filter, strike_range,
                                                expiration_range, delta_range)

        options = [o for o in opt_gen]

        data_file.close()

        self._chain = options

    def _cboe_generator(self, f, option_type_filter=None, strike_range=None,
                                        expiration_range=None,
                                        delta_range=None):
        pass