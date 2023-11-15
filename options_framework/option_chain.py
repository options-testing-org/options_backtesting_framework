import datetime

from .option_types import OptionType, TransactionType
from .option import Option
from .utils.helpers import distinct
import tomllib

# option_field_map = {'symbol': None, 'expiration': None, 'strike': None, 'option_type': None,
#                     'quote_date': None, 'spot_price': None, 'bid': None, 'ask': None,
#                     'delta': None, 'gamma': None, 'theta': None, 'vega': None, 'rho': None,
#                     'open_interest': None, 'implied_volatility': None}
#
#

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
        distinct_strikes = list(
            distinct([x.strikes for x in self._chain if x.expiration.date() == expiration_date.date()]))
        return distinct_strikes

    def load_data_from_file(self, file_path: str, data_column_idx_positions,
                            has_headers: bool = False, option_type_filter: OptionType = None, strike_range: dict = None,
                            expiration_range: dict = None, delta_range: dict = None, *args, **kwargs):
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
        pass
        # line = f.readline()  # get next record
        # while line:
        #
        #     values = line.split(',')
        #
        #     expiration = datetime.datetime.strptime(values[dni_exp], "%m/%d/%Y")
        #     if expiration_range:
        #         if expiration < expiration_range['low']:
        #             line = f.readline()  # get next record
        #             continue  # don't process this record if it's not the correct expiration
        #         if expiration > expiration_range['high']:
        #             return  # stop processing all records when out of expiration range
        #
        #     strike = float(values[dni_strike])
        #     if strike_range:
        #         if strike < strike_range['low']:
        #             line = f.readline()  # get next record
        #             continue # don't process if it's not within the strike range
        #         if strike > strike_range['high']:
        #             if expiration_range and expiration == expiration_range['high']:
        #                 return  # high strike in expiration range was reached. Stop processing the file.
        #             else:
        #                 line = f.readline()  # get next record
        #                 continue
        #
        #     delta = float(values[dni_delta])
        #     if delta_range:
        #         if delta < delta_range['low'] or delta > delta_range['high']:
        #             line = f.readline()  # get next record
        #             continue
        #
        #     option_type = OptionType.CALL if values[dni_type] == 'call' else OptionType.PUT
        #     if option_type_filter:
        #         if not option_type == option_type_filter:
        #             line = f.readline()
        #             continue
        #
        #     option_id, symbol = values[dni_id], values[dni_symbol]
        #     quote_date, spot_price, bid, ask = datetime.datetime.strptime(values[dni_date], "%m/%d/%Y"), \
        #         float(values[dni_spot_price]), float(values[dni_bid]), float(values[dni_ask])
        #     price = ((ask - bid)/2) + bid
        #     gamma, theta, vega = float(values[dni_gamma]), float(values[dni_theta]), \
        #         float(values[dni_vega])
        #     open_interest, implied_volatility = int(values[dni_oi]), float(values[dni_iv])
        #
        #     option = Option(option_id, symbol, strike, expiration, option_type, quote_date, spot_price, bid, ask,
        #                     price, delta=delta, gamma=gamma, theta=theta, vega=vega,
        #                     open_interest=open_interest, implied_volatility=implied_volatility)
        #     yield option
        #     line = f.readline()  # get next record


class DataFileMap:
    """
    When using local data in a flat file, the column positions for each value must be mapped to the
    appropriate option field to load the data into option objects.
    """

    def __init__(self):
        self._implied_volatility = None
        self._open_interest = None
        self._rho = None
        self._vega = None
        self._theta = None
        self._gamma = None
        self._delta = None
        self._ask = None
        self._bid = None
        self._spot_price = None
        self._quote_date = None
        self._option_type = None
        self._strike = None
        self._expiration = None
        self._symbol = None
        self._option_id = None
        self._call_value = None
        self._put_value = None
        self._column_map = None

    @classmethod
    def load_column_mapping(cls, data_mapping_toml):
        with open(data_mapping_toml, 'rb') as f:
            mapping_info = tomllib.load(f)

        return cls()

    def map_columns_by_header_name(self,  column_field_map: dict):
        """
        This method will map the options fields to the corresponding columns in your data file.
        You must pass in the header row as the first argument. The "headers" list is a list of the
        columns you will map to the option fields. The "option_fields" list is a list of
        fields to map to the headers list. They need to be in the same order so the correct
        columns will be mapped to the option fields.

        symbol strike, expiration, option_type quote_date, spot_price, bid, ask ' \
    + 'delta gamma theta vega rho open_interest implied_volatility

        The required option fields of symbol, expiration, strike, and option type must be mapped.
        If an "id" field is not specified, one will be generated using the required option fields.
        All other fields are optional.

        The call and put values in the file must be provided so the OptionType property can be set
        on the option object. For example, if your file contains the letters 'C' and 'P' to indicate a call or put,
        you would pass those values.


        :param column_field_map: A dictionary mapping the option fields to the column names
        :param call_value: The value your file contains to indicate a call option
        :param put_value: The value your file contains to indicate a put option
        :return: The column mapping
        """

        for key, value in column_field_map.items():
            setattr(self, key, value)

        # column_index_values = [all_headers.index(item) for item in column_field_map.values()]
        #
        # column_map = dict(zip(column_field_map.keys(), column_index_values))
        # if 'id' in column_map:
        #     column_map['id'] = [column_map['id']]
        # else:
        #     column_map['id'] = [column_map['symbol'], column_map['expiration'], column_map['strike'],
        #                         column_map['option_type']]
        #
        # self._column_map = column_map
        #
        # self._call_value = call_value
        # self._put_value = put_value

    @property
    def call_value(self):
        return self._call_value

    @call_value.setter
    def call_value(self, value):
        """
        The value in the data file to indication a call option
        :type value: str
        """
        self._call_value = value

    @property
    def put_value(self):
        """
        The value in the data file to indication a put option
        :type value: str
        """
        return self._put_value

    @put_value.setter
    def put_value(self, value):
        self._put_value = value

    @property
    def first_row_is_header(self):
        return self._first_row_header

    @property
    def option_id(self):
        return self._option_id

    @option_id.setter
    def option_id(self, *args):
        """
        The comma separated column name or names to be used as the option id
        :type args: list
        """
        self._option_id = args

    @property
    def symbol(self):
        return self._symbol

    @symbol.setter
    def symbol(self, value):
        """
        The name of the column that contains the ticker symbol
        :type value: str
        """
        self._symbol = value

    @property
    def expiration(self):
        return self._expiration

    @expiration.setter
    def expiration(self, value):
        """
        The name of the column that contains the expiration
        :type value: str
        """
        self._expiration = value

    @property
    def strike(self):
        return self._strike

    @strike.setter
    def strike(self, value):
        """
        The name of the column that contains the strike
        :type value: str
        """
        self._strike = value

    @property
    def option_type(self):
        return self._option_type

    @option_type.setter
    def option_type(self, value):
        """
        The name of the column that contains the option type
        :type value: str
        """
        self._option_type = value

    @property
    def quote_date(self):
        return self._quote_date

    @quote_date.setter
    def quote_date(self, value):
        """
        The name of the column that contains the quote date
        :type value: str
        """
        self._quote_date = value

    @property
    def spot_price(self):
        return self._spot_price

    @spot_price.setter
    def spot_price(self, value):
        """
        The name of the column that contains the spot price of the underlying asset
        :type value: str
        """
        self._spot_price = value

    @property
    def bid(self):
        return self._bid

    @bid.setter
    def bid(self, value):
        """
        The name of the column that contains the bid
        :type value: str
        """
        self._bid = value

    @property
    def ask(self):
        return self._ask

    @ask.setter
    def ask(self, value):
        """
        The name of the column that contains the ask
        :type value: str
        """
        self._ask = value

    @property
    def delta(self):
        return self._delta

    @delta.setter
    def delta(self, value):
        """
        The name of the column that contains the delta
        :type value: str
        """
        self._delta = value

    @property
    def gamma(self):
        return self._gamma

    @gamma.setter
    def gamma(self, value):
        """
        The name of the column that contains the gamma
        :type value: str
        """
        self._gamma = value

    @property
    def theta(self):
        return self._theta

    @theta.setter
    def theta(self, value):
        """
        The name of the column that contains the theta
        :type value: str
        """
        self._theta = value

    @property
    def vega(self):
        return self._vega

    @vega.setter
    def vega(self, value):
        """
        The name of the column that contains the delta
        :type value: str
        """
        self._vega = value

    @property
    def rho(self):
        return self._rho

    @rho.setter
    def rho(self, value):
        """
        The name of the column that contains the rho
        :type value: str
        """
        self._rho = value

    @property
    def open_interest(self):
        return self._open_interest

    @open_interest.setter
    def open_interest(self, value):
        """
        The name of the column that contains the open interest
        :type value: str
        """
        self._open_interest = value

    @property
    def implied_volatility(self):
        return self._implied_volatility

    @implied_volatility.setter
    def implied_volatility(self, value):
        """
        The name of the column that contains the implied volatility
        :type value: str
        """
        self._implied_volatility = value

        # DataColumnMap(
        #     i_id=dn_headers.index('AKA'),
        #     i_symbol=dn_headers.index('UnderlyingSymbol'),
        #     i_strike=dn_headers.index('Strike'),
        #     i_expiration=dn_headers.index('Expiration'),
        #     i_option_type=dn_headers.index('Type'),
        #     i_quote_date=dn_headers.index('DataDate'),
        #     i_spot_price=dn_headers.index('UnderlyingPrice'),
        #     i_bid=dn_headers.index('Bid'),
        #     i_ask=dn_headers.index('Ask'),
        #     i_delta=dn_headers.index('Delta'),
        #     i_gamma=dn_headers.index('Gamma'),
        #     i_theta=dn_headers.index('Theta'),
        #     i_vega=dn_headers.index('Vega'),
        #     i_open_interest=dn_headers.index('OpenInterest'),
        #     i_implied_volatility=dn_headers.index('IV'))
