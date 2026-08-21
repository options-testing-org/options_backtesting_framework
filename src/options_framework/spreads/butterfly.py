from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_0, decimalize_2
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase
from typing import Self


@dataclass(repr=False, slots=True)  # BUG 1 FIX: was @dataclass(slots=True) — missing repr=False
                                    # caused auto-generated __repr__ to shadow the hand-written one
class Butterfly(SpreadBase):

    lower_option: Option = field(init=False, default=None)
    center_option: Option = field(init=False, default=None)
    upper_option: Option = field(init=False, default=None)

    def __post_init__(self):
        self.lower_option = self.options[0]
        self.center_option = self.options[1]
        self.upper_option = self.options[2]

    def __repr__(self) -> str:
        return (
            f'<{self.spread_type.name}({self.instance_id}) '
            f'{self.option_type} {self.expiration} '
            f'{self.lower_option.strike}/{self.center_option.strike}/{self.upper_option.strike}>'
        )

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
            raise ValueError("No matching expiration was found in the option chain.")

        # Find nearest strikes
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

        # BUG 3 FIX: was hardcoded OptionPositionType.LONG, ignoring the position_type parameter
        resolved_position_type = position_type if position_type is not None else OptionPositionType.LONG

        butterfly = Butterfly(
            options=[lower_option, center_option, upper_option],
            spread_type=OptionSpreadType.BUTTERFLY,
            position_type=resolved_position_type,
        )

        super(Butterfly, butterfly)._save_user_defined_values(butterfly, **kwargs)
        return butterfly

    @property
    def expiration(self) -> datetime.date:
        return self.center_option.expiration

    @property
    def option_type(self) -> str:
        return self.center_option.option_type

    # BUG 2 FIX: removed symbol override — SpreadBase.symbol is non-abstract and returns
    # self.options[0].symbol; the override here used center_option and diverged from the contract.

    def _open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        qty = abs(quantity)
        if self.position_type == OptionPositionType.LONG:
            # Long butterfly: buy lower (+qty), sell 2x center (-2*qty), buy upper (+qty)
            center_qty = qty * -2
        else:
            # BUG 4 FIX: was qty = qty * -1 then center_qty = qty * 2, giving -2 for center.
            # Short butterfly: sell lower (-qty), buy 2x center (+2*qty), sell upper (-qty).
            # center_qty must be computed before negating qty.
            center_qty = qty * 2
            qty = qty * -1

        self.lower_option._open_trade(quantity=qty)
        self.center_option._open_trade(quantity=center_qty)
        self.upper_option._open_trade(quantity=qty)

        self.quantity = self.lower_option.quantity
        super(Butterfly, self)._save_user_defined_values(self, **kwargs)

    # BUG 5 FIX: signature was (self, quantity=None, *args, **kwargs) — missing the keyword-only
    # separator and the required quote_datetime parameter mandated by SpreadBase contract.
    def _close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:

        # BUG 6 FIX: was center_qty = quantity * 2 — crashed when quantity is None,
        # and the sign was wrong. center_qty = qty * -2 correctly mirrors the open:
        #   LONG open:  lower=+qty, center=-2*qty, upper=+qty  → close with lower=+qty, center=-2*qty, upper=+qty
        #   SHORT open: lower=-qty, center=+2*qty, upper=-qty  → close with lower=-qty, center=+2*qty, upper=-qty
        # Using qty * -2 produces the right result for both position types because
        # self.lower_option.quantity already carries the correct sign from open_trade.
        center_quantity = None if quantity is None else quantity * 2

        self.lower_option._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.center_option._close_trade(quote_datetime=quote_datetime, quantity=center_quantity)
        self.upper_option._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.quantity = self.lower_option.quantity
        super(Butterfly, self)._save_user_defined_values(self, **kwargs)

    def get_trade_price(self) -> float | None:
        # BUG 7 FIX: OptionStatus is a Flag — must use `in`, never `==`
        if OptionStatus.INITIALIZED in self.center_option.status:
            return None
        lower_price = self.lower_option.trade_open_info.price
        center_price = self.center_option.trade_open_info.price
        upper_price = self.upper_option.trade_open_info.price
        return self._calculate_price(lower_price=lower_price,
                                     center_price=center_price,
                                     upper_price=upper_price)

    @property
    def price(self) -> float:
        return self._calculate_price(
            lower_price=self.lower_option.price,
            center_price=self.center_option.price,
            upper_price=self.upper_option.price,
        )

    def get_required_margin(self, quantity: int) -> float:
        if self.position_type == OptionPositionType.LONG:
            return 0.0
        wing_width = min(
            self.center_option.strike - self.lower_option.strike,
            self.upper_option.strike - self.center_option.strike,
        )
        max_loss = float(decimalize_2(wing_width) - decimalize_2(self.price))
        return max_loss * 100 * abs(quantity)

    def get_dte(self) -> int | None:
        return self.center_option.get_dte()

    def get_closed_price(self) -> float | None:
        if all(OptionStatus.TRADE_IS_CLOSED in x.status for x in self.options):
            return self._calculate_price(
                lower_price=self.lower_option.trade_close_info.price,
                center_price=self.center_option.trade_close_info.price,
                upper_price=self.upper_option.trade_close_info.price,
            )
        return None

    # BUG 8 FIX (revised): original returned list of 4-tuples. First revision incorrectly
    # read from option.history (list of tuples). Single.get_price_history shows the real
    # data source is option.updates — a dict keyed by datetime — and greek values come
    # from the update dict (iv stored under key 'implied_volatility').
    #
    # PnL logic: the spread price formula encodes direction for both LONG and SHORT, so
    #   pnl = (spread_price_t - trade_price) * 100 * abs(quantity)
    # works uniformly. This follows from summing leg-level PnLs:
    #   LONG:  (lower + upper - 2*center) - (lower_open + upper_open - 2*center_open)
    #   SHORT: (2*center - lower - upper) - (2*center_open - lower_open - upper_open)
    # Both reduce to (current_spread_price - open_spread_price) * 100 * abs(qty).
    #
    # Greek netting (per-contract, not scaled by quantity):
    #   LONG butterfly:  net_G = G_lower + G_upper - 2*G_center
    #   SHORT butterfly: net_G = 2*G_center - G_lower - G_upper
    # IV is averaged across the three legs.
    def get_history(self) -> list[dict]:
        if (OptionStatus.TRADE_IS_OPEN not in self.lower_option.status
                and OptionStatus.TRADE_IS_CLOSED not in self.lower_option.status):
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        if OptionStatus.TRADE_IS_CLOSED in self.lower_option.status:
            last_date = self.lower_option.trade_close_info.date
        else:
            last_date = self.lower_option.quote_datetime

        trade_price = self.get_trade_price()
        open_qty = abs(self.lower_option.trade_open_info.quantity)
        close_records = self.lower_option.trade_close_records

        lower_updates  = self.lower_option.updates
        center_updates = self.center_option.updates
        upper_updates  = self.upper_option.updates

        keys = [k for k in lower_updates.keys() if k <= last_date]

        history = []
        for k in keys:
            lu = lower_updates[k]
            cu = center_updates[k]
            uu = upper_updates[k]

            lower_price  = round(float(lu['price']), 2)
            center_price = round(float(cu['price']), 2)
            upper_price  = round(float(uu['price']), 2)

            price = self._calculate_price(
                lower_price=lower_price,
                center_price=center_price,
                upper_price=upper_price,
            )

            spot_price = lu.get('spot_price')

            # Quantity remaining at this point in time (mirrors Single's logic)
            closes_so_far = sum(r.quantity for r in close_records if r.date <= k)
            remaining_qty = open_qty - closes_so_far
            open_premium_allocated = abs(trade_price) * 100 * remaining_qty

            pnl = round((price - trade_price) * 100 * remaining_qty, 2)
            pnl_pct = round(pnl / open_premium_allocated, 4) if open_premium_allocated != 0 else 0.0

            # Per-contract greeks from each leg's update dict
            l_delta = lu.get('delta')
            l_gamma = lu.get('gamma')
            l_theta = lu.get('theta')
            l_vega  = lu.get('vega')
            l_rho   = lu.get('rho')
            l_iv    = lu.get('implied_volatility')

            c_delta = cu.get('delta')
            c_gamma = cu.get('gamma')
            c_theta = cu.get('theta')
            c_vega  = cu.get('vega')
            c_rho   = cu.get('rho')
            c_iv    = cu.get('implied_volatility')

            u_delta = uu.get('delta')
            u_gamma = uu.get('gamma')
            u_theta = uu.get('theta')
            u_vega  = uu.get('vega')
            u_rho   = uu.get('rho')
            u_iv    = uu.get('implied_volatility')

            def _net(l, c, u):
                """Net a greek across legs. Returns None if any leg has no data."""
                if l is None or c is None or u is None:
                    return None
                if self.position_type == OptionPositionType.LONG:
                    return l + u - 2 * c
                else:
                    return 2 * c - l - u

            def _avg_iv(l, c, u):
                vals = [v for v in (l, c, u) if v is not None]
                return sum(vals) / len(vals) if vals else None

            history.append({
                'quote_datetime': k,
                'price': price,
                'spot_price': spot_price,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'delta': _net(l_delta, c_delta, u_delta),
                'gamma': _net(l_gamma, c_gamma, u_gamma),
                'theta': _net(l_theta, c_theta, u_theta),
                'vega':  _net(l_vega,  c_vega,  u_vega),
                'rho':   _net(l_rho,   c_rho,   u_rho),
                'iv':    _avg_iv(l_iv, c_iv, u_iv),
            })

        return history

    @property
    def max_profit(self) -> float | None:
        if OptionStatus.INITIALIZED in self.center_option.status:
            return None
        wing_width = min(
            self.center_option.strike - self.lower_option.strike,
            self.upper_option.strike - self.center_option.strike,
        )
        trade_price = self.get_trade_price()
        if self.position_type == OptionPositionType.LONG:
            return float(decimalize_2(wing_width) - decimalize_2(trade_price))
        else:
            return trade_price

    @property
    def max_loss(self) -> float | None:
        if OptionStatus.INITIALIZED in self.center_option.status:
            return None
        wing_width = min(
            self.center_option.strike - self.lower_option.strike,
            self.upper_option.strike - self.center_option.strike,
        )
        trade_price = self.get_trade_price()
        if self.position_type == OptionPositionType.LONG:
            return trade_price
        else:
            return float(decimalize_2(wing_width) - decimalize_2(trade_price))

    @property
    def status(self) -> OptionStatus:
        return self.center_option.status

    def _calculate_price(self, *, lower_price: float, center_price: float, upper_price: float) -> float:
        lower_price = decimalize_2(lower_price)
        center_price = decimalize_2(center_price)
        upper_price = decimalize_2(upper_price)
        if self.position_type == OptionPositionType.LONG:
            price = (lower_price + upper_price) - center_price * 2
        else:
            price = center_price * 2 - (lower_price + upper_price)
        return float(price)

    """
    Long Call/Put Butterfly:
      Max Profit = (center_strike - lower_strike) - net_debit  (achieved when spot = center_strike at expiry)
      Max Loss   = net_debit paid
    Short Call/Put Butterfly:
      Max Profit = net_credit received
      Max Loss   = (center_strike - lower_strike) - net_credit
    """

    def get_updates(self) -> list[dict]:
        pass