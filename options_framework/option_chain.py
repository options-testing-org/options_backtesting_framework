import datetime

from .option_types import OptionType, TransactionType
from .option import Option
from .utils.helpers import distinct

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

    def load_daily_data_from_file(self, file_path, select_option_type=None, select_strike_range=None,
                                        select_expiration_range=None,
                                        select_delta_range=None, *args, **kwargs):
        """

        :param file_path:
        :param select_option_type:
        :param select_strike_range:
        :param select_expiration_range:
        :param select_delta_range:
        :param args:
        :param kwargs:
        """
        data_file = open(file_path, 'r')
        data_file.readline()  # read header line and ignore
        opt_gen = self._import_daily_options_from_file(data_file, select_option_type, select_strike_range,
                                                       select_expiration_range, select_delta_range)

        options = [o for o in opt_gen]

        data_file.close()

        self._chain = options

    def load_intraday_options_from_file(self, file_path):
        pass

    def _import_daily_options_from_file(self, data_file, select_option_type=None, select_strike_range=None,
                                        select_expiration_range=None,
                                        select_delta_range=None):

        if select_delta_range is None:
            select_delta_range = []
        else:
            select_delta_range.sort()

        if select_expiration_range is None:
            select_expiration_range = []
        else:
            select_expiration_range.sort()

        if select_strike_range is None:
            select_strike_range = []
        else:
            select_strike_range.sort()

        line = data_file.readline()  # get next record

        while line:

            values = line.split(',')

            expiration = datetime.datetime.strptime(values[dni_exp], "%m/%d/%Y")
            hi_date = None
            if select_expiration_range:
                low_date = select_expiration_range[0]
                hi_date = select_expiration_range[1]
                if expiration < low_date:
                    line = data_file.readline()  # get next record
                    continue  # don't process this record if it's not the correct expiration
                if expiration > hi_date:
                    return  # stop processing all records when out of expiration range

            strike = float(values[dni_strike])
            if select_strike_range:
                lo_strike = select_strike_range[0]
                hi_strike = select_strike_range[1]
                if strike < lo_strike:
                    line = data_file.readline()  # get next record
                    continue # don't process if it's not within the strike range
                if strike > hi_strike:
                    if select_expiration_range and expiration == hi_date:
                        return  # last strike in expiration range was reached. Stop processing the file.
                    else:
                        line = data_file.readline()  # get next record
                        continue

            delta = float(values[dni_delta])
            if select_delta_range:
                lo_delta = select_delta_range[0]
                hi_delta = select_delta_range[1]
                if delta < lo_delta or delta > hi_delta:
                    line = data_file.readline()  # get next record
                    continue

            option_type = OptionType.CALL if values[dni_type] == 'call' else OptionType.PUT
            if select_option_type:
                if not option_type == select_option_type:
                    line = data_file.readline()
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
            line = data_file.readline()  # get next record

