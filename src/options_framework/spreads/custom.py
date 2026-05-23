from dataclasses import dataclass, field
import datetime
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionSpreadType, OptionStatus
from options_framework.spreads.spread_base import SpreadBase
from typing import Self


@dataclass(repr=False, slots=True)
class Custom(SpreadBase):

    def __post_init__(self):
        pass  # no named leg references — options list is the interface

    def __repr__(self) -> str:
        legs = '/'.join(
            f"{'+'if o.quantity > 0 else ''}{o.quantity}x{o.strike}{o.option_type[0].upper()}"
            for o in self.options
        )
        return f'<{self.spread_type.name}({self.instance_id}) {legs}>'

    @classmethod
    def create(cls,
               option_chain: OptionChain = None,
               options: list[Option] = None,
               quantities: list[int] = None,
               **kwargs) -> Self:

        if options is None or len(options) == 0:
            raise ValueError("options must be a non-empty list of Option objects.")
        if quantities is None or len(quantities) != len(options):
            raise ValueError("quantities must be a list of the same length as options.")

        custom = Custom(
            options=options,
            spread_type=OptionSpreadType.CUSTOM,
        )

        for option, qty in zip(options, quantities):
            option._open_trade(quantity=qty)

        custom.quantity = options[0].quantity
        super(Custom, custom)._save_user_defined_values(custom, **kwargs)
        return custom

    def _open_trade(self, *, quantity: int = 1, **kwargs: dict) -> None:
        raise RuntimeError(
            "Custom spreads are opened via Custom.create(). "
            "Pass options and quantities there to open the trade."
        )

    def _close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        for option in self.options:
            option._close_trade(quantity=quantity, quote_datetime=quote_datetime)
        self.quantity = self.options[0].quantity
        super(Custom, self)._save_user_defined_values(self, **kwargs)

    def _leg_sign(self, option: Option) -> int:
        """Returns +1 if the leg was opened long, -1 if short."""
        return 1 if option.trade_open_info.quantity > 0 else -1

    def _calculate_price(self, prices: list[float]) -> float:
        """Net spread price: sum of signed option prices."""
        return float(sum(
            decimalize_2(p) * self._leg_sign(o)
            for p, o in zip(prices, self.options)
        ))

    @property
    def price(self) -> float:
        return self._calculate_price([o.price for o in self.options])

    def get_trade_price(self) -> float | None:
        if any(OptionStatus.INITIALIZED in o.status for o in self.options):
            return None
        return self._calculate_price(
            [o.trade_open_info.price for o in self.options]
        )

    def get_closed_price(self) -> float | None:
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            return self._calculate_price(
                [o.trade_close_info.price for o in self.options]
            )
        return None

    def get_dte(self) -> int | None:
        dtes = [o.get_dte() for o in self.options if o.get_dte() is not None]
        return min(dtes) if dtes else None

    @property
    def max_profit(self) -> float | None:
        return None

    @property
    def max_loss(self) -> float | None:
        return None

    def get_required_margin(self, quantity: int) -> float | None:
        return None

    def get_price_history(self) -> list[dict]:
        first = self.options[0]
        if (OptionStatus.TRADE_IS_OPEN not in first.status
                and OptionStatus.TRADE_IS_CLOSED not in first.status):
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        if OptionStatus.TRADE_IS_CLOSED in first.status:
            last_date = first.trade_close_info.date
        else:
            last_date = first.quote_datetime

        trade_price   = self.get_trade_price()
        open_qty      = abs(first.trade_open_info.quantity)
        close_records = first.trade_close_records

        all_updates = [o.updates for o in self.options]
        keys = sorted(k for k in all_updates[0] if k <= last_date)

        history = []
        for k in keys:
            row_updates = [u[k] for u in all_updates]

            price = self._calculate_price(
                [round(float(u['price']), 2) for u in row_updates]
            )

            closes_so_far          = sum(r.quantity for r in close_records if r.date <= k)
            remaining_qty          = open_qty - closes_so_far
            open_premium_allocated = abs(trade_price) * 100 * remaining_qty if trade_price else 0

            pnl     = round((price - trade_price) * 100 * remaining_qty, 2) if trade_price is not None else 0.0
            pnl_pct = round(pnl / open_premium_allocated, 4) if open_premium_allocated != 0 else 0.0

            def _net_greek(greek: str) -> float | None:
                vals = [u.get(greek) for u in row_updates]
                if any(v is None for v in vals):
                    return None
                return sum(v * self._leg_sign(o) for v, o in zip(vals, self.options))

            def _avg_iv() -> float | None:
                vals = [u.get('implied_volatility') for u in row_updates]
                non_none = [v for v in vals if v is not None]
                return sum(non_none) / len(non_none) if non_none else None

            history.append({
                'quote_datetime': k,
                'price':      price,
                'spot_price': row_updates[0].get('spot_price'),
                'pnl':        pnl,
                'pnl_pct':    pnl_pct,
                'delta': _net_greek('delta'),
                'gamma': _net_greek('gamma'),
                'theta': _net_greek('theta'),
                'vega':  _net_greek('vega'),
                'rho':   _net_greek('rho'),
                'iv':    _avg_iv(),
            })

        return history