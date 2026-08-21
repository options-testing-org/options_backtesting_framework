from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase
from typing import Self


@dataclass(repr=False, slots=True)
class Condor(SpreadBase):

    lower_option: Option        = field(init=False, default=None)
    lower_middle_option: Option = field(init=False, default=None)
    upper_middle_option: Option = field(init=False, default=None)
    upper_option: Option        = field(init=False, default=None)

    def __post_init__(self):
        self.lower_option        = self.options[0]
        self.lower_middle_option = self.options[1]
        self.upper_middle_option = self.options[2]
        self.upper_option        = self.options[3]

    def __repr__(self) -> str:
        return (
            f'<{self.spread_type.name}({self.instance_id}) '
            f'{self.option_type} {self.expiration} '
            f'{self.lower_option.strike}/'
            f'{self.lower_middle_option.strike}/'
            f'{self.upper_middle_option.strike}/'
            f'{self.upper_option.strike}>'
        )

    @classmethod
    def create(cls,
               option_chain: OptionChain,
               expiration: datetime.date = None,
               option_type: str = None,
               lower_strike: int | float = None,
               lower_middle_strike: int | float = None,
               upper_middle_strike: int | float = None,
               upper_strike: int | float = None,
               position_type: OptionPositionType = None,
               *args, **kwargs) -> Self:

        if lower_strike >= lower_middle_strike:
            raise ValueError("lower_strike must be less than lower_middle_strike.")
        if lower_middle_strike >= upper_middle_strike:
            raise ValueError("lower_middle_strike must be less than upper_middle_strike.")
        if upper_middle_strike >= upper_strike:
            raise ValueError("upper_middle_strike must be less than upper_strike.")

        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            raise ValueError("No matching expiration was found in the option chain.")

        expiration_strikes = option_chain.expiration_strikes[expiration].copy()
        options = [o for o in option_chain.options
                   if o['option_type'] == option_type and o['expiration'] == expiration].copy()

        lower_strike        = min(expiration_strikes, key=lambda x: abs(x - lower_strike))
        lower_middle_strike = min(expiration_strikes, key=lambda x: abs(x - lower_middle_strike))
        upper_middle_strike = min(expiration_strikes, key=lambda x: abs(x - upper_middle_strike))
        upper_strike        = min(expiration_strikes, key=lambda x: abs(x - upper_strike))

        lower_option        = Option(**next(o for o in options if o['strike'] == lower_strike))
        lower_middle_option = Option(**next(o for o in options if o['strike'] == lower_middle_strike))
        upper_middle_option = Option(**next(o for o in options if o['strike'] == upper_middle_strike))
        upper_option        = Option(**next(o for o in options if o['strike'] == upper_strike))

        resolved_position_type = position_type if position_type is not None else OptionPositionType.LONG

        condor = Condor(
            options=[lower_option, lower_middle_option, upper_middle_option, upper_option],
            spread_type=OptionSpreadType.CONDOR,
            position_type=resolved_position_type,
        )

        super(Condor, condor)._save_user_defined_values(condor, **kwargs)
        return condor

    @property
    def expiration(self) -> datetime.date:
        return self.lower_option.expiration

    @property
    def option_type(self) -> str:
        return self.lower_option.option_type

    def _open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        qty = abs(quantity)
        if self.position_type == OptionPositionType.LONG:
            # LONG condor: buy wings, sell body
            wing_qty   =  qty
            body_qty   = -qty
        else:
            # SHORT condor: sell wings, buy body
            wing_qty   = -qty
            body_qty   =  qty

        self.lower_option._open_trade(quantity=wing_qty)
        self.lower_middle_option._open_trade(quantity=body_qty)
        self.upper_middle_option._open_trade(quantity=body_qty)
        self.upper_option._open_trade(quantity=wing_qty)

        self.quantity = self.lower_option.quantity
        super(Condor, self)._save_user_defined_values(self, **kwargs)

    def _close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        self.lower_option._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.lower_middle_option._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.upper_middle_option._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.upper_option._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.quantity = self.lower_option.quantity
        super(Condor, self)._save_user_defined_values(self, **kwargs)

    def _calculate_price(self, *,
                         lower_price: float,
                         lower_middle_price: float,
                         upper_middle_price: float,
                         upper_price: float) -> float:
        l  = decimalize_2(lower_price)
        lm = decimalize_2(lower_middle_price)
        um = decimalize_2(upper_middle_price)
        u  = decimalize_2(upper_price)
        if self.position_type == OptionPositionType.LONG:
            price = (l + u) - (lm + um)
        else:
            price = (lm + um) - (l + u)
        return float(price)

    @property
    def price(self) -> float:
        return self._calculate_price(
            lower_price=self.lower_option.price,
            lower_middle_price=self.lower_middle_option.price,
            upper_middle_price=self.upper_middle_option.price,
            upper_price=self.upper_option.price,
        )

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED in self.lower_option.status:
            return None
        return self._calculate_price(
            lower_price=self.lower_option.trade_open_info.price,
            lower_middle_price=self.lower_middle_option.trade_open_info.price,
            upper_middle_price=self.upper_middle_option.trade_open_info.price,
            upper_price=self.upper_option.trade_open_info.price,
        )

    def get_closed_price(self) -> float | None:
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            return self._calculate_price(
                lower_price=self.lower_option.trade_close_info.price,
                lower_middle_price=self.lower_middle_option.trade_close_info.price,
                upper_middle_price=self.upper_middle_option.trade_close_info.price,
                upper_price=self.upper_option.trade_close_info.price,
            )
        return None

    def get_dte(self) -> int | None:
        return self.lower_option.get_dte()

    @property
    def max_profit(self) -> float | None:
        if OptionStatus.INITIALIZED in self.lower_option.status:
            return None
        trade_price = self.get_trade_price()
        wing_width = min(
            self.lower_middle_option.strike - self.lower_option.strike,
            self.upper_option.strike - self.upper_middle_option.strike,
        )
        if self.position_type == OptionPositionType.LONG:
            return float(decimalize_2(wing_width) - decimalize_2(trade_price))
        else:
            return trade_price

    @property
    def max_loss(self) -> float | None:
        if OptionStatus.INITIALIZED in self.lower_option.status:
            return None
        trade_price = self.get_trade_price()
        wing_width = min(
            self.lower_middle_option.strike - self.lower_option.strike,
            self.upper_option.strike - self.upper_middle_option.strike,
        )
        if self.position_type == OptionPositionType.LONG:
            return trade_price
        else:
            return float(decimalize_2(wing_width) - decimalize_2(trade_price))

    @property
    def status(self) -> OptionStatus:
        return self.lower_middle_option.status

    def get_required_margin(self, quantity: int) -> float:
        if self.position_type == OptionPositionType.LONG:
            return 0.0
        wing_width = min(
            self.lower_middle_option.strike - self.lower_option.strike,
            self.upper_option.strike - self.upper_middle_option.strike,
        )
        max_loss = float(decimalize_2(wing_width) - decimalize_2(self.price))
        return max_loss * 100 * abs(quantity)

    def get_history(self) -> list[dict]:
        if (OptionStatus.TRADE_IS_OPEN not in self.lower_option.status
                and OptionStatus.TRADE_IS_CLOSED not in self.lower_option.status):
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        if OptionStatus.TRADE_IS_CLOSED in self.lower_option.status:
            last_date = self.lower_option.trade_close_info.date
        else:
            last_date = self.lower_option.quote_datetime

        trade_price   = self.get_trade_price()
        open_qty      = abs(self.lower_option.trade_open_info.quantity)
        close_records = self.lower_option.trade_close_records

        l_updates  = self.lower_option.updates
        lm_updates = self.lower_middle_option.updates
        um_updates = self.upper_middle_option.updates
        u_updates  = self.upper_option.updates

        keys = [k for k in l_updates if k <= last_date]

        history = []
        for k in keys:
            lu  = l_updates[k]
            lmu = lm_updates[k]
            umu = um_updates[k]
            uu  = u_updates[k]

            price = self._calculate_price(
                lower_price=round(float(lu['price']), 2),
                lower_middle_price=round(float(lmu['price']), 2),
                upper_middle_price=round(float(umu['price']), 2),
                upper_price=round(float(uu['price']), 2),
            )

            closes_so_far         = sum(r.quantity for r in close_records if r.date <= k)
            remaining_qty         = open_qty - closes_so_far
            open_premium_allocated = abs(trade_price) * 100 * remaining_qty

            pnl     = round((price - trade_price) * 100 * remaining_qty, 2)
            pnl_pct = round(pnl / open_premium_allocated, 4) if open_premium_allocated != 0 else 0.0

            def _net_greek(l_val, lm_val, um_val, u_val):
                if any(v is None for v in (l_val, lm_val, um_val, u_val)):
                    return None
                if self.position_type == OptionPositionType.LONG:
                    return (l_val + u_val) - (lm_val + um_val)
                else:
                    return (lm_val + um_val) - (l_val + u_val)

            def _avg_iv(*vals):
                non_none = [v for v in vals if v is not None]
                return sum(non_none) / len(non_none) if non_none else None

            history.append({
                'quote_datetime': k,
                'price':      price,
                'spot_price': lu.get('spot_price'),
                'pnl':        pnl,
                'pnl_pct':    pnl_pct,
                'delta': _net_greek(lu.get('delta'),  lmu.get('delta'),  umu.get('delta'),  uu.get('delta')),
                'gamma': _net_greek(lu.get('gamma'),  lmu.get('gamma'),  umu.get('gamma'),  uu.get('gamma')),
                'theta': _net_greek(lu.get('theta'),  lmu.get('theta'),  umu.get('theta'),  uu.get('theta')),
                'vega':  _net_greek(lu.get('vega'),   lmu.get('vega'),   umu.get('vega'),   uu.get('vega')),
                'rho':   _net_greek(lu.get('rho'),    lmu.get('rho'),    umu.get('rho'),    uu.get('rho')),
                'iv':    _avg_iv(lu.get('implied_volatility'), lmu.get('implied_volatility'),
                                 umu.get('implied_volatility'), uu.get('implied_volatility')),
            })

        return history

    def get_updates(self) -> list[dict]:
        pass