import datetime

from .option_types import OptionPositionType, OptionType
from .utils.helpers import decimalize_0, decimalize_2, decimalize_4

optional_fields = ['open_interest', 'iv', 'delta', 'gamma', 'theta', 'vega', 'rho', 'fee']

class Option:
    """
    The Option class holds all the values the pertain to a single option. The option can have just basic option information
    without any price or other current values. These values are id, symbol, strike, expiration and option type.
    Quote information can be set when the option is created and also using the update method.
    The trade_open and trade_close methods are used to capture open/close price and dates.
    """
    def __init__(self, option_id, symbol, strike, expiration, option_type,
                 quote_date=None, spot_price=None, bid=None, ask=None, price=None, *args, **kwargs):
        """
        Creates an option object. An option must have an id, symbol, strike, expiration and type at a minimum.
        Price information can be included or can be set using the update method.

        :param option_id: unique identifier for the option *required*
        :type option_id: Any
        :param symbol: ticker symbol for underlying asset *required*
        :type symbol: string
        :param strike: the strike price for the option *required*
        :type strike: float
        :param expiration: the expiration date for the option *required*
        :type expiration: datetime.datetime
        :param option_type: Put or Call option *required*
        :type option: OptionType
        :param quote_date: data date for price information
        :type quote_date: datetime.datetime
        :param spot_price: price of underlying on quote_date
        :type spot_price: float
        :param bid: bid price
        :type bid: float
        :param ask: ask price
        :type ask: float
        :param price: calculated price based on mid-point between bid and ask
        :type price: float
        :param args: arguments
        :type: list
        :param kwargs: keyword arguments
        :type: dictionary

        optional parameters: delta, theta, vega, gamma, iv, open_interest, rho, fee
        additional user-defined parameters passed as keyword arguments will be defined as attributes

        """
        # check for required fields
        if option_id is None:
            raise ValueError("option_id is required")
        if symbol is None:
            raise ValueError("symbol is required")
        if strike is None:
            raise ValueError("strike is required")
        if expiration is None:
            raise ValueError("expiration is required")
        if option_type is None:
            raise ValueError("option_type is required")
        if quote_date is not None and quote_date.date() > expiration.date():
            raise ValueError("Cannot create an option with a quote date past its expiration date")

        self._option_type = option_type
        self._option_id = option_id
        self._ticker_symbol = symbol
        self._strike = strike
        self._expiration = expiration
        self._quote_date = quote_date
        self._spot_price = spot_price
        self._bid = bid
        self._ask = ask
        self._price = price

        # The optional attributes are set using keyword arguments
        self._open_interest = None if kwargs is None else kwargs['open_interest'] if 'open_interest' in kwargs else None
        self._iv = None if kwargs is None else kwargs['iv'] if 'iv' in kwargs else None
        self._delta = None if kwargs is None else kwargs['delta'] if 'delta' in kwargs else None
        self._gamma = None if kwargs is None else kwargs['gamma'] if 'gamma' in kwargs else None
        self._theta = None if kwargs is None else kwargs['theta'] if 'theta' in kwargs else None
        self._vega = None if kwargs is None else kwargs['vega'] if 'vega' in kwargs else None
        self._rho = None if kwargs is None else kwargs['rho'] if 'rho' in kwargs else None
        self._fee = 0 if kwargs is None else kwargs['fee'] if 'fee' in kwargs else 0

        self._trade_open_date = None
        self._trade_spot_price = None
        self._trade_price = None
        self._trade_close_date = None
        self._trade_close_price = None
        self._trade_dte = None
        self._position_type = None
        self._quantity = None
        self._total_fees = 0

        self._set_additional_fields(kwargs)

    def __repr__(self) -> str:
        return f'<{self._option_type.name} {self._ticker_symbol} {self.strike} ' \
            + f'{datetime.datetime.strftime(self.expiration, "%Y-%m-%d")}>'

    def _set_additional_fields(self, kwargs):
        """
        An internal method to set keyword arguments as attributes on the option object
        :param kwargs:
        :type: dict
        """
        additional_fields = {key: kwargs[key] for key in kwargs.keys() if key not in optional_fields}
        for key, value in additional_fields.items():
            setattr(self, key, value)

    def open_trade(self, quantity, incur_fees=True, *args, **kwargs):
        """
        Opens a trade with a given quantity

        :param quantity: quantity to open. Positive quantity will open long option.
            Negative quantity will open short option
        :type quantity: integer
        :param incur_fees: if True, fees will be incurred using the fee amount when option was created
        :type incur_fees: boolean
        :param args: arguments
        :type: list
        :param kwargs: keyword arguments
        :type: dictionary

        additional user-defined parameters passed as keyword arguments will be defined as attributes
        """
        if self._quote_date is None:
            raise ValueError("Cannot open a position that does not have price data")
        if self._trade_open_date is not None:
            raise ValueError("Cannot open position. A position is already open.")
        if (quantity is None) or not (isinstance(quantity, int)) or (quantity == 0):
            raise ValueError("Quantity must be a non-zero integer.")
        self._trade_open_date = self._quote_date
        self._trade_spot_price = self._spot_price
        self._trade_price = self._price
        self._trade_dte = self.dte()
        self._position_type = OptionPositionType.LONG if quantity > 0 else OptionPositionType.SHORT
        self._quantity = quantity

        self._set_additional_fields(kwargs)

        if incur_fees:
            self._incur_fees()

    def update(self, quote_date, spot_price, bid, ask, price, *args, **kwargs):
        """
        Updates price and underlying asset information for a given data date and/or time

        :param quote_date: data date for price information
        :type quote_date: datetime.datetime
        :param spot_price: price of underlying on quote_date
        :type spot_price: float
        :param bid: bid price
        :type bid: float
        :param ask: ask price
        :type ask: float
        :param price: calculated price based on mid-point between bid and ask
        :type price: float

        optional parameters: delta, theta, vega, gamma, iv, open_interest, rho, fee
        additional user-defined parameters passed as keyword arguments will be defined as attributes
        """
        if quote_date is None:
            raise ValueError("quote_date is required")
        if spot_price is None:
            raise ValueError("spot_price is required")
        if bid is None:
            raise ValueError("bid is required")
        if ask is None:
            raise ValueError("ask is required")
        if price is None:
            raise ValueError("price is required")
        if quote_date.date() > self._expiration.date():
            raise ValueError("Cannot update to a date past the option expiration")

        self._bid = bid
        self._ask = ask
        self._price = price
        self._quote_date = quote_date
        self._spot_price = spot_price
        self._open_interest = None if kwargs is None else kwargs['open_interest'] if 'open_interest' in kwargs else None
        self._iv = None if kwargs is None else kwargs['iv'] if 'iv' in kwargs else None
        self._delta = None if kwargs is None else kwargs['delta'] if 'delta' in kwargs else None
        self._gamma = None if kwargs is None else kwargs['gamma'] if 'gamma' in kwargs else None
        self._theta = None if kwargs is None else kwargs['theta'] if 'theta' in kwargs else None
        self._vega = None if kwargs is None else kwargs['vega'] if 'vega' in kwargs else None
        self._rho = None if kwargs is None else kwargs['rho'] if 'rho' in kwargs else None

        self._set_additional_fields(kwargs)

    def _incur_fees(self):
        """
        Calculates fees for a transaction and adds to the total fees
        :return: fees that were added to the option
        :rtype: float
        """
        fees = self._fee * abs(self._quantity)
        self._total_fees += fees
        return fees

    def get_closing_price(self):
        """
        :return: Determines the appropriate closing price for an option. If an option
        is expired, appropriate ITM and OTM prices will be calculated.
        If the bid is zero, the value it can be bought or sold, depending on whether the
        option is short or long, will be returned.

        The option will not be closed until the close_trade method is called.

        Closing price can only be calculated on an option that has an open trade
        :rtype: float
        """
        if self._trade_open_date is None:
            raise ValueError("Cannot determine closing price on option that has not been traded")
        price = decimalize_2(self._price)
        spot_price = decimalize_2(self._spot_price)
        close_price = None
        # check if option is expired (assume PM settled)
        if self.is_expired():
            if self.otm:  # OTM options have no value at expiration
                close_price = 0

            # ITM options value is the difference between the spot price and the strike price
            elif self.itm:  # ITM options only have intrinsic value at expiration
                if self._option_type == OptionType.CALL:
                    close_price = spot_price - self._strike
                elif self._option_type == OptionType.PUT:
                    close_price = self._strike - spot_price

        # get price, but if bid is zero, assume option cannot be sold to close for any amount
        # (LONG options must be sold to close).
        # if bid is zero, option can only be bought to close for the ask price
        # (SHORT options must be bought to close)
        else:  # option is not expired
            if self._bid == 0:
                if self._position_type == OptionPositionType.LONG:
                    close_price = 0
                elif self._position_type == OptionPositionType.SHORT:
                    close_price = self._ask
            else:
                close_price = price
        return float(close_price)

    def close_trade(self, incur_fees=True):
        """
        Calculates the closing price and sets the close date and price for the option
        :param incur_fees: if True, calculates the fees for the closing transaction
            and adds that to the total fees
        :return: the value of the option at the closing price
        :rtype: float
        """
        if self._trade_open_date is None:
            raise ValueError("Cannot close an option that has not been traded to open")
        if self._trade_close_date is not None:
            raise ValueError("Cannot close an option and is already closed")
        self._price = self.get_closing_price()
        self._trade_close_date = self._quote_date
        self._trade_close_price = self.get_closing_price()
        if incur_fees:
            self._incur_fees()
        closing_value = self._trade_close_price * 100 * self._quantity
        return closing_value

    def dte(self):
        """
        DTE is "days to expiration"
        :return: The number of days to the expiration for the current quote
        :rtype: int
        """
        if self._quote_date is None:
            return None
        dt_date = self._quote_date.date()
        time_delta = self._expiration.date() - dt_date
        return time_delta.days

    def is_expired(self):
        """
        Assumes the option is PM settled
        :return: True if option quote is at or exceeds the expiration date
        :rtype: bool
        """
        quote_date, expiration_date = self._quote_date.date(), self._expiration.date()
        quote_time, exp_time = self._quote_date.time(), datetime.time(16, 15)
        if (quote_date == expiration_date and quote_time >= exp_time) or (quote_date > expiration_date):
            return True
        else:
            return False

    def total_premium(self):
        """
        The value of the trade at opening. If the value is positive, that is a debit, and it will be taken
            from the account to open the trade. If the value is negative, that is a credit, and it will be credited
            to the account when the trade is opened.
        :return: The cost to open a trade, positive for a debit, negative for a credit
        :rtype: float
        """
        if self._trade_open_date is None:
            raise Exception("No trade has been opened.")
        trade_price = decimalize_2(self._trade_price)
        quantity = decimalize_0(self._quantity)
        value = trade_price * 100 * quantity
        return float(value)

    def current_gain_loss(self):
        """
        The current value is the difference in value between the trade open and the current quote.
        The value is determined by multiplying the price difference by the quantity and number
        of underlying units the option represents (100).
        :return: the current value of the trade
        :rtype: float
        """
        if self._trade_open_date is None:
            raise Exception("No trade has been opened.")
        trade_price = decimalize_2(self._trade_price)
        price = decimalize_2(self._price)
        quantity = decimalize_0(self._quantity)
        price_diff = price - trade_price
        value = price_diff * 100 * quantity
        return float(value)

    # def current_premium(self):
    #     price = decimalize_2(self._price)
    #     quantity = decimalize_0(self._quantity)
    #     premium = price * quantity
    #     return float(premium)

    def profit_loss_percent(self):
        """
        The percentage gain or loss based on the current price compared to the trade price of an option.
        :return: the percentage gain or loss
        :rtype: float
        """
        if self._trade_open_date is None:
            raise Exception("No trade has been opened.")
        trade_price = decimalize_4(self._trade_price)
        price = decimalize_4(self._price)
        quantity = decimalize_0(self._quantity)
        percent = ((price - trade_price) / trade_price) * int(quantity / abs(quantity))
        return float(decimalize_4(percent))

    def close_value(self):
        """
        The value of a closed option at closing.
        :return: The value of the closed option
        :rtype: object
        """
        if self._trade_open_date is None:
            raise Exception("No trade has been opened.")
        if self._trade_close_date is None:
            raise Exception("The open trade has not been closed.")
        close_value = self._trade_close_price * 100 * self._quantity
        return close_value

    @property
    def option_type(self):
        """
        The option can be a call or a put.
        :return: OptionType.CALL or OptionType.PUT
        """
        return self._option_type

    @property
    def option_id(self):
        """
        The unique identifier for an option
        :return: The option id that was set when the option was created
        :rtype: Any
        """
        return self._option_id

    @property
    def ticker_symbol(self):
        """
        The ticker symbol that was set when the option was created
        :return: ticker symbol
        :rtype: string
        """
        return self._ticker_symbol

    @property
    def strike(self):
        """
        The strike that was set when the option was created
        :return: strike
        :rtype: float
        """
        return self._strike

    @property
    def expiration(self):
        """
        The expiration that was set when the option was created
        :return: expiration
        :rtype: datetime.datetime
        """
        return self._expiration

    @property
    def bid(self):
        """
        :return: bid
        :rtype: float
        """
        return self._bid

    @property
    def ask(self):
        """
        :return: ask
        :rtype: float
        """
        return self._ask

    @property
    def price(self):
        """
        Price is a calculated field based on the mid-point between the bid and ask
        :return: price
        :rtype: float
        """
        return self._price

    @property
    def quote_date(self):
        """
        :return: current quote date for price and greeks
        :rtype: datetime.datetime
        """
        return self._quote_date

    @property
    def spot_price(self):
        """
        :return: current price of underlying asset
        :rtype: float
        """
        return self._spot_price

    @property
    def open_interest(self):
        """
        :return: open interest
        :rtype: integer
        """
        return self._open_interest

    @property
    def iv(self):
        """
        :return: implied volatility
        :rtype: float
        """
        return self._iv

    @property
    def delta(self):
        """
        :return: delta
        :rtype: float
        """
        return self._delta

    @property
    def gamma(self):
        """
        :return: gamma
        :rtype: float
        """
        return self._gamma

    @property
    def theta(self):
        """
        :return: theta
        :rtype: float
        """
        return self._theta

    @property
    def vega(self):
        """
        :return: vega
        :rtype: float
        """
        return self._vega

    @property
    def rho(self):
        """
        :return: rho
        :rtype: float
        """
        return self._rho

    @property
    def trade_price(self):
        """
        :return: This is the price at the time when the option was opened
        :rtype: float
        """
        return self._trade_price

    @property
    def trade_spot_price(self):
        """
        :return: The price of the underlying asset when the option was opened
        :rtype: float
        """
        return self._trade_spot_price

    @property
    def trade_open_date(self):
        """
        :return: The date/time when the option was opened
        :rtype: datetime.datetime
        """
        return self._trade_open_date

    @property
    def trade_close_date(self):
        """
        :return: The date/time when the option was closed
        :rtype: datetime.datetime
        """
        return self._trade_close_date

    @property
    def fee(self):
        """
        The base transaction fee for a quantity of one option for one transaction
        :return: fee
        :rtype: float
        """
        return self._fee

    @property
    def total_fees(self):
        """
        All the fees that have been incurred for this option
        :return: current fees
        :rtype: float
        """
        return self._total_fees

    @property
    def position_type(self):
        """
        The position type is determined when the option is opened. It is either long or short.
            An option is long if the quantity is positive. It is bought to open and sold to close.
            An option is long if the quantity is negative. It is sold to open and bought to close
        :return: OptionPositionType of LONG or SHORT
        :rtype: OptionPositionType
        """
        return self._position_type

    @property
    def quantity(self):
        """
        A positive quantity indicates a long position, and a negative quantity indicates a short position
        :return: quantity
        :rtype: integer
        """
        return self._quantity

    @property
    def trade_dte(self):
        """
        Trade DTE is days to expiration calculated from the trade open date
        :return: The number of days to expiration when the trade was opened
        :rtype: integer
        """
        return self._trade_dte

    @property
    def itm(self):
        """
        In the Money
        :return: ITM returns true if the option is "in the money" and false if the option is "out of the money".
            An option is ITM when the strike price has been exceeded by the price of the underlying.
            The intrinsic value is the value it will have at expiration if the price of the underlying
            does not change.
        :rtype: bool
        """
        itm = None

        if self._spot_price is not None and self._option_type == OptionType.PUT:
            itm = True if self._strike >= self._spot_price else False
        elif self._spot_price is not None and self._option_type == OptionType.CALL:
            itm = True if self._strike <= self._spot_price else False

        return itm

    @property
    def otm(self):
        """
        Out of the Money
        :return: OTM returns true if the option is "out of the money" and false if the option is "in the money".
            An option is OTM when an option has a strike price that the option has not
            reached. The option has no instrinsic value. If the underlying price
            does not change, the option will expire worthless.
        :rtype: bool
        """
        otm = None
        if self._spot_price is not None and self._option_type == OptionType.PUT:
            otm = True if self.strike < self.spot_price else False
        elif self._spot_price is not None and self._option_type == OptionType.CALL:
            otm = True if self.strike > self.spot_price else False

        return otm


