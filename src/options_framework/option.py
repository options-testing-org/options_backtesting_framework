from collections import namedtuple
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
import datetime
import numbers
import itertools

import pandas as pd
import numpy as np
from options_framework.option_types import OptionPositionType, OptionStatus
from options_framework.utils.helpers import decimalize_0, decimalize_2, decimalize_4
from options_framework.config import settings

from pydispatch import Dispatcher

TradeOpenInfo = namedtuple("TradeOpen", "option_id instance_id date quantity price premium fees spot_price")
TradeCloseInfo = namedtuple("TradeClose", "option_id instance_id date quantity price premium profit_loss profit_loss_percent fees spot_price")


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
    """The unique identifier of the option contract"""
    symbol: str = field(compare=True)
    """The ticker symbol"""
    strike: int | float = field(compare=True)
    """The option strike"""
    expiration: datetime.date = field(compare=True)
    """The expiration date"""
    option_type: str = field(compare=True)
    """Put or Call"""
    instance_id: int = field(init=False, default_factory=lambda counter=itertools.count(): next(counter))
    """internal counter to keep track of individual option instances"""
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
    user_defined: dict = field(default_factory=lambda: {}, compare=False)
    incur_fees: bool = field(default=True, compare=False)
    fee_per_contract: float = field(default=0.65, compare=False)

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
        self.price = round(self.price, 2)
        self.incur_fees = settings.get('incur_fees', True)
        self.fee_per_contract = settings.get('standard_fee', 0.65)

        # make sure the quote date is not past the expiration date
        if self.quote_datetime.date() > self.expiration:
            raise ValueError("Cannot create an option with a quote date past its expiration date")


    def __repr__(self) -> str:
        long_short = '' if self.position_type is None else f' {self.position_type.name}'
        return f'<{self.option_type.upper()}({self.option_id}) {self.symbol} {self.strike} ' \
            + f'{datetime.datetime.strftime(self.expiration, "%Y-%m-%d")}{long_short}>'

    def _incur_fees(self, *, quantity: int | Decimal) -> float:
        """
        Calculates fees for a transaction and adds to the total fees
        :return: fees that were added to the option
        :rtype: float
        """
        fee = decimalize_2(self.fee_per_contract)
        qty = decimalize_0(quantity)
        fees = fee * abs(qty)
        total_fees = decimalize_2(self.total_fees) + fees
        self.total_fees = float(total_fees)
        fees = float(fees)

        self.emit("fees_incurred", fees)
        #print(f'emit fees {self.option_id}')

        return fees

    def is_expired(self) -> bool:
        """
        Assumes the option is PM settled. Add the status OptionStatus.EXPIRED flag if the
        option is expired.
        """
        if OptionStatus.EXPIRED in self.status:
            return True
        if type(self.quote_datetime) == datetime.datetime:
            quote_date, quote_time = self.quote_datetime.date(), self.quote_datetime.time()
        else:
            message = f"Wrong format for option date. Must be python datetime.datetime. Date was provided in {type(self.quote_datetime)} format."
            raise ValueError(message)
        expiration_date, exp_time = self.expiration, datetime.time(16, 00)
        if ((quote_date > expiration_date) or (quote_date == expiration_date and quote_time >= exp_time)):
            self.status |= OptionStatus.EXPIRED
            _id = self.instance_id
            self.emit("option_expired", instance_id=_id)
            #print(f'emit expire {self.option_id}')
            return True
        return False

    def next(self, updates: dict):
        if self.option_id != updates['option_id']:
            raise ValueError("Option ID mismatch")

        self.quote_datetime = updates['quote_datetime']

        if self.is_expired():
            #self.close_trade(quantity=self.quantity)
            return

        self.spot_price = updates['spot_price']
        self.bid = float(decimalize_2(updates['bid']))
        self.ask = float(decimalize_2(updates['ask']))
        self.price = float(decimalize_2(updates['price']))

        self.delta = updates.get('delta', None)
        self.gamma = updates.get('gamma', None)
        self.theta = updates.get('theta', None)
        self.vega = updates.get('vega', None)
        self.rho = updates.get('rho', None)
        self.open_interest = updates.get('open_interest', None)
        self.volume = updates.get('volume', None)
        self.implied_volatility = updates.get('implied_volatility')

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

        # Quote sanity
        if self.bid is None or self.ask is None:
            raise ValueError(f"Missing bid/ask for {self.option_id} on {self.quote_datetime}")
        if self.bid > self.ask:
            raise ValueError(f"Crossed quote bid>ask for {self.option_id}: {self.bid}>{self.ask}")

        # calculate premium debit or credit. If this is a long position, the premium is a positive number.
        # If it is a short position, the premium is a negative number.
        if quantity > 0:
            fill_price = decimalize_2(self.ask)
            if fill_price <= 0:
                raise ValueError(f"Cannot open LONG with non-positive ask for {self.option_id}")
            premium = float(-fill_price * 100 * abs(quantity))  # cash outflow
            self.position_type = OptionPositionType.LONG
        else:
            fill_price = decimalize_2(self.bid)
            if fill_price <= 0:
                raise ValueError(f"Cannot open SHORT with non-positive bid for {self.option_id}")
            premium = float(+fill_price * 100 * abs(quantity))  # cash inflow
            self.position_type = OptionPositionType.SHORT

        for key, value in kwargs.items():
            self.user_defined[key] = value

        fees = 0
        if self.incur_fees:
            fees = self._incur_fees(quantity=quantity)
        trade_open_info = TradeOpenInfo(option_id=self.option_id,
                                        instance_id=self.instance_id,
                                        date=self.quote_datetime,
                                        quantity=int(quantity),
                                        price=float(price),
                                        premium=premium,
                                        fees=fees,
                                        spot_price=float(self.spot_price))

        self.trade_open_info = trade_open_info
        self.quantity = quantity
        self.status = OptionStatus.TRADE_IS_OPEN

        self.emit("open_transaction_completed", trade_open_info)
        #print(f'emit open {self.option_id}')

        return trade_open_info

    def close_trade(self, *, quantity: int | None = None, **kwargs: dict) -> TradeCloseInfo:
        """
        Calculates the closing price and sets the close date, price and profit/loss info for the
        quantity closed.
        :param quantity: If a quantity is provided, only that quantity will be closed.
        :return: the profit/loss of the closed quantity of the trade
        :rtype: float
        """

        # if trade has already been closed, just return the close info
        if OptionStatus.TRADE_IS_CLOSED in self.status:
            return self.trade_close_info

        if OptionStatus.TRADE_IS_OPEN not in self.status:
            raise ValueError("Cannot close an option that is not open.")

        pos_qty = int(self.quantity)
        if pos_qty == 0:
            raise ValueError("No open quantity.")

        # how many contracts to close (always positive)
        if close_qty is None:
            close_qty = abs(pos_qty)
        if close_qty <= 0:
            raise ValueError("close_qty must be positive.")
        if close_qty > abs(pos_qty):
            raise ValueError("Quantity to close is greater than the current open quantity.")

        # determine executable close price and action sign
        if self.position_type == OptionPositionType.LONG:
            close_price = decimalize_2(self.bid)  # sell to close on bid
            action_qty = -close_qty  # sell
        else:  # SHORT
            close_price = decimalize_2(self.ask)  # buy to close on ask
            action_qty = +close_qty  # buy

        if close_price <= 0:
            raise ValueError(f"Non-positive close price for {self.option_id}.")

        open_price = decimalize_2(self.trade_open_info.price)
        close_premium = decimalize_2(close_price * 100 * action_qty * -1)

        # PnL for this close lot:
        # Long: (close - open)*100*close_qty
        # Short: (open - close)*100*close_qty
        if self.position_type == OptionPositionType.LONG:
            profit_loss = decimalize_2((close_price - open_price) * 100 * close_qty)
        else:
            profit_loss = decimalize_2((open_price - close_price) * 100 * close_qty)

        ratio = (close_price - open_price) / open_price if open_price > 0 else 0
        profit_loss_percent = decimalize_4(ratio) * (quantity * -1 / abs(quantity))

        fees = self._incur_fees(quantity=close_qty) if self.incur_fees else 0

        # Update position quantity
        if self.position_type == OptionPositionType.LONG:
            self.quantity = pos_qty - close_qty
        else:
            self.quantity = pos_qty + close_qty

            # Save record with *close_qty* (positive) + side stored separately is cleaner
            rec = TradeCloseInfo(
                option_id=self.option_id,
                instance_id=self.instance_id,
                date=self.quote_datetime,
                quantity=close_qty,  # positive count
                price=float(close_price),
                premium=float(close_premium),
                profit_loss=float(profit_loss),
                profit_loss_percent=0.0,  # compute from abs(open premium) if you want
                fees=fees,
                spot_price=float(self.spot_price),
            )
            self.trade_close_records.append(rec)

        for key, value in kwargs.items():
            self.user_defined[key] = value

        if self.quantity == 0:
            self.status &= ~OptionStatus.TRADE_IS_OPEN
            self.status &= ~OptionStatus.TRADE_PARTIALLY_CLOSED
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
        # Expired: intrinsic only
        if OptionStatus.EXPIRED in self.status:
            if self.option_type == "call":
                return max(spot - strike, 0.0)
            else:
                return max(strike - spot, 0.0)

        # Not expired: executable close depends on position side
        bid = float(self.bid)
        ask = float(self.ask)

        # Basic quote sanity
        if bid < 0 or ask < 0 or (ask > 0 and bid > ask):
            raise ValueError(f"Bad quote bid/ask for {self.option_id}: bid={bid}, ask={ask}")

        if self.position_type == OptionPositionType.LONG:
            # sell to close on bid
            if bid <= 0:
                # No executable bid -> treat as missing quote, not worth 0
                raise ValueError(f"Missing/zero bid for LONG option close: {self.option_id}")
            return bid

        elif self.position_type == OptionPositionType.SHORT:
            # buy to close on ask
            if ask <= 0:
                raise ValueError(f"Missing/zero ask for SHORT option close: {self.option_id}")
            return ask

        else:
            raise ValueError("position_type must be LONG or SHORT before closing")

    def _calculate_trade_close_info(self) -> None:
        if not self.trade_close_records:
            return None
        # date quantity price premium profit_loss fees
        records = self.trade_close_records
        date = records[-1].date
        quantity = decimalize_0(sum(decimalize_0(x.quantity) for x in records))
        trade_open_premium = decimalize_2(self.trade_open_info.premium)
        # Weighted average price of close transactions
        notional = sum(decimalize_2(r.price) * decimalize_0(r.quantity) for r in records)
        price = decimalize_2(notional / quantity)

        premium = decimalize_2(sum(decimalize_2(r.premium) for r in records))

        profit_loss = decimalize_2(sum(decimalize_2(r.profit_loss) for r in records))
        fees = sum(r.fees for r in records)

        open_premium = decimalize_2(self.trade_open_info.premium)
        profit_loss_percent = decimalize_4(profit_loss / abs(open_premium)) if open_premium else 0.0

        self.trade_close_info = TradeCloseInfo(
            option_id=self.option_id,
            instance_id=self.instance_id,
            date=date,
            quantity=int(quantity),
            price=float(price),
            premium=float(premium),
            profit_loss=float(profit_loss),
            profit_loss_percent=float(profit_loss_percent),
            fees=fees,
            spot_price=float(self.spot_price),
        )


    def get_dte(self) -> int:
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
        percent = float(decimalize_4(percent))
        return percent

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

        profit_loss_percent = float(profit_loss_percent)

        return round(profit_loss_percent, 4)

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
