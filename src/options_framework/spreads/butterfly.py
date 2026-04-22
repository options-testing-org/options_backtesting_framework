from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_0, decimalize_2
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase
from typing import Self

@dataclass(slots=True)
class Butterfly(SpreadBase):

    @classmethod
    def create(cls,
               option_chain: OptionChain,
               expiration: datetime.date = None,
               option_type: str = None,
               center_strike: int | float = None,
               lower_strike: int | float = None,
               upper_strike: int | float = None,
               position_type: OptionPositionType = None,
               *args, **kwargs) -> Self:

        if center_strike == lower_strike or center_strike == upper_strike:
            raise ValueError("Cannot open a butterfly if the wings are the same strike as the center strike.")
        if lower_strike > center_strike:
            raise ValueError("Lower strike must be lower than the center strike.")
        if upper_strike < center_strike:
            raise ValueError("Upper strike must be higher than the center strike.")

        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain."
            raise ValueError(message)

        # find nearest strikes
        expiration_strikes = option_chain.expiration_strikes[expiration].copy()
        options = [o for o in option_chain.options if
                   o['option_type'] == option_type and o['expiration'] == expiration].copy()

        center_strike = min(expiration_strikes, key=lambda x: abs(x - center_strike))
        lower_strike = min(expiration_strikes, key=lambda x: abs(x - lower_strike))
        upper_strike = min(expiration_strikes, key=lambda x: abs(x - upper_strike))

        center_option_data = next(o for o in options if o['strike'] == center_strike)
        lower_option_data = next(o for o in options if o['strike'] == lower_strike)
        upper_option_data = next(o for o in options if o['strike'] == upper_strike)

        center_option = Option(**center_option_data)
        lower_option = Option(**lower_option_data)
        upper_option = Option(**upper_option_data)

        butterfly = Butterfly(options=[lower_option, center_option, upper_option],
                              spread_type=OptionSpreadType.BUTTERFLY,
                              position_type=OptionPositionType.LONG)

        # save any kwargs that were sent to user_defined
        super(Butterfly, butterfly)._save_user_defined_values(butterfly, **kwargs)
        return butterfly

    lower_option: Option = field(init=False, default=None)
    center_option: Option = field(init=False, default=None)
    upper_option: Option = field(init=False, default=None)


    def __post_init__(self):
        self.lower_option = self.options[0]
        self.center_option = self.options[1]
        self.upper_option = self.options[2]


    def __repr__(self) -> str:
        return f'<{self.spread_type.name}({self.instance_id}) {self.option_type} {self.expiration} {self.lower_option.strike}/{self.center_option.strike}/{self.upper_option.strike}>'


    @property
    def expiration(self) -> datetime.date:
        return self.center_option.expiration

    @property
    def option_type(self) -> str:
        return self.center_option.option_type


    def open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        qty = abs(quantity)
        if self.position_type == OptionPositionType.LONG:
            center_qty = qty * -2
        else:
            qty = qty * -1
            center_qty = qty * 2

        self.lower_option.open_trade(quantity=qty, parent_id=self.instance_id, bid_open=self.lower_option.bid, ask_open=self.lower_option.ask, mid_open=self.lower_option.price)
        self.center_option.open_trade(quantity=center_qty, parent_id=self.instance_id, bid_open=self.center_option.bid, ask_open=self.center_option.ask, mid_open=self.center_option.price)
        self.upper_option.open_trade(quantity=qty, parent_id=self.instance_id, bid_open=self.upper_option.bid, ask_open=self.upper_option.ask, mid_open=self.upper_option.price)

        self.quantity = self.lower_option.quantity

        super(Butterfly, self)._save_user_defined_values(self, **kwargs)


    def close_trade(self, quantity: int | None = None, *args, **kwargs: dict) -> None:
        qty = quantity if quantity is not None else self.lower_option.quantity
        center_qty = quantity * 2
        self.lower_option.close_trade(quantity=qty, parent_id=self.instance_id, bid_close=self.lower_option.bid, ask_close=self.lower_option.ask, mid_close=self.lower_option.price)
        self.center_option.close_trade(quantity=center_qty, parent_id=self.instance_id, bid_close=self.center_option.bid, ask_close=self.center_option.ask, mid_close=self.center_option.price)
        self.upper_option.close_trade(quantity=qty, parent_id=self.instance_id, bid_close=self.upper_option.bid, ask_close=self.upper_option.ask, mid_close=self.upper_option.price)
        self.quantity = self.lower_option.quantity

        super(Butterfly, self)._save_user_defined_values(self, **kwargs)


    def get_trade_price(self) -> float | None:
        if self.center_option.status == OptionStatus.INITIALIZED:
            return None
        else:
            lower_price = self.lower_option.trade_open_info.price
            center_price = self.center_option.trade_open_info.price
            upper_price = self.upper_option.trade_open_info.price
            price = self._calculate_price(lower_price=lower_price,
                                          center_price=center_price,
                                          upper_price=upper_price)

            return price


    @property
    def price(self) -> float:
        lower_price = self.lower_option.price
        center_price = self.center_option.price
        upper_price = self.upper_option.price

        price = self._calculate_price(lower_price=lower_price, center_price=center_price, upper_price=upper_price)

        return price

    """
    Long Call Butterfly Spread:
    Maximum Profit: Limited to the difference between the middle and lower strike minus the net cost of the spread.
    Maximum Loss: Limited to the net cost of establishing the spread.
    
    Long Put Butterfly Spread:
    Maximum Profit: Limited to the difference between the middle and lower strike minus the net cost of the spread.
    Maximum Loss: Limited to the net cost of establishing the spread.
    
    Short Call Butterfly Spread:
    Maximum Profit: Limited to the net credit received when entering the trade.
    Maximum Loss: Limited to the difference between the middle and lower strike prices minus the net credit received.
    
    Short Put Butterfly Spread:
    Maximum Profit: Limited to the net credit received when entering the trade.
    Maximum Loss: Limited to the difference between the middle and lower strike prices minus the net credit received.
    """

    @property
    def symbol(self) -> str:
        return self.center_option.symbol

    def get_required_margin(self, quantity: int) -> float:
        pass

    @property
    def status(self) -> OptionStatus:
        return self.center_option.status

    def get_dte(self) -> int | None:
        return self.center_option.get_dte()

    def get_closed_price(self) -> float | None:
        if all(OptionStatus.TRADE_IS_CLOSED in x.status for x in self.options):
            lower_price = self.lower_option.trade_close_info.price
            center_price = self.center_option.trade_close_info.price
            upper_price = self.upper_option.trade_close_info.price

            price = self._calculate_price(lower_price=lower_price, center_price=center_price, upper_price=upper_price)
            return price
        else:
           return None

    def get_price_history(self) -> list[tuple]:
        lower_history = self.lower_option.history
        center_history = self.center_option.history
        upper_history = self.upper_option.history

        history = []
        for i in range(len(lower_history)):
            dt = lower_history[i][0]
            lower_price = lower_history[i][1]
            center_price = center_history[i][1]
            upper_price = upper_history[i][1]
            price = self._calculate_price(lower_price=lower_price, center_price=center_price, upper_price=upper_price)
            spot_price = lower_history[i][2]
            dte = lower_history[i][3]

            history.append((dt, price, spot_price, dte))

        return history

    @property
    def max_profit(self) -> float | None:
        return None
        """
        current_price = decimalize_2(self.price)
        quantity = decimalize_0(self.quantity)
        current_value = current_price * 100 * quantity
        """


    @property
    def max_loss(self) -> float | None:
        return None


    def _calculate_price(self, *, lower_price: float, center_price: float, upper_price: float) -> float:
        lower_price = decimalize_2(lower_price)
        center_price = decimalize_2(center_price)
        upper_price = decimalize_2(upper_price)
        if self.position_type == OptionPositionType.LONG:
            price = (lower_price + upper_price) - center_price*2
        else:
            price = center_price*2 - (lower_price + upper_price)

        return float(price)
