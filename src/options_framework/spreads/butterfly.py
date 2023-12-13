from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_0, decimalize_2
from options_framework.option import Option
from options_framework.option_types import OptionType, OptionCombinationType, OptionStatus
from options_framework.spreads.option_combo import OptionCombination


@dataclass(repr=False, slots=True)
class Butterfly(OptionCombination):

    @classmethod
    def get_balanced_butterfly(cls, *, options: list[Option], expiration: datetime.date, option_type: OptionType,
                               center_strike: int | float, wing_width: int | float, quantity: int = 1):

        expiration = datetime.date(expiration.year, expiration.month, expiration.day)
        candidates = [o for o in options if o.expiration == expiration and o.option_type == option_type]
        center_option_candidates = [o for o in candidates if o.strike >= center_strike]
        if not center_option_candidates:
            raise ValueError("Butterfly position cannot be created with these values")
        center_option = center_option_candidates[0]
        center_option.quantity = quantity * 2 * -1
        lower_wing_candidates = [o for o in candidates if o.strike <= (center_option.strike - wing_width)]
        if not lower_wing_candidates:
            raise ValueError("Butterfly position cannot be created with these values")
        lower_wing = lower_wing_candidates[-1]
        lower_wing.quantity = quantity
        upper_wing_candidates = [o for o in candidates if o.strike >= (center_option.strike + wing_width)]
        if not upper_wing_candidates:
            raise ValueError("Butterfly position cannot be created with these values")
        upper_wing = upper_wing_candidates[0]
        upper_wing.quantity = quantity
        position_options = [lower_wing, center_option, upper_wing]
        butterfly = Butterfly(position_options, option_combination_type=OptionCombinationType.BUTTERFLY,
                              quantity=quantity)
        return butterfly

    lower_option: Option = field(init=False, default=None)
    center_option: Option = field(init=False, default=None)
    upper_option: Option = field(init=False, default=None)
    lower_breakeven: float = field(init=False, default=None)
    upper_breakeven: float = field(init=False, default=None)
    _max_loss: float | int = field(init=False, default=None)
    _max_profit: float | int = field(init=False, default=None)

    def __post_init__(self):
        self.lower_option = self.options[0]
        self.center_option = self.options[1]
        self.upper_option = self.options[2]

    def __repr__(self) -> str:
        return f'<{self.option_combination_type.name}({self.position_id}) {self.option_type.name}  {self.lower_option.strike}/{self.center_option.strike}/{self.upper_option.strike}>'

    @property
    def expiration(self) -> datetime.date:
        return self.center_option.expiration

    @property
    def option_type(self) -> OptionType:
        return self.center_option.option_type

    def open_trade(self, *, quantity: int, **kwargs: dict) -> None:
        self.lower_option.open_trade(quantity=self.quantity)
        self.center_option.open_trade(quantity=self.quantity * 2 * -1)
        self.upper_option.open_trade(quantity=self.quantity)
        self._max_profit = (((self.upper_option.strike - self.center_option.strike)
                             - (self.lower_option.price + (
                        self.center_option.price * 2 * -1) + self.upper_option.price))
                            * 100)
        self._max_loss = self.current_value
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

    @property
    def max_profit(self) -> float:
        upper_strike = decimalize_0(self.upper_option.strike)
        center_strike = decimalize_0(self.center_option.strike)
        price = decimalize_2(self.price)
        max_profit = self._max_profit if self._max_profit else (((upper_strike - center_strike) - price) * 100)
        return float(max_profit)

    @property
    def max_loss(self) -> float:
        max_loss = self._max_loss if self._max_loss else self.current_value
        return float(max_loss)

    @property
    def risk_to_reward(self) -> float:
        max_profit = decimalize_2(self.max_profit)
        max_loss = decimalize_2(self.max_loss)
        r2r = decimalize_2(max_profit / max_loss)

        return float(r2r)

