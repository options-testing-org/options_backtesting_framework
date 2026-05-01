from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase
from typing import Self


@dataclass(repr=False, slots=True)
class IronCondor(SpreadBase):

    lower_put: Option   = field(init=False, default=None)
    upper_put: Option   = field(init=False, default=None)
    lower_call: Option  = field(init=False, default=None)
    upper_call: Option  = field(init=False, default=None)

    def __post_init__(self):
        self.lower_put  = self.options[0]
        self.upper_put  = self.options[1]
        self.lower_call = self.options[2]
        self.upper_call = self.options[3]

    def __repr__(self) -> str:
        return (
            f'<{self.spread_type.name}({self.instance_id}) '
            f'{self.expiration} '
            f'{self.lower_put.strike}P/'
            f'{self.upper_put.strike}P/'
            f'{self.lower_call.strike}C/'
            f'{self.upper_call.strike}C>'
        )

    @classmethod
    def create(cls,
               option_chain: OptionChain,
               expiration: datetime.date = None,
               lower_put_strike: int | float = None,
               upper_put_strike: int | float = None,
               lower_call_strike: int | float = None,
               upper_call_strike: int | float = None,
               position_type: OptionPositionType = None,
               *args, **kwargs) -> Self:

        if lower_put_strike >= upper_put_strike:
            raise ValueError("lower_put_strike must be less than upper_put_strike.")
        if upper_put_strike >= lower_call_strike:
            raise ValueError("upper_put_strike must be less than lower_call_strike.")
        if lower_call_strike >= upper_call_strike:
            raise ValueError("lower_call_strike must be less than upper_call_strike.")

        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            raise ValueError("No matching expiration was found in the option chain.")

        all_options = [o for o in option_chain.options if o['expiration'] == expiration].copy()
        puts  = [o for o in all_options if o['option_type'] == 'put']
        calls = [o for o in all_options if o['option_type'] == 'call']

        put_strikes  = sorted({o['strike'] for o in puts})
        call_strikes = sorted({o['strike'] for o in calls})

        lower_put_strike  = min(put_strikes,  key=lambda x: abs(x - lower_put_strike))
        upper_put_strike  = min(put_strikes,  key=lambda x: abs(x - upper_put_strike))
        lower_call_strike = min(call_strikes, key=lambda x: abs(x - lower_call_strike))
        upper_call_strike = min(call_strikes, key=lambda x: abs(x - upper_call_strike))

        lower_put  = Option(**next(o for o in puts  if o['strike'] == lower_put_strike))
        upper_put  = Option(**next(o for o in puts  if o['strike'] == upper_put_strike))
        lower_call = Option(**next(o for o in calls if o['strike'] == lower_call_strike))
        upper_call = Option(**next(o for o in calls if o['strike'] == upper_call_strike))

        resolved_position_type = position_type if position_type is not None else OptionPositionType.SHORT

        iron_condor = IronCondor(
            options=[lower_put, upper_put, lower_call, upper_call],
            spread_type=OptionSpreadType.IRON_CONDOR,
            position_type=resolved_position_type,
        )

        super(IronCondor, iron_condor)._save_user_defined_values(iron_condor, **kwargs)
        return iron_condor

    @property
    def expiration(self) -> datetime.date:
        return self.lower_put.expiration

    def open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        qty = abs(quantity)
        if self.position_type == OptionPositionType.SHORT:
            # SHORT: long wings, short body
            wing_qty =  qty
            body_qty = -qty
        else:
            # LONG: short wings, long body
            wing_qty = -qty
            body_qty =  qty

        self.lower_put.open_trade(quantity=wing_qty)
        self.upper_put.open_trade(quantity=body_qty)
        self.lower_call.open_trade(quantity=body_qty)
        self.upper_call.open_trade(quantity=wing_qty)

        self.quantity = self.lower_put.quantity
        super(IronCondor, self)._save_user_defined_values(self, **kwargs)

    def close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        self.lower_put.close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.upper_put.close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.lower_call.close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.upper_call.close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.quantity = self.lower_put.quantity
        super(IronCondor, self)._save_user_defined_values(self, **kwargs)

    def _calculate_price(self, *,
                         lower_put_price: float,
                         upper_put_price: float,
                         lower_call_price: float,
                         upper_call_price: float) -> float:
        lp = decimalize_2(lower_put_price)
        up = decimalize_2(upper_put_price)
        lc = decimalize_2(lower_call_price)
        uc = decimalize_2(upper_call_price)
        if self.position_type == OptionPositionType.SHORT:
            price = (up + lc) - (lp + uc)
        else:
            price = (lp + uc) - (up + lc)
        return float(price)

    @property
    def price(self) -> float:
        return self._calculate_price(
            lower_put_price=self.lower_put.price,
            upper_put_price=self.upper_put.price,
            lower_call_price=self.lower_call.price,
            upper_call_price=self.upper_call.price,
        )

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED in self.lower_put.status:
            return None
        return self._calculate_price(
            lower_put_price=self.lower_put.trade_open_info.price,
            upper_put_price=self.upper_put.trade_open_info.price,
            lower_call_price=self.lower_call.trade_open_info.price,
            upper_call_price=self.upper_call.trade_open_info.price,
        )

    def get_closed_price(self) -> float | None:
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            return self._calculate_price(
                lower_put_price=self.lower_put.trade_close_info.price,
                upper_put_price=self.upper_put.trade_close_info.price,
                lower_call_price=self.lower_call.trade_close_info.price,
                upper_call_price=self.upper_call.trade_close_info.price,
            )
        return None

    def get_dte(self) -> int | None:
        return self.lower_put.get_dte()

    def _wing_width(self) -> float:
        put_width  = self.upper_put.strike  - self.lower_put.strike
        call_width = self.upper_call.strike - self.lower_call.strike
        return min(put_width, call_width)

    @property
    def max_profit(self) -> float | None:
        if OptionStatus.INITIALIZED in self.lower_put.status:
            return None
        trade_price = self.get_trade_price()
        if self.position_type == OptionPositionType.SHORT:
            return trade_price
        else:
            return float(decimalize_2(self._wing_width()) - decimalize_2(trade_price))

    @property
    def max_loss(self) -> float | None:
        if OptionStatus.INITIALIZED in self.lower_put.status:
            return None
        trade_price = self.get_trade_price()
        if self.position_type == OptionPositionType.SHORT:
            return float(decimalize_2(self._wing_width()) - decimalize_2(trade_price))
        else:
            return trade_price

    def get_required_margin(self, quantity: int) -> float:
        if self.position_type == OptionPositionType.LONG:
            return 0.0
        max_loss = float(decimalize_2(self._wing_width()) - decimalize_2(self.price))
        return max_loss * 100 * abs(quantity)

    def get_price_history(self) -> list[dict]:
        if (OptionStatus.TRADE_IS_OPEN not in self.lower_put.status
                and OptionStatus.TRADE_IS_CLOSED not in self.lower_put.status):
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        if OptionStatus.TRADE_IS_CLOSED in self.lower_put.status:
            last_date = self.lower_put.trade_close_info.date
        else:
            last_date = self.lower_put.quote_datetime

        trade_price   = self.get_trade_price()
        open_qty      = abs(self.lower_put.trade_open_info.quantity)
        close_records = self.lower_put.trade_close_records

        lp_updates = self.lower_put.updates
        up_updates = self.upper_put.updates
        lc_updates = self.lower_call.updates
        uc_updates = self.upper_call.updates

        keys = [k for k in lp_updates if k <= last_date]

        history = []
        for k in keys:
            lpu = lp_updates[k]
            upu = up_updates[k]
            lcu = lc_updates[k]
            ucu = uc_updates[k]

            price = self._calculate_price(
                lower_put_price=round(float(lpu['price']), 2),
                upper_put_price=round(float(upu['price']), 2),
                lower_call_price=round(float(lcu['price']), 2),
                upper_call_price=round(float(ucu['price']), 2),
            )

            closes_so_far          = sum(r.quantity for r in close_records if r.date <= k)
            remaining_qty          = open_qty - closes_so_far
            open_premium_allocated = abs(trade_price) * 100 * remaining_qty

            pnl     = round((price - trade_price) * 100 * remaining_qty, 2)
            pnl_pct = round(pnl / open_premium_allocated, 4) if open_premium_allocated != 0 else 0.0

            def _net_greek(lp_val, up_val, lc_val, uc_val):
                if any(v is None for v in (lp_val, up_val, lc_val, uc_val)):
                    return None
                if self.position_type == OptionPositionType.SHORT:
                    # long wings (+), short body (-)
                    return (lp_val + uc_val) - (up_val + lc_val)
                else:
                    # short wings (-), long body (+)
                    return (up_val + lc_val) - (lp_val + uc_val)

            def _avg_iv(*vals):
                non_none = [v for v in vals if v is not None]
                return sum(non_none) / len(non_none) if non_none else None

            history.append({
                'quote_datetime': k,
                'price':      price,
                'spot_price': lpu.get('spot_price'),
                'pnl':        pnl,
                'pnl_pct':    pnl_pct,
                'delta': _net_greek(lpu.get('delta'),  upu.get('delta'),  lcu.get('delta'),  ucu.get('delta')),
                'gamma': _net_greek(lpu.get('gamma'),  upu.get('gamma'),  lcu.get('gamma'),  ucu.get('gamma')),
                'theta': _net_greek(lpu.get('theta'),  upu.get('theta'),  lcu.get('theta'),  ucu.get('theta')),
                'vega':  _net_greek(lpu.get('vega'),   upu.get('vega'),   lcu.get('vega'),   ucu.get('vega')),
                'rho':   _net_greek(lpu.get('rho'),    upu.get('rho'),    lcu.get('rho'),    ucu.get('rho')),
                'iv':    _avg_iv(lpu.get('implied_volatility'), upu.get('implied_volatility'),
                                 lcu.get('implied_volatility'), ucu.get('implied_volatility')),
            })

        return history