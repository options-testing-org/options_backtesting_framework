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
    upper_put: Option = field(init=False, default=None)
    lower_call: Option = field(init=False, default=None)
    upper_call: Option  = field(init=False, default=None)

    def __post_init__(self):
        expirations = [options.expiration for options in self.options]
        if len(set(expirations)) != 1:
            raise ValueError("Option expiration must be the same for all options.")
        self.lower_put  = self.options[0]
        self.upper_put = self.options[1]
        self.lower_call = self.options[2]
        self.upper_call  = self.options[3]

    def __repr__(self) -> str:
        return (
            f'<{self.spread_type.name}({self.instance_id}) '
            f'{self.expiration} '
            f'{self.lower_put.strike}/{self.upper_put.strike}/{self.lower_call.strike}/{self.upper_call.strike}>'
        )

    @classmethod
    def create(cls,
               option_chain: OptionChain,
               expiration: datetime.date = None,
               center_strike: int | float = None,
               lower_put_strike: int | float = None,
               upper_call_strike: int | float = None,
               position_type: OptionPositionType = None,
               *args, **kwargs) -> Self:

        if center_strike == lower_put_strike or center_strike == upper_call_strike:
            raise ValueError("Cannot open an iron butterfly if the wings are the same strike as the center strike.")
        if lower_put_strike > center_strike:
            raise ValueError("Lower put strike must be lower than the center strike.")
        if upper_call_strike < center_strike:
            raise ValueError("Upper call strike must be higher than the center strike.")

        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            raise ValueError("No matching expiration was found in the option chain.")

        expiration_strikes = option_chain.expiration_strikes[expiration].copy()
        all_options = [o for o in option_chain.options if o['expiration'] == expiration].copy()
        puts  = [o for o in all_options if o['option_type'] == 'put']
        calls = [o for o in all_options if o['option_type'] == 'call']

        center_strike = min(expiration_strikes, key=lambda x: abs(x - center_strike))
        lower_put_strike  = min(expiration_strikes, key=lambda x: abs(x - lower_put_strike))
        upper_call_strike  = min(expiration_strikes, key=lambda x: abs(x - upper_call_strike))

        lower_put  = Option(**next(o for o in puts  if o['strike'] == lower_put_strike))
        upper_put = Option(**next(o for o in puts  if o['strike'] == center_strike))
        lower_call = Option(**next(o for o in calls if o['strike'] == center_strike))
        upper_call  = Option(**next(o for o in calls if o['strike'] == upper_call_strike))

        resolved_position_type = position_type if position_type is not None else OptionPositionType.SHORT

        iron_butterfly = IronButterfly(
            options=[lower_put, upper_put, lower_call, upper_call],
            spread_type=OptionSpreadType.IRON_BUTTERFLY,
            position_type=resolved_position_type,
        )

        super(IronButterfly, iron_butterfly)._save_user_defined_values(iron_butterfly, **kwargs)
        return iron_butterfly

    @property
    def expiration(self) -> datetime.date:
        return self.upper_put.expiration

    @property
    def center_strike(self) -> int | float:
        return self.upper_put.strike

    def _open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        qty = abs(quantity)
        if self.position_type == OptionPositionType.SHORT:
            # SHORT iron butterfly: long wings, short center
            wing_qty   =  qty
            center_qty = -qty
        else:
            # LONG iron butterfly: short wings, long center
            wing_qty   = -qty
            center_qty =  qty

        self.lower_put._open_trade(quantity=wing_qty)
        self.upper_put._open_trade(quantity=center_qty)
        self.lower_call._open_trade(quantity=center_qty)
        self.upper_call._open_trade(quantity=wing_qty)

        self.quantity = self.upper_put.quantity
        super(IronButterfly, self)._save_user_defined_values(self, **kwargs)

    def _close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        self.lower_put._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.upper_put._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.lower_call._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.upper_call._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.quantity = self.upper_put.quantity
        super(IronButterfly, self)._save_user_defined_values(self, **kwargs)

    def _calculate_price(self, *,
                         lower_put_price: float,
                         upper_put_price: float,
                         lower_call_price: float,
                         upper_call_price: float) -> float:
        lp = decimalize_2(lower_put_price)
        cp = decimalize_2(upper_put_price)
        cc = decimalize_2(lower_call_price)
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
            upper_put_price=self.upper_put.price,
            lower_call_price=self.lower_call.price,
            upper_call_price=self.upper_call.price,
        )

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED in self.upper_put.status:
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
        return self.upper_put.get_dte()

    @property
    def max_profit(self) -> float | None:
        if OptionStatus.INITIALIZED in self.upper_put.status:
            quantity = -1 if self.position_type == OptionPositionType.SHORT else 1
            
            wing_position_type = OptionPositionType.LONG if self.position_type == OptionPositionType.SHORT else OptionPositionType.SHORT
            center_position_type = self.position_type
            lower_put_price=self.lower_put.get_open_price(position_type=wing_position_type)
            upper_put_price=self.upper_put.get_open_price(position_type=center_position_type)
            lower_call_price=self.lower_call.get_open_price(position_type=center_position_type)
            upper_call_price=self.upper_call.get_open_price(position_type=wing_position_type)
        else:
            lower_put_price=self.lower_put.trade_open_info.price
            upper_put_price=self.upper_put.trade_open_info.price
            lower_call_price=self.lower_call.trade_open_info.price
            upper_call_price=self.upper_call.trade_open_info.price
            
            quantity = self.quantity
            
        
        price = self._calculate_price(lower_put_price=lower_put_price,
                                      upper_put_price=upper_put_price,
                                      lower_call_price=lower_call_price,
                                      upper_call_price=upper_call_price)
        
        if self.position_type == OptionPositionType.LONG:
            wing_width = max((self.upper_put.strike - self.lower_put.strike), (self.upper_call.strike - self.lower_call.strike))
            max_profit_value = (wing_width - abs(price)) * 100 * quantity
        else:
            max_profit_value = price * 100 * abs(quantity)
            
        return round(max_profit_value, 2)


    @property
    def max_loss(self) -> float | None:
        max_profit_value = self.max_profit
        max_width = max(
            self.upper_put.strike - self.lower_put.strike,
            self.upper_call.strike - self.lower_call.strike
        )
        max_loss_value = max_profit_value  - max_width * 100
        return round(abs(max_loss_value), 2)

    @property
    def status(self) -> OptionStatus:
        return self.upper_put.status

    def get_required_margin(self, quantity: int) -> float:
        if self.position_type == OptionPositionType.LONG:
            return 0.0
        wing_width = max(
            self.upper_put.strike - self.lower_put.strike,
            self.upper_call.strike - self.lower_call.strike,
        )
        required_margin = float(decimalize_2(wing_width) - decimalize_2(self.price)) * 100 * abs(quantity)
        return round(required_margin, 2)

    def get_history(self) -> list[dict]:
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
        cp_updates = self.upper_put.updates
        cc_updates = self.lower_call.updates
        uc_updates = self.upper_call.updates

        keys = sorted(
            set(lp_updates.keys()) & set(cp_updates.keys() & set(cc_updates.keys() & uc_updates.keys()))
        )
        keys = [k for k in keys if k <= last_date]

        history = []
        for k in keys:
            lpu = lp_updates[k]
            cpu = cp_updates[k]
            ccu = cc_updates[k]
            ucu = uc_updates[k]

            price = self._calculate_price(
                lower_put_price=round(float(lpu['price']), 2),
                upper_put_price=round(float(cpu['price']), 2),
                lower_call_price=round(float(ccu['price']), 2),
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

    def get_updates(self) -> list[dict]:
        pass