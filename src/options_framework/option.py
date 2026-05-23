from collections import namedtuple
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from pathlib import Path
import datetime
import numbers
import itertools

import pandas as pd
import numpy as np
from options_framework.option_types import OptionPositionType, OptionStatus
from options_framework.utils.helpers import decimalize_0, decimalize_2, decimalize_4
from options_framework.utils.options_db import OptionsDB, IntradayOptionsDB
from options_framework.config import settings

from pydispatch import Dispatcher

TradeOpenInfo = namedtuple("TradeOpen", "option_id instance_id date quantity price premium fees spot_price")
TradeCloseInfo = namedtuple("TradeClose", "option_id instance_id date quantity price premium profit_loss profit_loss_percent fees spot_price")


@dataclass(repr=False, kw_only=True)
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
    """The weighted average information about the trade open: date, quantity, price, premium, and fees"""
    trade_open_records: Optional[list] = field(init=False, default_factory=list, compare=False)
    """The trade open information for each opening transaction"""
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
    incur_fees: Optional[bool] = field(default=None, compare=False)
    fee_per_contract: Optional[float] = field(default=None, compare=False)
    updates: dict = field(default_factory=lambda: {}, compare=False)

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
        if isinstance(self.expiration, datetime.datetime):
            raise TypeError("expiration must be datetime.date, not datetime.datetime.")
        if not isinstance(self.expiration, datetime.date):
            raise TypeError(
                f"expiration must be datetime.date, got {type(self.expiration).__name__}"
            )
        if self.option_type is None:
            raise ValueError("option_type cannot be None")
        if self.quote_datetime is None:
            raise ValueError("quote_datetime cannot be None")
        if isinstance(self.quote_datetime, pd.Timestamp):
            self.quote_datetime = self.quote_datetime.to_pydatetime()
        elif not isinstance(self.quote_datetime, datetime.datetime):
            raise TypeError(
                f"quote_datetime must be datetime.datetime or pd.Timestamp, got {type(self.quote_datetime).__name__}"
            )
        if self.spot_price is None:
            raise ValueError("spot_price cannot be None")
        if self.bid is None:
            raise ValueError("bid cannot be None")
        if self.ask is None:
            raise ValueError("ask cannot be None")
        if self.price is None:
            raise ValueError("price cannot be None")
        self.price = round(self.price, 2)

        if self.incur_fees is None:
            self.incur_fees = settings.get('incur_fees', True)
        if self.fee_per_contract is None:
            self.fee_per_contract = settings.get('standard_fee', 0.65)

        # make sure the quote date is not past the expiration date
        if self.quote_datetime.date() > self.expiration:
            raise ValueError("Cannot create an option with a quote date past its expiration date")

        # option was successfully instantiated
        data_frequency = settings['data_frequency']
        if data_frequency == 'daily':
            self.db = OptionsDB.from_symbol(self.symbol)
        else:
            self.db = IntradayOptionsDB.from_symbol(self.symbol)
        pass


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
        if isinstance(self.quote_datetime, (datetime.datetime, pd.Timestamp)):
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

    def _next(self, quote_datetime: datetime.datetime) -> None:
        """Advance the option's clock to quote_datetime and refresh its quote
            state from the pre-loaded updates.

            Side effects:
              - Always updates self.quote_datetime (after normalization).
              - If the new datetime triggers expiration, sets OptionStatus.EXPIRED
                and emits option_expired; no further state changes.
              - If an update exists at quote_datetime, refreshes spot_price, bid,
                ask, price, greeks, open_interest, volume, and implied_volatility.
              - If no update exists at quote_datetime, leaves market-data fields
                unchanged (silent no-op on the price side, but quote_datetime
                still advances).

            :param quote_datetime: The new clock value. Must be datetime.datetime
                or pd.Timestamp (normalized to datetime.datetime internally).
            :raises TypeError: if quote_datetime is not a datetime or Timestamp.
            """
        if isinstance(quote_datetime, pd.Timestamp):
            quote_datetime = quote_datetime.to_pydatetime()
        elif not isinstance(quote_datetime, datetime.datetime):
            raise TypeError(
                f"quote_datetime must be datetime.datetime or pd.Timestamp, got {type(quote_datetime).__name__}")
        self.quote_datetime = quote_datetime
        if self.is_expired():
            return

        updates = self.updates.get(quote_datetime, None)
        if updates is None:
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


    def _open_trade(self, *, quantity: int, **kwargs: dict) -> TradeOpenInfo:
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
        if OptionStatus.TRADE_IS_CLOSED in self.status:
            raise ValueError(f"Cannot open a closed position. ({self.symbol})")
        if (quantity is None) or not (isinstance(quantity, numbers.Integral)) or (quantity == 0) or (quantity != int(quantity)):
            raise ValueError(f"Quantity must be a non-zero integer. ({self.symbol}) Quantity: {quantity}")
        if (self.quantity != 0) and (quantity * self.quantity < 0):
            direction = 'positive' if quantity > 0 else 'negative'
            raise ValueError(f"Quantity cannot be in the opposite direction to scale in. Quantity entered is {direction}. It must match the existing {self.position_type.name} position.")
        quantity = int(quantity)

        # Quote sanity
        if self.bid is None or self.ask is None:
            raise ValueError(f"Missing bid/ask for {self.option_id} on {self.quote_datetime}")
        if self.bid > self.ask:
            raise ValueError(f"Crossed quote bid>ask for {self.option_id}: {self.bid}>{self.ask}")

        fill_factor = settings.get('fill_factor', 0)

        # calculate premium debit or credit. If this is a long position, the premium is a positive number.
        # If it is a short position, the premium is a negative number.
        if quantity > 0:
            ask = self.ask - fill_factor*(self.ask - self.price)
            fill_price = decimalize_2(ask)
            if fill_price <= 0:
                raise ValueError(f"Cannot open LONG with non-positive ask for {self.option_id}")
            premium = float(+fill_price * 100 * abs(quantity))  # cash outflow
            self.position_type = OptionPositionType.LONG
        else:
            bid = self.bid + fill_factor*(self.price - self.bid)
            fill_price = decimalize_2(bid)
            if fill_price <= 0:
                raise ValueError(f"Cannot open SHORT with non-positive bid for {self.option_id}")
            premium = float(-fill_price * 100 * abs(quantity))  # cash inflow
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
                                        price=float(fill_price),
                                        premium=premium,
                                        fees=fees,
                                        spot_price=float(self.spot_price))

        self.trade_open_records.append(trade_open_info)
        self.quantity += quantity

        is_first_open = OptionStatus.TRADE_IS_OPEN not in self.status
        self.status |= OptionStatus.TRADE_IS_OPEN
        self.status &= ~OptionStatus.INITIALIZED

        # Only load price history on the first open; it covers the full remaining life
        if is_first_open:
            self.updates = self.db.get_contract_updates(self.option_id, self.quote_datetime.isoformat())

        self._calculate_trade_open_info()
        self.emit("open_transaction_completed", trade_open_info)
        # print(f'emit open {self.option_id}')
        return trade_open_info


    def get_open_price(self, position_type: OptionPositionType | None = None) -> float:

        fill_factor = settings.get('fill_factor', 0)
        bid = self.bid + fill_factor * (self.price - self.bid)
        ask = self.ask - fill_factor * (self.ask - self.price)

        if position_type is None and self.position_type is None:
            return None

        position_type = self.position_type if position_type is None else position_type

        if position_type == OptionPositionType.LONG:
            return ask
        elif position_type == OptionPositionType.SHORT:
            return bid
        else:
            return None


    def _close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> TradeCloseInfo:
        """
        Calculates the closing price and sets the close date, price and profit/loss info for the
        quantity closed.
        :param quantity: If a quantity is provided, only that quantity will be closed.
        :return: the profit/loss of the closed quantity of the trade
        :rtype: float
        """

        # if trade has already been closed, just return the close info
        if OptionStatus.TRADE_IS_CLOSED in self.status:
            raise ValueError("Option is already closed.")

        if OptionStatus.TRADE_IS_OPEN not in self.status:
            raise ValueError("Cannot close an option that is not open.")

        if quote_datetime is None:
            raise ValueError("quote_datetime is required.")
        if not isinstance(quote_datetime, (datetime.datetime, pd.Timestamp)):
            raise TypeError("quote_datetime must be datetime.datetime or pd.Timestamp.")
        if quote_datetime != self.quote_datetime:
            raise ValueError(
                f"quote_datetime mismatch for {self.option_id}: "
                f"passed {quote_datetime}, option is at {self.quote_datetime}. "
                f"Call next({quote_datetime}) before close_trade()."
            )

        pos_qty = int(self.quantity)
        if pos_qty == 0:
            raise ValueError("No open quantity.")

        # how many contracts to close (always positive)
        if quantity is None:
            close_qty = abs(pos_qty)
        else:
            if not isinstance(quantity, numbers.Integral) or isinstance(quantity, bool):
                raise TypeError("quantity must be an integer.")
            if quantity <= 0:
                raise ValueError("quantity must be positive.")
            if quantity > abs(pos_qty):
                raise ValueError("Quantity to close is greater than the current open quantity.")
            close_qty = int(quantity)

        fill_factor = settings.get('fill_factor', 0)

        # determine executable close price and action sign
        if self.position_type == OptionPositionType.LONG:
            # bid = self.bid + fill_factor*(self.price - self.bid)
            # close_price = decimalize_2(bid)  # sell to close on bid
            action_qty = -close_qty  # sell
        else:  # SHORT
            # ask = self.ask - fill_factor*(self.ask - self.price)
            # close_price = decimalize_2(ask)  # buy to close on ask
            action_qty = +close_qty  # buy

        close_price = decimalize_2(self.get_closing_price())

        if close_price < 0:
            raise ValueError(f"Non-positive close price for {self.option_id}.")

        open_price = decimalize_2(self.trade_open_info.price)
        close_premium = decimalize_2(-(close_price * 100 * action_qty))

        # PnL for this close lot:
        # Long: (close - open)*100*close_qty
        # Short: (open - close)*100*close_qty
        if self.position_type == OptionPositionType.LONG:
            profit_loss = decimalize_2((close_price - open_price) * 100 * close_qty)
        else:
            profit_loss = decimalize_2((open_price - close_price) * 100 * close_qty)

        open_premium = self.trade_open_info.premium
        open_qty = abs(int(self.trade_open_info.quantity))
        open_prem_alloc = decimalize_2(abs(open_premium) * (close_qty/open_qty))
        profit_loss_percent = (profit_loss / open_prem_alloc) if open_prem_alloc > 0 else 0.0
        profit_loss_percent = decimalize_4(profit_loss_percent)

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
            profit_loss_percent=float(profit_loss_percent),
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
        self.emit("close_transaction_completed", rec)
        #print(f'emit close {self.option_id}')

        return rec


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
                return max(self.spot_price - self.strike, 0.0)
            else:
                return max(self.strike - self.spot_price, 0.0)

        # Not expired: executable close depends on position side
        fill_factor = settings.get('fill_factor', 0)
        bid = self.bid + fill_factor*(self.price - self.bid)
        ask = self.ask - fill_factor*(self.ask - self.price)

        # Basic quote sanity
        if bid < 0 or ask < 0 or (ask > 0 and bid > ask):
            raise ValueError(f"Bad quote bid/ask for {self.option_id}: bid={bid}, ask={ask}")

        if self.position_type == OptionPositionType.LONG:

            return bid

        elif self.position_type == OptionPositionType.SHORT:

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


    def _calculate_trade_open_info(self) -> None:
        """Recompute trade_open_info as the weighted average across all open lots in
        trade_open_records. Called after every open_trade (first open or scale-in)."""
        if not self.trade_open_records:
            return
        records = self.trade_open_records
        date = records[-1].date
        total_abs_qty = decimalize_0(sum(abs(r.quantity) for r in records))
        notional = sum(decimalize_2(r.price) * decimalize_0(abs(r.quantity)) for r in records)
        price = decimalize_2(notional / total_abs_qty)
        quantity = int(sum(r.quantity for r in records))
        premium = float(decimalize_2(sum(decimalize_2(r.premium) for r in records)))
        fees = sum(r.fees for r in records)

        self.trade_open_info = TradeOpenInfo(
            option_id=self.option_id,
            instance_id=self.instance_id,
            date=date,
            quantity=quantity,
            price=float(price),
            premium=premium,
            fees=fees,
            spot_price=float(records[-1].spot_price),
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

        total_pnl = decimalize_2(self.get_profit_loss())
        opening_cost_basis = abs(decimalize_2(self.trade_open_info.premium))
        if opening_cost_basis == 0:
            return 0.0
        pnl_pct = decimalize_4(total_pnl / opening_cost_basis)
        return round(float(pnl_pct), 4)

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
        In the Money.
        A call is in the money when the underlying's spot price is at or above the strike.
        A put is in the money when the underlying's spot price is at or below the strike.
        :return: True if the option is currently in the money.
        :rtype: bool
        """

        if self.option_type == 'call':
            return True if self.spot_price >= self.strike else False
        elif self.option_type == 'put':
            return True if self.spot_price <= self.strike else False

    def otm(self) -> bool:
        """
        Out of the Money.
        A call is out of the money when the underlying's spot price is below the strike.
        A put is out of the money when the underlying's spot price is above the strike.
        :return: True if the option is currently out of the money.
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
