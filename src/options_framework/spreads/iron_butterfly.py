from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase
from typing import Self


@dataclass(repr=False, slots=True)
class IronButterfly(SpreadBase):

    lower_put: Option  = field(init=False, default=None)
    center_put: Option = field(init=False, default=None)
    center_call: Option = field(init=False, default=None)
    upper_call: Option  = field(init=False, default=None)

    def __post_init__(self):
        self.lower_put  = self.options[0]
        self.center_put = self.options[1]
        self.center_call = self.options[2]
        self.upper_call  = self.options[3]

    def __repr__(self) -> str:
        return (
            f'<{self.spread_type.name}({self.instance_id}) '
            f'{self.expiration} '
            f'{self.lower_put.strike}/{self.center_put.strike}/{self.upper_call.strike}>'
        )

    @classmethod
    def create(cls,
               option_chain: OptionChain,
               expiration: datetime.date = None,
               center_strike: int | float = None,
               lower_strike: int | float = None,
               upper_strike: int | float = None,
               position_type: OptionPositionType = None,
               *args, **kwargs) -> Self:

        if center_strike == lower_strike or center_strike == upper_strike:
            raise ValueError("Cannot open an iron butterfly if the wings are the same strike as the center strike.")
        if lower_strike > center_strike:
            raise ValueError("Lower strike must be lower than the center strike.")
        if upper_strike < center_strike:
            raise ValueError("Upper strike must be higher than the center strike.")

        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            raise ValueError("No matching expiration was found in the option chain.")

        expiration_strikes = option_chain.expiration_strikes[expiration].copy()
        all_options = [o for o in option_chain.options if o['expiration'] == expiration].copy()
        puts  = [o for o in all_options if o['option_type'] == 'put']
        calls = [o for o in all_options if o['option_type'] == 'call']

        center_strike = min(expiration_strikes, key=lambda x: abs(x - center_strike))
        lower_strike  = min(expiration_strikes, key=lambda x: abs(x - lower_strike))
        upper_strike  = min(expiration_strikes, key=lambda x: abs(x - upper_strike))

        lower_put  = Option(**next(o for o in puts  if o['strike'] == lower_strike))
        center_put = Option(**next(o for o in puts  if o['strike'] == center_strike))
        center_call = Option(**next(o for o in calls if o['strike'] == center_strike))
        upper_call  = Option(**next(o for o in calls if o['strike'] == upper_strike))

        resolved_position_type = position_type if position_type is not None else OptionPositionType.SHORT

        iron_butterfly = IronButterfly(
            options=[lower_put, center_put, center_call, upper_call],
            spread_type=OptionSpreadType.IRON_BUTTERFLY,
            position_type=resolved_position_type,
        )

        super(IronButterfly, iron_butterfly)._save_user_defined_values(iron_butterfly, **kwargs)
        return iron_butterfly

    @property
    def expiration(self) -> datetime.date:
        return self.center_put.expiration

    @property
    def center_strike(self) -> int | float:
        return self.center_put.strike

    def open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        qty = abs(quantity)
        if self.position_type == OptionPositionType.SHORT:
            # SHORT iron butterfly: long wings, short center
            wing_qty   =  qty
            center_qty = -qty
        else:
            # LONG iron butterfly: short wings, long center
            wing_qty   = -qty
            center_qty =  qty

        self.lower_put.open_trade(quantity=wing_qty)
        self.center_put.open_trade(quantity=center_qty)
        self.center_call.open_trade(quantity=center_qty)
        self.upper_call.open_trade(quantity=wing_qty)

        self.quantity = self.lower_put.quantity
        super(IronButterfly, self)._save_user_defined_values(self, **kwargs)

    def close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        self.lower_put.close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.center_put.close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.center_call.close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.upper_call.close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.quantity = self.lower_put.quantity
        super(IronButterfly, self)._save_user_defined_values(self, **kwargs)

    def _calculate_price(self, *,
                         lower_put_price: float,
                         center_put_price: float,
                         center_call_price: float,
                         upper_call_price: float) -> float:
        lp = decimalize_2(lower_put_price)
        cp = decimalize_2(center_put_price)
        cc = decimalize_2(center_call_price)
        uc = decimalize_2(upper_call_price)
        if self.position_type == OptionPositionType.SHORT:
            # Net credit received: center premiums minus wing premiums
            price = (cp + cc) - (lp + uc)
        else:
            # Net debit paid: wing premiums minus center premiums
            price = (lp + uc) - (cp + cc)
        return float(price)

    @property
    def price(self) -> float:
        return self._calculate_price(
            lower_put_price=self.lower_put.price,
            center_put_price=self.center_put.price,
            center_call_price=self.center_call.price,
            upper_call_price=self.upper_call.price,
        )

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED in self.center_put.status:
            return None
        return self._calculate_price(
            lower_put_price=self.lower_put.trade_open_info.price,
            center_put_price=self.center_put.trade_open_info.price,
            center_call_price=self.center_call.trade_open_info.price,
            upper_call_price=self.upper_call.trade_open_info.price,
        )

    def get_closed_price(self) -> float | None:
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            return self._calculate_price(
                lower_put_price=self.lower_put.trade_close_info.price,
                center_put_price=self.center_put.trade_close_info.price,
                center_call_price=self.center_call.trade_close_info.price,
                upper_call_price=self.upper_call.trade_close_info.price,
            )
        return None

    def get_dte(self) -> int | None:
        return self.center_put.get_dte()

    @property
    def max_profit(self) -> float | None:
        if OptionStatus.INITIALIZED in self.center_put.status:
            return None
        trade_price = self.get_trade_price()
        wing_width = max(
            self.center_put.strike - self.lower_put.strike,
            self.upper_call.strike - self.center_put.strike,
        )
        if self.position_type == OptionPositionType.SHORT:
            return trade_price
        else:
            return float(decimalize_2(wing_width) - decimalize_2(trade_price))

    @property
    def max_loss(self) -> float | None:
        if OptionStatus.INITIALIZED in self.center_put.status:
            return None
        trade_price = self.get_trade_price()
        wing_width = max(
            self.center_put.strike - self.lower_put.strike,
            self.upper_call.strike - self.center_put.strike,
        )
        if self.position_type == OptionPositionType.SHORT:
            return float(decimalize_2(wing_width) - decimalize_2(trade_price))
        else:
            return trade_price

    def get_required_margin(self, quantity: int) -> float:
        if self.position_type == OptionPositionType.LONG:
            return 0.0
        wing_width = max(
            self.center_put.strike - self.lower_put.strike,
            self.upper_call.strike - self.center_put.strike,
        )
        max_loss = float(decimalize_2(wing_width) - decimalize_2(self.price))
        return max_loss * 100 * abs(quantity)

    def get_price_history(self) -> list[dict]:
        if (OptionStatus.TRADE_IS_OPEN not in self.lower_put.status
                and OptionStatus.TRADE_IS_CLOSED not in self.lower_put.status):
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        if OptionStatus.TRADE_IS_CLOSED in self.lower_put.status:
            last_date = self.lower_put.trade_close_info.date
        else:
            last_date = self.lower_put.quote_datetime

        trade_price = self.get_trade_price()
        open_qty    = abs(self.lower_put.trade_open_info.quantity)
        close_records = self.lower_put.trade_close_records

        lp_updates = self.lower_put.updates
        cp_updates = self.center_put.updates
        cc_updates = self.center_call.updates
        uc_updates = self.upper_call.updates

        keys = [k for k in lp_updates if k <= last_date]

        history = []
        for k in keys:
            lpu = lp_updates[k]
            cpu = cp_updates[k]
            ccu = cc_updates[k]
            ucu = uc_updates[k]

            price = self._calculate_price(
                lower_put_price=round(float(lpu['price']), 2),
                center_put_price=round(float(cpu['price']), 2),
                center_call_price=round(float(ccu['price']), 2),
                upper_call_price=round(float(ucu['price']), 2),
            )

            closes_so_far = sum(r.quantity for r in close_records if r.date <= k)
            remaining_qty = open_qty - closes_so_far
            open_premium_allocated = abs(trade_price) * 100 * remaining_qty

            pnl     = round((price - trade_price) * 100 * remaining_qty, 2)
            pnl_pct = round(pnl / open_premium_allocated, 4) if open_premium_allocated != 0 else 0.0

            def _net_greek(lp_val, cp_val, cc_val, uc_val):
                if any(v is None for v in (lp_val, cp_val, cc_val, uc_val)):
                    return None
                if self.position_type == OptionPositionType.SHORT:
                    # long wings (+), short center (-)
                    return (lp_val + uc_val) - (cp_val + cc_val)
                else:
                    # short wings (-), long center (+)
                    return (cp_val + cc_val) - (lp_val + uc_val)

            def _avg_iv(*vals):
                non_none = [v for v in vals if v is not None]
                return sum(non_none) / len(non_none) if non_none else None

            history.append({
                'quote_datetime': k,
                'price':      price,
                'spot_price': lpu.get('spot_price'),
                'pnl':        pnl,
                'pnl_pct':    pnl_pct,
                'delta': _net_greek(lpu.get('delta'), cpu.get('delta'), ccu.get('delta'), ucu.get('delta')),
                'gamma': _net_greek(lpu.get('gamma'), cpu.get('gamma'), ccu.get('gamma'), ucu.get('gamma')),
                'theta': _net_greek(lpu.get('theta'), cpu.get('theta'), ccu.get('theta'), ucu.get('theta')),
                'vega':  _net_greek(lpu.get('vega'),  cpu.get('vega'),  ccu.get('vega'),  ucu.get('vega')),
                'rho':   _net_greek(lpu.get('rho'),   cpu.get('rho'),   ccu.get('rho'),   ucu.get('rho')),
                'iv':    _avg_iv(lpu.get('implied_volatility'), cpu.get('implied_volatility'),
                                 ccu.get('implied_volatility'), ucu.get('implied_volatility')),
            })

        return history