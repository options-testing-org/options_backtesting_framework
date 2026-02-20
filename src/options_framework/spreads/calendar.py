from dataclasses import dataclass, field

from options_framework.option_types import OptionPositionType, OptionSpreadType, OptionStatus
from options_framework.option_chain import OptionChain
from options_framework.spreads.spread_base import SpreadBase
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
import datetime
from typing import Self


@dataclass(slots=True)
class Calendar(SpreadBase):

    front_option: Option = field(default=None)
    back_option: Option = field(default=None)
    position_type: OptionPositionType = field(default=None)

    @classmethod
    def create(cls, option_chain: OptionChain,
               strike: float,
               front_expiration: datetime.date,
               back_expiration: datetime.date,
               option_type: str,
               *args, **kwargs) -> Self:

        # Make sure expirations exist
        has_front_exp =  any(e for e in option_chain.expirations if e == front_expiration)
        if not has_front_exp:
            raise ValueError(f"Front expiration {front_expiration} cannot be found")

        has_back_exp = any(e for e in option_chain.expirations if e == back_expiration)
        if not has_back_exp:
            raise ValueError(f"Back expiration {back_expiration} cannot be found")

        # Make sure we can find the strike for each expiration
        expiration_strikes = option_chain.expiration_strikes[front_expiration].copy()
        front_exp_has_strike = any(k for k in expiration_strikes if k == strike)
        if not front_exp_has_strike:
            raise ValueError(f"Strike {strike} for front expiration {front_expiration} cannot be found")

        expiration_strikes = option_chain.expiration_strikes[back_expiration].copy()
        back_exp_has_strike = any(k for k in expiration_strikes if k == strike)
        if not back_exp_has_strike:
            raise ValueError(f"Strike {strike} for back expiration {back_expiration} cannot be found")

        try:
            front_data = next(x for x in option_chain.options if x['option_type'] == option_type
                            and x['expiration'] == front_expiration
                            and x['strike'] == strike)
            back_data = next(x for x in option_chain.options if x['option_type'] == option_type
                            and x['expiration'] == back_expiration
                            and x['strike'] == strike)

        except StopIteration:
            raise ValueError("Option cannot be found in option chain")

        front_option = Option(**front_data)
        back_option = Option(**back_data)

        calendar = Calendar(options=[front_option, back_option], spread_type=OptionSpreadType.CALENDAR)

        # save any kwargs that were sent to user_defined dict
        super(Calendar, calendar)._save_user_defined_values(calendar, **kwargs)

        return calendar

    def __post_init__(self):
        message = None
        if self.options[0].option_type != self.options[1].option_type:
            message = "Invalid option type. Both legs must be either calls or puts."
        if self.options[0].expiration >= self.options[1].expiration:
            message = "Front expiration must be before back expiration"
        if self.options[0].strike != self.options[1].strike:
            message = "Front and back option strikes must be the same."

        if self.spread_type != OptionSpreadType.CALENDAR:
            message = "Calendar must have spread type of CALENDAR"
        if message is not None:
            raise ValueError(message)

        self.front_option = self.options[0]
        self.back_option = self.options[1]

    def __repr__(self) -> str:
        return "calendar"

    def open_trade(self, quantity: int = 1, *args, **kwargs: dict) -> None:
        if quantity == 0:
            raise ValueError("Quantity cannot be zero")

        front_qty = -quantity  # long cal => short front
        back_qty = quantity  # long cal => long back

        self.front_option.open_trade(quantity=front_qty)
        self.back_option.open_trade(quantity=back_qty)

        self.position_type = OptionPositionType.LONG if quantity > 0 else OptionPositionType.SHORT
        self.quantity = quantity

        super(Calendar, self)._save_user_defined_values(self, **kwargs)

    def close_trade(self, quantity: int | None = None, *args, **kwargs: dict) -> None:
        # how many spreads to close
        if quantity is None:
            # close all based on the back leg open size
            n = abs(int(self.back_option.quantity))
        else:
            if quantity == 0:
                raise ValueError("Quantity cannot be zero")
            n = abs(int(quantity))

        # close front leg if open
        if OptionStatus.TRADE_IS_OPEN in self.front_option.status:
            self.front_option.close_trade(quantity=n)

        # close back leg if open
        if OptionStatus.TRADE_IS_OPEN in self.back_option.status:
            self.back_option.close_trade(quantity=n)

        super(Calendar, self)._save_user_defined_values(self, **kwargs)

    @property
    def max_profit(self) -> float | None:
        if self.position_type == OptionPositionType.LONG:
            return None # Max Profit = (Value of Long-Term Option at Front-Month Expiration) - (Net Debit Paid)
        else:
            premium = self.price * abs(self.quantity)
            return premium # Max Profit = Net Credit Received - Commissions

    @property
    def max_loss(self) -> float | None:
        if self.position_type == OptionPositionType.LONG:
            premium = self.get_trade_price() * 100 * abs(self.quantity)
            return premium # Maximum Loss = Net Debit Paid + Commissions
        else:
            return None #

    def get_required_margin(self, quantity: int) -> float:
        if self.position_type == OptionPositionType.LONG:
            premium = self.get_trade_price() * 100 * abs(self.quantity)
            return premium  # Maximum Loss = Net Debit Paid + Commissions
        else:
            return None # short option

    @property
    def status(self) -> OptionStatus:
        if any(x for x in self.options if OptionStatus.TRADE_IS_OPEN in x.status):
            return OptionStatus.TRADE_IS_OPEN
        elif all(x for x in self.options if OptionStatus.TRADE_IS_CLOSED in x.status):
            return OptionStatus.TRADE_IS_CLOSED
        elif all(x for x in self.options if OptionStatus.EXPIRED in x.status):
            return OptionStatus.EXPIRED
        else:
            return OptionStatus.INITIALIZED


    @property
    def price(self) -> float:
        if self.position_type == OptionPositionType.LONG:
            price = self.back_option.price - self.front_option.price
        elif self.position_type == OptionPositionType.SHORT:
            price = self.front_option.price - self.back_option.price
        else:
            price = None
        return price

    def get_dte(self) -> int | None:
        if OptionStatus.TRADE_IS_OPEN in self.front_option.status:
            return self.front_option.get_dte()
        else:
            return self.back_option.get_dte()

    def get_trade_price(self) -> float | None:
        if all(o.status == OptionStatus.INITIALIZED for o in self.options):
            return None
        else:
            if self.position_type == OptionPositionType.LONG:
                price = self.back_option.trade_open_info.price - self.front_option.trade_open_info.price
            else:
                price = self.front_option.trade_open_info.price - self.back_option.trade_open_info.price
            return price

    def get_profit_loss(self) -> float:
        pnl = super(Calendar, self).get_profit_loss()
        if self.position_type == OptionPositionType.LONG and pnl < self.max_loss * -1:
            return self.max_loss * -1
        elif self.position_type == OptionPositionType.SHORT and pnl > self.max_profit:
            return self.max_profit
        else:
            return pnl