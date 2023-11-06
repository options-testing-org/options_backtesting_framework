import datetime

from .option_types import OptionType, TransactionType
from .option import Option


class OptionChain:



    def __init__(self):
        self._chain = []
        self._datetime = None


    def load_data_from_file(self, file_path, *args, **kwargs):
        cols = ['UnderlyingSymbol', 'UnderlyingPrice', 'Type', 'Expiration', 'DataDate', 'Strike', 'Last', 'Bid', 'Ask',
                 'OpenInterest', 'IV', 'Delta', 'Gamma', 'Theta', 'Vega']
        headers = ['AKA','UnderlyingSymbol','UnderlyingPrice','Exchange','OptionSymbol','OptionExt','Type','Expiration',
                   'DataDate','Strike','Last','Bid','Ask','Volume','OpenInterest','IV','Delta','Gamma','Theta','Vega']
        options = []

        with open(file_path, 'r') as f:
            line = f.readline()
            i_id = headers.index('AKA')
            i_symbol = headers.index('UnderlyingSymbol')
            i_spot_price = headers.index('UnderlyingPrice')
            i_exp = headers.index('Expiration')
            i_strike = headers.index('Strike')
            i_type = headers.index('Type')
            i_date = headers.index('DataDate')
            i_bid = headers.index('Bid')
            i_ask = headers.index('Ask')
            i_oi = headers.index('OpenInterest')
            i_iv = headers.index('IV')
            i_delta = headers.index('Delta')
            i_gamma = headers.index('Gamma')
            i_theta = headers.index('Theta')
            i_vega = headers.index('Vega')
            line = f.readline()
            while len(line) > 0:
                print("'", line, "'")
                line = line.split(',')
                option_id = line[i_id]
                symbol = line[i_symbol]
                expiration = datetime.datetime.strptime(line[i_exp], "%m/%d/%Y")
                strike = float(line[i_strike])
                option_type = OptionType.CALL if line[i_type] == 'call' else OptionType.PUT
                quote_date = datetime.datetime.strptime(line[i_date], "%m/%d/%Y")
                spot_price = float(line[i_spot_price])
                bid = float(line[i_bid])
                ask = float(line[i_ask])
                oi = int(line[i_oi])
                iv = float(line[i_iv])
                delta = float(line[i_delta])
                gamma = float(line[i_gamma])
                theta = float(line[i_theta])
                vega = float(line[i_vega])

                option = Option(option_id, symbol, strike, expiration, option_type, quote_date, spot_price, bid,ask,
                                price=((ask - bid)/2)+bid, delta=delta, gamma=gamma, theta=theta, vega=vega,
                                open_interest=oi, implied_volatility=iv)
                options.append(option)
                line = f.readline()

            self._chain = [(x.strike, x) for x in options]

