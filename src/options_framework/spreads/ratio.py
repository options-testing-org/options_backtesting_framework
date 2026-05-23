from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase
from typing import Self


@dataclass(repr=False, slots=True)
class Ratio(SpreadBase):

    ratio: int           = field(default=2)
    long_option: Option  = field(init=False, default=None)
    short_option: Option = field(init=False, default=None)

    def __post_init__(self):
        self.long_option  = self.options[0]
        self.short_option = self.options[1]

    def __repr__(self) -> str:
        return (
            f'<{self.spread_type.name}({self.instance_id}) '
            f'{self.option_type} {self.expiration} '
            f'1x{self.long_option.strike}/{self.ratio}x{self.short_option.strike}>'
        )

    @classmethod
    def create(cls,
               option_chain: OptionChain,
               expiration: datetime.date = None,
               option_type: str = None,
               long_strike: int | float = None,
               short_strike: int | float = None,
               ratio: int = 2,
               *args, **kwargs) -> Self:

        if long_strike == short_strike:
            raise ValueError("long_strike and short_strike must be different.")
        if ratio < 2:
            raise ValueError("ratio must be at least 2.")

        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            raise ValueError("No matching expiration was found in the option chain.")

        expiration_strikes = option_chain.expiration_strikes[expiration].copy()
        options = [o for o in option_chain.options
                   if o['option_type'] == option_type and o['expiration'] == expiration].copy()

        long_strike  = min(expiration_strikes, key=lambda x: abs(x - long_strike))
        short_strike = min(expiration_strikes, key=lambda x: abs(x - short_strike))

        long_option  = Option(**next(o for o in options if o['strike'] == long_strike))
        short_option = Option(**next(o for o in options if o['strike'] == short_strike))

        ratio_spread = Ratio(
            options=[long_option, short_option],
            spread_type=OptionSpreadType.RATIO,
            ratio=ratio,
        )

        super(Ratio, ratio_spread)._save_user_defined_values(ratio_spread, **kwargs)
        return ratio_spread

    @property
    def expiration(self) -> datetime.date:
        return self.long_option.expiration

    @property
    def option_type(self) -> str:
        return self.long_option.option_type

    def _open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        qty = abs(quantity)
        self.long_option._open_trade(quantity=qty)
        self.short_option._open_trade(quantity=-qty * self.ratio)
        self.quantity = self.long_option.quantity
        super(Ratio, self)._save_user_defined_values(self, **kwargs)

    def _close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        short_qty = None if quantity is None else quantity * self.ratio
        self.long_option._close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.short_option._close_trade(quantity=short_qty, quote_datetime=quote_datetime)
        self.quantity = self.long_option.quantity
        super(Ratio, self)._save_user_defined_values(self, **kwargs)

    def _calculate_price(self, *, long_price: float, short_price: float) -> float:
        l = decimalize_2(long_price)
        s = decimalize_2(short_price)
        return float(l - self.ratio * s)

    @property
    def price(self) -> float:
        return self._calculate_price(
            long_price=self.long_option.price,
            short_price=self.short_option.price,
        )

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED in self.long_option.status:
            return None
        return self._calculate_price(
            long_price=self.long_option.trade_open_info.price,
            short_price=self.short_option.trade_open_info.price,
        )

    def get_closed_price(self) -> float | None:
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            return self._calculate_price(
                long_price=self.long_option.trade_close_info.price,
                short_price=self.short_option.trade_close_info.price,
            )
        return None

    def get_dte(self) -> int | None:
        return self.long_option.get_dte()

    @property
    def max_profit(self) -> float | None:
        return None

    @property
    def max_loss(self) -> float | None:
        return None

    def get_required_margin(self, quantity: int) -> float:
        return None

    def get_price_history(self) -> list[dict]:
        if (OptionStatus.TRADE_IS_OPEN not in self.long_option.status
                and OptionStatus.TRADE_IS_CLOSED not in self.long_option.status):
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        if OptionStatus.TRADE_IS_CLOSED in self.long_option.status:
            last_date = self.long_option.trade_close_info.date
        else:
            last_date = self.long_option.quote_datetime

        trade_price   = self.get_trade_price()
        open_qty      = abs(self.long_option.trade_open_info.quantity)
        close_records = self.long_option.trade_close_records

        long_updates  = self.long_option.updates
        short_updates = self.short_option.updates

        keys = [k for k in long_updates if k <= last_date]

        history = []
        for k in keys:
            lu = long_updates[k]
            su = short_updates[k]

            price = self._calculate_price(
                long_price=round(float(lu['price']), 2),
                short_price=round(float(su['price']), 2),
            )

            closes_so_far          = sum(r.quantity for r in close_records if r.date <= k)
            remaining_qty          = open_qty - closes_so_far
            open_premium_allocated = abs(trade_price) * 100 * remaining_qty if trade_price else 0

            pnl     = round((price - trade_price) * 100 * remaining_qty, 2) if trade_price is not None else 0.0
            pnl_pct = round(pnl / open_premium_allocated, 4) if open_premium_allocated != 0 else 0.0

            def _net_greek(long_val, short_val):
                if long_val is None or short_val is None:
                    return None
                return long_val - self.ratio * short_val

            def _avg_iv(long_val, short_val):
                vals = [v for v in (long_val, short_val) if v is not None]
                return sum(vals) / len(vals) if vals else None

            history.append({
                'quote_datetime': k,
                'price':      price,
                'spot_price': lu.get('spot_price'),
                'pnl':        pnl,
                'pnl_pct':    pnl_pct,
                'delta': _net_greek(lu.get('delta'),  su.get('delta')),
                'gamma': _net_greek(lu.get('gamma'),  su.get('gamma')),
                'theta': _net_greek(lu.get('theta'),  su.get('theta')),
                'vega':  _net_greek(lu.get('vega'),   su.get('vega')),
                'rho':   _net_greek(lu.get('rho'),    su.get('rho')),
                'iv':    _avg_iv(lu.get('implied_volatility'), su.get('implied_volatility')),
            })

        return history