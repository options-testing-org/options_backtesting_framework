from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Self

from .spread_base import SpreadBase
from ..option import Option
from ..option_chain import OptionChain
from ..option_types import OptionSpreadType, OptionStatus, OptionPositionType
from ..utils.helpers import decimalize_4, decimalize_2, decimalize_0


# noinspection PyUnresolvedReferences
@dataclass(repr=False, slots=True)
class Strangle(SpreadBase):

    call: Option = field(default=None)
    put: Option = field(default=None)

    @classmethod
    def create(cls, option_chain: OptionChain,
               expiration: datetime.date = None,
               call_strike: float | int = None,
               put_strike: float | int = None,
               *args, **kwargs) -> Self:

        if call_strike <= put_strike:
            raise ValueError("Call strike must be greater than put strike for a strangle.")

        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain."
            raise ValueError(message)

        # Find nearest matching strikes for this expiration
        strikes = option_chain.expiration_strikes[expiration].copy()
        options = [o for o in option_chain.options if o['expiration'] == expiration]

        selected_call_strike = min(strikes, key=lambda x: abs(x - call_strike))
        selected_put_strike = min(strikes, key=lambda x: abs(x - put_strike))

        if selected_call_strike == selected_put_strike:
            raise ValueError("Call and put strikes resolved to the same strike. Use a wider spread.")

        try:
            call_data = next(o for o in options if o['option_type'] == 'call' and o['strike'] == selected_call_strike)
            put_data = next(o for o in options if o['option_type'] == 'put' and o['strike'] == selected_put_strike)
        except StopIteration:
            raise ValueError("Cannot create strangle with these strikes and expiration.")

        put_option = Option(**put_data)
        call_option = Option(**call_data)

        strangle = Strangle(options=[call_option, put_option], spread_type=OptionSpreadType.STRANGLE)

        # save any kwargs that were sent to user_defined dict
        super(Strangle, strangle)._save_user_defined_values(strangle, **kwargs)
        return strangle


    def __post_init__(self):
        if len(self.options) != 2:
            raise ValueError("A Strangle must have two options.")
        if self.options[0].option_type == self.options[1].option_type:
            raise ValueError("A Strangle must have one put and one call option.")
        call_option = next(o for o in self.options if o.option_type == 'call')
        put_option = next(o for o in self.options if o.option_type == 'put')
        if call_option.strike <= put_option.strike:
            raise ValueError("Strangle call strike must be greater than put strike.")
        if call_option.position_type is not None and put_option.position_type is not None:
            if call_option.position_type != put_option.position_type:
                raise ValueError("Strangle options must both be long or short.")
        if call_option.quantity != put_option.quantity:
            raise ValueError("Strangle options must have the same quantity")
        if call_option.symbol != put_option.symbol:
            raise ValueError("Strangle options must be for the same equity")
        if call_option.expiration != put_option.expiration:
            raise ValueError("Strangle options must have the same expiration")
        if self.spread_type != OptionSpreadType.STRANGLE:
            raise ValueError("Strangle must have spread type of STRANGLE")

        self.call = call_option
        self.put = put_option


    def __repr__(self):
        long_short = '' if self.position_type is None else f' {self.position_type.name}'
        return f'<{self.spread_type.name}({self.instance_id}) {self.symbol} {self.strike} {self.expiration}{long_short}>'


    def _open_trade(self, quantity: int = 1, *args, **kwargs: dict) -> None:
        self.call._open_trade(quantity=quantity)
        self.put._open_trade(quantity=quantity)
        self.position_type = self.call.position_type
        self.quantity = self.call.quantity

        super(Strangle, self)._save_user_defined_values(self, **kwargs)


    def _close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        self.call._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.put._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.quantity = self.call.quantity

        super(Strangle, self)._save_user_defined_values(self, **kwargs)


    def get_required_margin(self, quantity: int) -> float:
        margin = 0
        position_type = OptionPositionType.LONG if quantity > 0 else OptionPositionType.SHORT
        if position_type == OptionPositionType.SHORT:
            legs = [self.call, self.put]
            leg_margins = []
            leg_premiums = []
            for option in legs:
                pct_20 = decimalize_4(option.spot_price * 0.2)
                pct_10 = decimalize_4(option.spot_price * 0.1)
                otm_amount = decimalize_4(option.spot_price - option.strike) if option.otm() else decimalize_0(0)
                price = decimalize_2(option.price)
                calc1 = pct_20 - otm_amount + price
                calc2 = pct_10 + price
                calc3 = Decimal(1) + price
                leg_margin = float(max(calc1, calc2, calc3)) * 100 * abs(quantity)
                leg_margins.append(leg_margin)
                leg_premiums.append(float(price) * 100 * abs(quantity))

            # larger margin plus the other leg's premium
            if leg_margins[0] >= leg_margins[1]:
                margin = leg_margins[0] + leg_premiums[1]
            else:
                margin = leg_margins[1] + leg_premiums[0]

            margin = round(margin, 2)
        return margin


    @property
    def price(self) -> float:
        price = decimalize_2(self.call.price) + decimalize_2(self.put.price)
        return float(price)


    def get_dte(self) -> int | None:
        return self.call.get_dte()


    def get_trade_price(self) -> float | None:
        if all(OptionStatus.INITIALIZED in o.status for o in self.options):
            return None
        else:
            return self.call.trade_open_info.price + self.put.trade_open_info.price


    def get_closed_price(self) -> float | None:
        if OptionStatus.TRADE_IS_CLOSED not in self.call.status:
            return None
        price = decimalize_2(self.call.trade_close_info.price) + decimalize_2(self.put.trade_close_info.price)
        return float(price)


    @property
    def strike(self) -> int | float:
        return self.call.strike


    @property
    def expiration(self) -> datetime.date:
        return self.call.expiration


    @property
    def max_profit(self) -> float | None:
        if self.position_type == OptionPositionType.SHORT:
            return self.get_trade_premium() * -1
        else:
            return None


    @property
    def max_loss(self) -> float | None:
        if self.position_type == OptionPositionType.LONG:
            return self.get_trade_premium() * -1
        else:
            return None

    @property
    def status(self) -> OptionStatus:
        return self.call.status


    def get_history(self) -> list[dict]:
        if (OptionStatus.TRADE_IS_OPEN not in self.call.status
                and OptionStatus.TRADE_IS_CLOSED not in self.call.status):
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        if OptionStatus.TRADE_IS_CLOSED in self.call.status:
            last_date = self.call.trade_close_info.date
        else:
            last_date = self.call.quote_datetime

        call_open_price = self.call.trade_open_info.price
        call_open_qty = self.call.trade_open_info.quantity
        call_close_records = self.call.trade_close_records

        put_open_price = self.put.trade_open_info.price
        put_open_qty = self.put.trade_open_info.quantity
        put_close_records = self.put.trade_close_records

        keys = sorted(
            set(self.call.updates.keys()) & set(self.put.updates.keys())
        )
        keys = [k for k in keys if k <= last_date]

        history = []
        for k in keys:
            call_update = self.call.updates[k]
            put_update = self.put.updates[k]

            call_closes = sum(r.quantity for r in call_close_records if r.date <= k)
            call_remaining = abs(call_open_qty) - call_closes
            call_signed = call_remaining * (1 if call_open_qty > 0 else -1)
            call_price = round(float(call_update['price']), 2)
            call_pnl = round((call_price - call_open_price) * 100 * call_signed, 2)

            put_closes = sum(r.quantity for r in put_close_records if r.date <= k)
            put_remaining = abs(put_open_qty) - put_closes
            put_signed = put_remaining * (1 if put_open_qty > 0 else -1)
            put_price = round(float(put_update['price']), 2)
            put_pnl = round((put_price - put_open_price) * 100 * put_signed, 2)

            spread_price = round(call_price + put_price, 2)
            spread_pnl = round(call_pnl + put_pnl, 2)
            trade_price = abs(self.get_trade_price() or 0)
            open_premium = trade_price * 100 * call_remaining
            pnl_pct = round(spread_pnl / open_premium, 4) if open_premium != 0 else 0.0

            def net(field):
                cv = call_update.get(field)
                pv = put_update.get(field)
                return round(float(cv) + float(pv), 4) if cv is not None and pv is not None else None

            history.append({
                'quote_datetime': k,
                'price': spread_price,
                'spot_price': call_update.get('spot_price'),
                'pnl': spread_pnl,
                'pnl_pct': pnl_pct,
                'delta': net('delta'),
                'gamma': net('gamma'),
                'theta': net('theta'),
                'vega': net('vega'),
                'rho': net('rho'),
                'iv': net('implied_volatility'),
            })

        return history

    def get_updates(self) -> list[dict]:
        pass