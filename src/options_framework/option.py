from collections import namedtuple
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
import datetime
import numbers

import pandas as pd
import numpy as np
from options_framework.option_types import OptionPositionType, OptionStatus
from options_framework.utils.helpers import decimalize_0, decimalize_2, decimalize_4
from options_framework.config import settings

from pydispatch import Dispatcher

TradeOpenInfo = namedtuple("TradeOpen", "option_id date quantity price premium fees spot_price")
TradeCloseInfo = namedtuple("TradeClose", "option_id date quantity price premium profit_loss profit_loss_percent fees spot_price")


@dataclass(repr=False, kw_only=True, slots=True)
class Option(Dispatcher):
    """
    The Option class holds all the values that pertain to a single option. The option can have just basic option information
    without any price or other current values. These values are id, symbol, strike, expiration and option type.
    Quote information can be set when the option is created and also using the update method.
    The trade_open and trade_close methods are used to capture open/close price and dates.
    """

    _events_ = ["open_transaction_completed", "close_transaction_completed", "option_expired", "fees_incurred"]


    # immutable fields
    option_id: str | int = field(compare=True)
    """The unique id of the option"""
    symbol: str = field(compare=True)
    """The ticker symbol"""
    strike: int | float = field(compare=True)
    """The option strike"""
    expiration: datetime.date = field(compare=True)
    """The expiration date"""
    option_type: str = field(compare=True)
    """Put or Call"""
    quote_datetime: datetime.datetime = field(default=None, compare=False)
    """The date of the current price information: spot_price, bid, ask, and price"""
    spot_price: int | float = field(default=None, compare=False)
    """The current price of the underlying asset"""
    bid: float | int = field(default=None, compare=False)
    """The current bid price of the option"""
    ask: float | int = field(default=None, compare=False)
    """The current ask price of the option"""
    price: float | int = field(default=None, compare=False)
    """The price is the mid-point between the bid and ask"""
    status: OptionStatus = field(init=False, default=OptionStatus.INITIALIZED, compare=False)
    """
    The option status tracks the life cycle of an option. This is a flag enum, so there can be 
    more than one status. To find out about a status, such as if the option is currently
    opened or closed, use the "in" keyword.
    
    Example: OptionStatus.TRADE_IS_OPEN in option.status
    
    OptionStatus.INITIALIZED: Option has been creatd, but has not been opened and added to a portfolio
    OptionStatus.TRADE_IS_OPEN: A trade is currently open.
    OptionStatus.TRADE_PARTIALLY_CLOSED: Some of the contracts were closed, but the trade is still open.
    In this state, the status will have both TRADE_IS_OPEN and TRADE_PARTIALLY_CLOSED statuses
    OptionStatus.TRADE_IS_CLOSED: All contracts have been closed. The TRADE_IS_OPEN and TRADE_PARTIALLY_CLOSED
    statuses will be removed.
    OptionStatus.EXPIRED: This status is added when an option reaches its expiration.
    """
    quantity: Optional[int] = field(init=False, default=0, compare=False)
    """The current open quantity"""
    total_fees: Optional[int | float] = field(init=False, default=0, compare=False)
    """The total accumulated fees"""
    position_type: Optional[OptionPositionType] = field(init=False, default=None, compare=False)
    """Debit or Credit"""
    trade_open_info: Optional[TradeOpenInfo] = field(init=False, default=None, compare=False)
    """The information about the trade open: date, quantity, price, premium, and fees"""
    trade_close_info: Optional[TradeCloseInfo] = field(init=False, default=None, compare=False)
    """
    The weighted average information about the trade close transactions: date, quantity price, profit_loss, 
    profit_loss_percent, and fees
    """
    trade_close_records: Optional[list] = field(init=False, default_factory=list, compare=False)
    """The trade close information for each closing transaction"""

    # these fields can be updated directly
    delta: Optional[float] = field(default=None, compare=False)
    gamma: Optional[float] = field(default=None, compare=False)
    theta: Optional[float] = field(default=None, compare=False)
    vega: Optional[float] = field(default=None, compare=False)
    rho: Optional[float] = field(default=None, compare=False)
    open_interest: Optional[int] = field(default=None, compare=False)
    volume: Optional[int] = field(default=None, compare=False)
    implied_volatility: Optional[float] = field(default=None, compare=False)
    update_cache: list | None = field(default_factory=list, compare=False)
    user_defined: dict = field(default_factory=lambda: {}, compare=False)

    def __post_init__(self):
        # check for required fields
        if self.option_id is None:
            raise ValueError("option_id cannot be None")
        if self.symbol is None:
            raise ValueError("symbol cannot be None")
        if self.strike is None:
            raise ValueError("strike cannot be None")
        if self.expiration is None:
            raise ValueError("expiration cannot be None")
        if self.option_type is None:
            raise ValueError("option_type cannot be None")
        if self.quote_datetime is None:
            raise ValueError("quote_datetime cannot be None")
        elif type(self.quote_datetime) != datetime.datetime and type(self.quote_datetime) != pd.Timestamp:
            raise ValueError("quote datetime must be python datetime.datetime or pandas Timestamp")
        if self.spot_price is None:
            raise ValueError("spot_price cannot be None")
        if self.bid is None:
            raise ValueError("bid cannot be None")
        if self.ask is None:
            raise ValueError("ask cannot be None")
        if self.price is None:
            raise ValueError("price cannot be None")

        # make sure the quote date is not past the expiration date
        if self.quote_datetime.date() > self.expiration:
            raise ValueError("Cannot create an option with a quote date past its expiration date")

    def __repr__(self) -> str:
        return f'<{self.option_type.upper()}({self.option_id}) {self.symbol} {self.strike} ' \
            + f'{datetime.datetime.strftime(self.expiration, "%Y-%m-%d")}>'

    def _incur_fees(self, *, quantity: int | Decimal) -> float:
        """
        Calculates fees for a transaction and adds to the total fees
        :return: fees that were added to the option
        :rtype: float
        """
        fee = decimalize_2(settings['standard_fee'])
        qty = decimalize_0(quantity)
        fees = fee * abs(qty)
        total_fees = decimalize_2(self.total_fees) + fees
        self.total_fees = float(total_fees)
        fees = float(fees)

        self.emit("fees_incurred", fees)
        #print(f'emit fees {self.option_id}')

        return fees

    def _check_expired(self) -> bool:
        """
        Assumes the option is PM settled. Add the status OptionStatus.EXPIRED flag if the
        option is expired.
        """
        if OptionStatus.EXPIRED in self.status:
            return True
        if type(self.quote_datetime) == datetime.datetime or type(self.quote_datetime) == pd.Timestamp:
            quote_date, quote_time = self.quote_datetime.date(), self.quote_datetime.time()
        else:
            message = f"Wrong format for option date. Must be python datetime.datetime. Date was provided in {type(self.quote_datetime)} format."
            raise ValueError(message)
        expiration_date, exp_time = self.expiration, datetime.time(16, 15)
        #quote_time, exp_time = self.quote_datetime.time(), datetime.time(16, 15)
        if ((quote_date > expiration_date) or (quote_date == expiration_date and quote_time >= exp_time)):
            self.status |= OptionStatus.EXPIRED
            self.emit("option_expired", self.option_id)
            #print(f'emit expire {self.option_id}')
            self.update_cache = None
            return True
        return False

    def next_update(self, quote_datetime: datetime.datetime):
        self.quote_datetime = quote_datetime
        if self._check_expired():
            return
        try:
            update_values = next(x for x in self.update_cache if x['quote_datetime'] == quote_datetime) #self.update_cache[self.update_cache['quote_datetime'] == quote_datetime]
            #values = list(np.array(update_row)[0])
            # update_fields = [f for f in update_row.columns]
            # update_values = dict(zip(update_fields, values))
            self.update_cache = [x for x in self.update_cache if x['quote_datetime'] > quote_datetime]
            #self.update_cache[self.update_cache['quote_datetime'] > quote_datetime] # drop row after updating
        except KeyError as e:
            return

        self.spot_price = update_values['spot_price']
        self.bid = float(decimalize_2(update_values['bid']))
        self.ask = float(decimalize_2(update_values['ask']))
        self.price = float(decimalize_2(update_values['price']))

        #if 'delta' in update_fields:
        self.delta = update_values['delta']
        #if 'gamma' in update_fields:
        self.gamma = update_values['gamma']
        #if 'theta' in update_fields:
        self.theta = update_values['theta']
        #if 'vega' in update_fields:
        self.vega = update_values['vega']
        #if 'rho' in update_fields:
        self.rho = update_values['rho']
        #if 'open_interest' in update_fields:
        self.open_interest = update_values['open_interest']
        #if 'volume' in update_fields:
        self.volume = update_values['volume']
        #if 'implied_volatility' in update_fields:
        self.implied_volatility = update_values['implied_volatility']

    def open_trade(self, *, quantity: int, **kwargs: dict) -> TradeOpenInfo:
        """
        Opens a trade with a given quantity. Returns the premium amount of the trade.
        The premium is the cost to open the trade.
        A positive number for quantity opens a long position, which returns a positive
        amount for the premium. If the quantity is negative, a short position is
        opened, and premium amount is negative.

        :param quantity: quantity to open. Positive quantity will open long option.
            Negative quantity will open short option
        :type quantity: integer
        :type: list
        :param kwargs: keyword arguments
        :type: dictionary
        :return: Information about the opening transaction: date, quantity, price, premium and fees
        :rtype: float

        additional keyword arguments are added to the user_defined list of values
        """
        if OptionStatus.TRADE_IS_OPEN in self.status:
            raise ValueError(f"Cannot open position. A position is already open. ({self.symbol})")
        if (quantity is None) or not (isinstance(quantity, numbers.Number)) or (quantity == 0) or (quantity != int(quantity)):
            raise ValueError(f"Quantity must be a non-zero integer. ({self.symbol}) Quantity: {quantity}")
        quantity = int(quantity)

        # calculate premium debit or credit. If this is a long position, the premium is a positive number.
        # If it is a short position, the premium is a negative number.
        price = decimalize_2(self.price)
        if price == 0:
            raise Exception(f"Option price is zero {self.symbol} ({self.option_id}). Cannot open this option.")
        quantity = decimalize_0(quantity)
        if settings['apply_slippage_entry']:
            if quantity > 0:
                price -= self.slippage
            else:
                price += self.slippage
        premium = float(price * 100 * quantity)
        price = float(price)
        quantity = int(quantity)

        for key, value in kwargs.items():
            self.user_defined[key] = value

        fees = 0
        if settings['incur_fees']:
            fees = self._incur_fees(quantity=quantity)
        trade_open_info = TradeOpenInfo(option_id=self.option_id, date=self.quote_datetime, quantity=quantity,
                                        price=price,
                                        premium=premium,
                                        fees=fees,
                                        spot_price=float(self.spot_price))
        self.trade_open_info = trade_open_info
        self.position_type = OptionPositionType.LONG if quantity > 0 else OptionPositionType.SHORT
        self.quantity = quantity
        self.status |= OptionStatus.TRADE_IS_OPEN

        self.emit("open_transaction_completed", trade_open_info)
        #print(f'emit open {self.option_id}')

        return trade_open_info

    def close_trade(self, *, quantity: int, **kwargs: dict) -> TradeCloseInfo:
        """
        Calculates the closing price and sets the close date, price and profit/loss info for the
        quantity closed.
        :param quantity: If a quantity is provided, only that quantity will be closed.
        :return: the profit/loss of the closed quantity of the trade
        :rtype: float
        """
        if OptionStatus.TRADE_IS_OPEN not in self.status:
            raise ValueError("Cannot close an option that is not open.")

        if quantity is None:
            quantity = decimalize_0(self.quantity) * -1
        elif not (isinstance(quantity, numbers.Number)) or (quantity == 0):
            raise ValueError("Must supply a non-zero quantity.")
        # elif self._position_type == OptionPositionType.LONG and quantity + self._quantity - closed_quantity:
        #     raise ValueError("Quantity to close is greater than the current open quantity.")
        elif quantity < 0 and self.position_type == OptionPositionType.LONG:
            raise ValueError(
                "This is a long option position. The quantity to close should be a positive number.")
        elif quantity > 0 and self.position_type == OptionPositionType.SHORT:
            raise ValueError(
                "This is a short option position. The quantity should be a negative number.")
        elif ((self.position_type == OptionPositionType.LONG) and quantity > self.quantity) \
                or ((self.position_type == OptionPositionType.SHORT) and quantity < self.quantity):
            raise ValueError("Quantity to close is greater than the current open quantity.")
        else:
            quantity = decimalize_0(quantity) * -1

        close_price = decimalize_2(self.get_closing_price())
        if settings['apply_slippage_exit']:
            if not OptionStatus.EXPIRED in self.status:
                slippage = settings['slippage']
                if self.trade_open_info.quantity > 0:
                    close_price += close_price * decimalize_2(slippage)
                elif self.trade_open_info.quantity < 0:
                    close_price -= close_price * decimalize_2(slippage)

        open_price = decimalize_2(self.trade_open_info.price)
        premium = decimalize_2(close_price) * 100 * quantity*-1
        profit_loss = (open_price * 100 * quantity) - (close_price * 100 * quantity)
        ratio = (close_price - open_price) / open_price if open_price > 0 else 0
        profit_loss_percent = decimalize_4(ratio) * (quantity * -1 / abs(quantity))

        fees = 0
        if settings['incur_fees']:
            fees = self._incur_fees(quantity=abs(quantity))

        # date quantity price premium profit_loss fees
        trade_close_record = TradeCloseInfo(option_id=self.option_id, date=self.quote_datetime, quantity=int(quantity),
                                            price=float(close_price),
                                            premium=float(premium),
                                            profit_loss=float(profit_loss),
                                            profit_loss_percent=float(profit_loss_percent),
                                            fees=fees,
                                            spot_price=float(self.spot_price),)
        self.trade_close_records.append(trade_close_record)
        self.quantity = self.quantity + int(quantity)

        for key, value in kwargs.items():
            self.user_defined[key] = value

        if self.quantity == 0:
            self.status &= ~OptionStatus.TRADE_IS_OPEN
            self.status |= OptionStatus.TRADE_IS_CLOSED
            self.price = float(close_price)
        else:
            self.status |= OptionStatus.TRADE_PARTIALLY_CLOSED

        self._calculate_trade_close_info()
        self.emit("close_transaction_completed", trade_close_record)
        #print(f'emit close {self.option_id}')

        return trade_close_record

    def get_closing_price(self) -> float:
        """
        :return: Determines the appropriate closing price for an option. If an option
        is expired, appropriate ITM and OTM prices will be calculated.
        If the bid is zero, the value it can be bought or sold, depending on whether the
        option is short or long, will be returned.

        The option will not be closed until the close_trade method is called.

        Closing price can only be calculated on an option that has an open trade
        :rtype: float
        """
        if not (OptionStatus.TRADE_IS_OPEN in self.status or OptionStatus.TRADE_IS_CLOSED in self.status):
            raise ValueError("Cannot determine closing price on option that does not have an opening trade")
        price = decimalize_2(self.price)
        spot_price = decimalize_2(self.spot_price)
        strike = decimalize_2(self.strike)
        close_price = None
        # check if option is expired (assume PM settled)
        # If an option is expired, the price in the data may not match what the actual
        # settlement price of the option. An expired option's value is always
        # its intrinsic value. An out-of-the-money has no intrinsic value,
        # therefore its expiry price is zero.
        # If an option expires in the money, its value is equal to its intrinsic value.
        # Just calculate the intrinsic value and return that price.
        if OptionStatus.EXPIRED in self.status:
            if self.otm():  # OTM options have no value at expiration
                close_price = 0

            # ITM options value is the difference between the spot price and the strike price
            elif self.itm():  # ITM options only have intrinsic value at expiration
                if self.option_type == 'call':
                    close_price = spot_price - strike
                elif self.option_type == 'put':
                    close_price = strike - spot_price

        # Normally, the option price is assumed to be halfway between the bid and ask
        # When the bid is zero, it implies that there are no buyers, and only sellers at the ask price
        # Therefore, the option can only be bought at the ask and cannot be sold at any price
        # LONG options must be sold to close. Therefore, if the bid is zero,
        # the option is worthless since it cannot be sold.
        # SHORT options must be bought to close. If the bid is zero,
        # the option can only be bought to close for the ask price
        #
        # If the bid is not zero, then the price is the mid-point between the bid and ask
        else:  # option is not expired
            if self.bid == 0:
                # bid is zero, option is long. Cannot be sold to close, therefore it is worthless
                if self.position_type == OptionPositionType.LONG:
                    close_price = 0
                # bid is zero, option is short. The other side of this transaction holds a long option,
                # which is worthless. People will always take free money for something that is worthless,
                # so the option can be bought to close for the ask price.
                elif self.position_type == OptionPositionType.SHORT:
                    close_price = self.ask
            else:
                close_price = price
        return float(close_price)

    def _calculate_trade_close_info(self) -> None:
        if not self.trade_close_records:
            return None
        # date quantity price premium profit_loss fees
        records = self.trade_close_records
        date = records[-1].date
        quantity = decimalize_0(sum(decimalize_0(x.quantity) for x in records))
        trade_open_premium = decimalize_2(self.trade_open_info.premium)
        price = decimalize_2(sum((decimalize_2(x.price) * decimalize_0(x.quantity)) / quantity for x in records))
        premium = price * 100 * quantity*-1
        profit_loss = sum(decimalize_2(x.profit_loss) for x in records)
        profit_loss_percent = decimalize_4(profit_loss / trade_open_premium) * (quantity * -1 / abs(quantity))
        fees = sum(x.fees for x in records)

        trade_close = TradeCloseInfo(option_id=self.option_id, date=date, quantity=int(quantity), price=float(price),
                                     premium=float(premium),
                                     profit_loss=float(profit_loss),
                                     profit_loss_percent=float(profit_loss_percent),
                                     fees=fees,
                                     spot_price=float(self.spot_price))

        self.trade_close_info = trade_close

    def dte(self) -> int:
        """
        DTE is "days to expiration"
        :return: The number of days to the expiration for the current quote
        :rtype: int
        """

        dt_date = self.quote_datetime.date()
        time_delta = self.expiration - dt_date
        return time_delta.days

    @property
    def current_value(self) -> float:
        current_price = decimalize_2(self.price)
        quantity = decimalize_0(self.quantity)
        current_value = current_price * 100 * quantity
        return float(current_value)

    @property
    def trade_value(self) -> float:
        price = self.trade_price
        trade_price = decimalize_2(price)
        quantity = self.quantity if self.status == OptionStatus.INITIALIZED else self.trade_open_info.quantity
        quantity = decimalize_0(quantity)
        trade_value = trade_price * 100 * quantity
        return float(trade_value)

    @property
    def trade_price(self) -> float:
        return self.price if self.status == OptionStatus.INITIALIZED else self.trade_open_info.price

    def get_unrealized_profit_loss(self) -> float:
        """
        Returns the current unrealized profit/loss. This is the difference in value between
        the trade open and the current quote.
        The value is determined by multiplying the price difference by the quantity and number
        of underlying units the option represents (100).
        This method uses the current price of the option. This may be different from the closing
        price which considers other factors such as expiration and intrinsic value.
        :return: the current value of the trade
        :rtype: float
        """
        if OptionStatus.TRADE_IS_OPEN not in self.status and OptionStatus.TRADE_IS_CLOSED not in self.status:
            raise Exception("This option has no transactions.")

        trade_price = decimalize_2(self.trade_open_info.price)
        current_price = decimalize_2(self.price)
        open_quantity = decimalize_0(self.quantity)
        trade_premium = trade_price * 100 * open_quantity
        current_premium = current_price * 100 * open_quantity
        current_value = current_premium - trade_premium
        return float(current_value)

    def get_profit_loss(self) -> float:
        """
        Returns the total realized and unrealized profit/loss.
        :return: Returns the total profit/loss for both open and closed contracts.
        :rtype: float
        """
        if OptionStatus.TRADE_IS_OPEN not in self.status and OptionStatus.TRADE_IS_CLOSED not in self.status:
            raise Exception("This option has not been traded.")

        unrealized_pnl = self.get_unrealized_profit_loss()
        # if no contracts were closed, this is just the open pnl
        if not self.trade_close_records:
            return unrealized_pnl
        realized_pnl = sum(x.profit_loss for x in self.trade_close_records)

        total_profit_loss = unrealized_pnl + realized_pnl
        return total_profit_loss

    def get_unrealized_profit_loss_percent(self) -> float:
        """
        Returns the unrealized profit/loss percent.
        The percentage gain or loss based on the current price compared to the trade price of an option.
        :return: the percentage gain or loss
        :rtype: float
        """
        if OptionStatus.TRADE_IS_CLOSED in self.status:
            return 0.0

        if OptionStatus.TRADE_IS_OPEN not in self.status:
            raise Exception("This option has no transactions.")

        trade_price = decimalize_4(self.trade_open_info.price)
        current_price = decimalize_4(self.price)
        open_quantity = decimalize_0(self.quantity)
        percent = ((current_price - trade_price) / trade_price) * (open_quantity / abs(open_quantity))
        return float(decimalize_4(percent))

    def get_profit_loss_percent(self) -> float:
        if OptionStatus.TRADE_IS_OPEN not in self.status and OptionStatus.TRADE_IS_CLOSED not in self.status:
            raise Exception("This option has not been traded.")

        current_price = decimalize_2(self.price)
        open_quantity = decimalize_0(self.quantity)
        opening_trade_value = decimalize_2(self.trade_open_info.premium)
        closed_contracts_value = sum(decimalize_2(x.price) * 100 * decimalize_0(x.quantity) * -1
                                     for x in self.trade_close_records)
        open_contracts_value = current_price * 100 * open_quantity
        value_of_trade = open_contracts_value + closed_contracts_value
        profit_loss_percent = (decimalize_4((value_of_trade - opening_trade_value) / opening_trade_value))
        if self.position_type == OptionPositionType.SHORT:
            profit_loss_percent *= -1

        return float(profit_loss_percent)

    def get_days_in_trade(self) -> int:

        # if the trade has any open contracts, use current quote date.
        # if the trade is closed, then use the latest close date.
        if OptionStatus.TRADE_IS_OPEN in self.status:
            dt_date = self.quote_datetime.date()
        elif OptionStatus.TRADE_IS_CLOSED in self.status:
            dt_date = self.trade_close_records[-1].date.date()
        else:
            raise Exception("No trade has been opened.")

        time_delta = dt_date - self.trade_open_info.date.date()
        return time_delta.days

    def itm(self) -> bool :
        """
        In the Money
        A call option is in the money when the current price is higher than or equal to the strike price
        A put option is in the money when the current price is lower than or equal to the strike price
        Returns a boolean value indicating whether the option is currently in the money.
        :return: Returns a boolean value indicating whether the option is currently in the money.
        :rtype: bool
        """

        if self.option_type == 'call':
            return True if self.spot_price >= self.strike else False
        elif self.option_type == 'put':
            return True if self.spot_price <= self.strike else False

    def otm(self) -> bool:
        """
        Out of the Money
        A call option is out of the money when the current price is lower than the spot price.
        A put option is out of the money when the current price is greater than the spot price.
        :return: Returns a boolean value indicating whether the option is currently out of the money.
        :rtype: bool
        """
        if self.option_type == 'call':
            return True if self.spot_price < self.strike else False
        elif self.option_type == 'put':
            return True if self.spot_price > self.strike else False

    def get_fees(self):
        if self.status == OptionStatus.INITIALIZED:
            return 0
        open_fees = self.trade_open_info.fees
        if OptionStatus.TRADE_PARTIALLY_CLOSED in self.status or OptionStatus.TRADE_IS_CLOSED in self.status:
            close_fees = self.trade_close_info.fees
        else:
            close_fees = 0

        return open_fees + close_fees
