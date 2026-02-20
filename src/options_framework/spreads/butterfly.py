from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_0, decimalize_2
from options_framework.option import Option
from options_framework.option_types import OptionSpreadType, OptionStatus, OptionPositionType
from options_framework.spreads.spread_base import SpreadBase


@dataclass(repr=False, slots=True)
class Butterfly(SpreadBase):

    @classmethod
    def get_balanced_butterfly(cls, *, option_chain: list[Option], expiration: datetime.date, option_type: str,
                               center_strike: int | float, wing_width: int | float, quantity: int = 1):

        expiration = datetime.date(expiration.year, expiration.month, expiration.day)
        candidates = [o for o in option_chain if o.expiration == expiration and o.option_type == option_type]
        center_option_candidates = [o for o in candidates if o.strike >= center_strike]
        if not center_option_candidates:
            raise ValueError("Butterfly position cannot be created with these values - no center wing options found")
        center_option = center_option_candidates[0]
        lower_wing_candidates = [o for o in candidates if o.strike <= (center_option.strike - wing_width)]
        if not lower_wing_candidates:
            lower_wing = candidates[0]
        else:
            lower_wing = lower_wing_candidates[-1]
        upper_wing_candidates = [o for o in candidates if o.strike >= (center_option.strike + wing_width)]
        if not upper_wing_candidates:
            upper_wing = candidates[-1]
        else:
            upper_wing = upper_wing_candidates[0]
        position_options = [lower_wing, center_option, upper_wing]

        butterfly = Butterfly(position_options, spread_type=OptionSpreadType.BUTTERFLY,
                              quantity=quantity)
        return butterfly

    @classmethod
    def get_unbalanced_butterfly(cls, *, option_chain: list[Option], expiration: datetime.date, option_type: str,
                                 center_strike: int | float,  lower_wing_width: int | float,
                                 upper_wing_width: int | float, center_quantity_multiple: int = -3,
                                 lower_quantity_multiple: int = 2, upper_quantity_multiple: int = 1,
                                 quantity: int = 1):

        if center_quantity_multiple + lower_quantity_multiple + upper_quantity_multiple != 0:
            raise ValueError("Option quantity multiples are unbalanced. This configuration will open naked options.")

        expiration = datetime.date(expiration.year, expiration.month, expiration.day)
        candidates = [o for o in option_chain if o.expiration == expiration and o.option_type == option_type]
        center_option_candidates = [o for o in candidates if o.strike >= center_strike]
        if not center_option_candidates:
            ex = ValueError()
            ex.strerror = "Butterfly position cannot be created with these values - no center wing options found"
            raise ex
        center_option = center_option_candidates[0]
        center_option.quantity = center_quantity_multiple * quantity
        lower_wing_candidates = [o for o in candidates if o.strike <= (center_option.strike - lower_wing_width)]
        if not lower_wing_candidates:
            lower_wing = candidates[0]
        else:
            lower_wing = lower_wing_candidates[-1]
        lower_wing.quantity = lower_quantity_multiple * quantity
        upper_wing_candidates = [o for o in candidates if o.strike >= (center_option.strike + upper_wing_width)]
        if not upper_wing_candidates:
            upper_wing = candidates[-1]
        else:
            upper_wing = upper_wing_candidates[0]
        upper_wing.quantity = upper_quantity_multiple * quantity
        position_options = [lower_wing, center_option, upper_wing]
        user_defined = {'center_quantity_multiple': center_quantity_multiple,
                        'lower_quantity_multiple': lower_quantity_multiple,
                        'upper_quantity_multiple': upper_quantity_multiple}
        butterfly = Butterfly(position_options, spread_type=OptionSpreadType.BUTTERFLY,
                              quantity=quantity, user_defined=user_defined)
        return butterfly

    lower_quantity_multiple: int = field(init=False, default=1)
    center_quantity_multiple: int = field(init=False, default=-2)
    upper_quantity_multiple: int = field(init=False, default=1)
    lower_option: Option = field(init=False, default=None)
    center_option: Option = field(init=False, default=None)
    upper_option: Option = field(init=False, default=None)
    lower_breakeven: float = field(init=False, default=None)
    upper_breakeven: float = field(init=False, default=None)

    def __post_init__(self):
        self.lower_option = self.options[0]
        if 'lower_quantity_multiple' in self.user_defined.keys():
            self.lower_quantity_multiple = self.user_defined['lower_quantity_multiple']
        self.lower_option.quantity = self.quantity * self.lower_quantity_multiple
        self.center_option = self.options[1]
        if 'center_quantity_multiple' in self.user_defined.keys():
            self.center_quantity_multiple = self.user_defined['center_quantity_multiple']
        self.center_option.quantity = self.quantity * self.center_quantity_multiple
        self.upper_option = self.options[2]
        if 'upper_quantity_multiple' in self.user_defined.keys():
            self.upper_quantity_multiple = self.user_defined['upper_quantity_multiple']
        self.upper_option.quantity = self.quantity * self.upper_quantity_multiple
        self.option_position_type = OptionPositionType.LONG if self.center_option.quantity < 0 \
            else OptionPositionType.SHORT

    def __repr__(self) -> str:
        return f'<{self.spread_type.name}({self.instance_id}) {self.option_type.name}  {self.lower_option.strike}/{self.center_option.strike}/{self.upper_option.strike}>'

    @property
    def expiration(self) -> datetime.date:
        return self.center_option.expiration

    @property
    def option_type(self) -> str:
        return self.center_option.option_type

    def open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        self.lower_option.open_trade(quantity=quantity * self.lower_quantity_multiple)
        self.center_option.open_trade(quantity=quantity * self.center_quantity_multiple)
        self.upper_option.open_trade(quantity=quantity * self.upper_quantity_multiple)
        self.lower_breakeven = self.lower_option.strike + self.price
        self.upper_breakeven = self.upper_option.strike - self.price

    def close_trade(self, *, quantity: int, **kwargs: dict) -> None:
        self.lower_option.close_trade(quantity=self.lower_option.quantity)
        self.center_option.close_trade(quantity=self.center_option.quantity)
        self.upper_option.close_trade(quantity=self.upper_option.quantity)

    def get_trade_price(self) -> float | None:
        lower_price = decimalize_2(self.lower_option.trade_open_info.price)
        center_price = decimalize_2(self.center_option.trade_open_info.price)
        upper_price = decimalize_2(self.upper_option.trade_open_info.price)
        price = lower_price + (center_price * 2 * -1) + upper_price
        return float(price)

    @property
    def price(self) -> float:
        lower_price = decimalize_2(self.lower_option.price)
        center_price = decimalize_2(self.center_option.price)
        upper_price = decimalize_2(self.upper_option.price)
        price = lower_price + (center_price * 2 * -1) + upper_price
        return float(price)

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
    def max_profit(self) -> float:
        upper_strike = decimalize_2(self.upper_option.strike)
        center_strike = decimalize_2(self.center_option.strike)
        lower_strike = decimalize_2(self.lower_option.strike)
        """
        current_price = decimalize_2(self.price)
        quantity = decimalize_0(self.quantity)
        current_value = current_price * 100 * quantity
        """

        max_profit = None
        if self.option_position_type == OptionPositionType.LONG:
            if self.option_type == 'call':
                # debit spread max profit
                spread = center_strike - lower_strike
                price = self.center_option.trade_price + self.lower_option.trade_price
                amt = spread - price
                # credit spread max profit

                pass
            # the spread between the strike prices - net premium paid
            spread1 = self.upper_option.trade_value * 0
            compare_strike = lower_strike if self.option_type == 'call' else upper_strike
        else:
            pass

        price = decimalize_2(self.price)
        max_profit = self._max_profit if self._max_profit else (((upper_strike - center_strike) - price) * 100)
        return float(decimalize_2(max_profit))

    @property
    def max_loss(self) -> float:
        max_loss = self._max_loss if self._max_loss else self.current_value
        return float(max_loss)
        # self._max_profit = (((self.upper_option.strike - self.center_option.strike)
        #                      - (self.lower_option.price + (
        #                 self.center_option.price * 2 * -1) + self.upper_option.price))
        #                     * 100)
        # self._max_loss = self.current_value

    @property
    def risk_to_reward(self) -> float:
        max_profit = decimalize_2(self.max_profit)
        max_loss = decimalize_2(self.max_loss)
        r2r = decimalize_2(max_profit / max_loss)

        return float(r2r)

    @property
    def required_margin(self) -> float:
        return 0
