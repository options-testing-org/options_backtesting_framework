from dataclasses import dataclass, field

from options_framework.option_types import OptionPositionType, OptionSpreadType, OptionStatus
from options_framework.option_chain import OptionChain
from options_framework.spreads.spread_base import SpreadBase
from options_framework.utils.helpers import decimalize_2
from options_framework.option import Option
import datetime
from typing import Self

@dataclass(repr=False, slots=True)
class Vertical(SpreadBase):

    long_option: Option = field(default=None)
    short_option: Option = field(default=None)

    @classmethod
    def create(cls,
               option_chain: OptionChain,
               expiration: datetime.date = None,
               option_type: str = None,
               long_strike: int | float = None,
               short_strike: int | float = None,
               position_type: OptionPositionType = None,
               *args, **kwargs) -> Self:

        if position_type is None:
            raise ValueError("position_type must be specified.")
        if long_strike == short_strike:
            raise ValueError("Long and short strikes cannot be the same.")

        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain."
            raise ValueError(message)

        expiration_strikes = option_chain.expiration_strikes[expiration].copy()
        options = [o for o in option_chain.options if o['option_type'] == option_type and o['expiration'] == expiration].copy()

        long_strike = min(expiration_strikes, key=lambda x: abs(x - long_strike))
        short_strike = min(expiration_strikes, key=lambda x: abs(x - short_strike))

        long_dict = next(o for o in options if o['strike'] == long_strike)
        long_option = Option(**long_dict)
        short_dict = next(o for o in options if o['strike'] == short_strike)
        short_option = Option(**short_dict)

        vertical = Vertical(options=[long_option, short_option],
                            spread_type=OptionSpreadType.VERTICAL,
                            position_type=position_type)
        super(Vertical, vertical)._save_user_defined_values(vertical, **kwargs)
        return vertical


    def __post_init__(self):
        message = None
        if self.options[0].option_type != self.options[1].option_type:
            message = "Invalid option type. Both legs must be either calls or puts."
        if self.options[0].expiration != self.options[1].expiration:
            message = "Invalid option expirations. Both legs must have the same expiration."
        if self.options[0].strike == self.options[1].strike:
            message = "Long and short option strikes must not be the same option."
        if self.spread_type != OptionSpreadType.VERTICAL:
            message = "Vertical must have spread type of VERTICAL"
        if message is not None:
            raise ValueError(message)

        self.long_option = self.options[0]
        self.long_option.position_type = OptionPositionType.LONG
        self.short_option = self.options[1]
        self.short_option.position_type = OptionPositionType.SHORT


    def __repr__(self) -> str:
        strikes = [self.long_option.strike, self.short_option.strike]
        s = f'<{self.spread_type.name}({self.instance_id}) {self.option_type.upper()} {self.position_type.name} ' \
                + f'{self.symbol} {strikes[0]}/{strikes[1]} ' \
                + f'{self.expiration}>'
        return s


    def _open_trade(self, quantity: int = 1, *args, **kwargs: dict) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive. The position type determines the direction of each leg.")
        self.quantity = quantity if quantity is not None else self.long_option.quantity
        self.long_option._open_trade(quantity=self.quantity)
        self.short_option._open_trade(quantity=self.quantity * -1)
        super(Vertical, self)._save_user_defined_values(self, **kwargs)

    def _close_trade(self, *, quote_datetime: datetime.datetime, quantity: int | None = None, **kwargs: dict) -> None:
        quantity = quantity if quantity is not None else self.long_option.quantity
        self.long_option._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.short_option._close_trade(quote_datetime=quote_datetime, quantity=quantity)
        self.quantity -= quantity
        super(Vertical, self)._save_user_defined_values(self, **kwargs)

    @property
    def max_profit(self) -> float | None:
        if self.position_type is None:
            raise RuntimeError("Cannot calculate max profit: trade has not been opened.")
        if self.position_type == OptionPositionType.LONG:
            long_price = self.long_option.price if OptionStatus.INITIALIZED == self.long_option.status \
                else self.long_option.trade_open_info.price
            short_price = self.short_option.price if OptionStatus.INITIALIZED == self.short_option.status \
                else self.short_option.trade_open_info.price
            max_profit = float((abs(decimalize_2(self.long_option.strike) - decimalize_2(self.short_option.strike))
                                - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100)
        else:
            max_profit = self.trade_value * -1
        return max_profit

    @property
    def max_loss(self) -> float | None:
        if self.position_type is None:
            raise RuntimeError("Cannot calculate max loss: trade has not been opened.")
        if self.position_type == OptionPositionType.LONG:
            max_loss = self.trade_value
        else:
            if OptionStatus.INITIALIZED in self.long_option.status:
                long_price = self.long_option.price
                short_price = self.short_option.price
            else:
                long_price = self.long_option.trade_open_info.price
                short_price = self.short_option.trade_open_info.price

            if OptionStatus.TRADE_IS_OPEN in self.long_option.status:
                quantity = self.quantity
            elif OptionStatus.TRADE_IS_CLOSED in self.long_option.status:
                quantity = self.long_option.trade_open_info.quantity
            elif OptionStatus.INITIALIZED in self.long_option.status:
                quantity = 1
            else:
                raise RuntimeError("Cannot calculate max loss.")

            max_loss = float((abs(decimalize_2(self.long_option.strike) - decimalize_2(self.short_option.strike))
                              - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100 * abs(quantity))
        return max_loss

    @property
    def status(self) -> OptionStatus:
        return self.short_option.status

    def get_required_margin(self, quantity: int) -> float:
        if OptionStatus.TRADE_IS_OPEN not in self.long_option.status:
            return 0
        elif self.position_type == OptionPositionType.LONG:
            return 0
        elif self.position_type == OptionPositionType.SHORT:
            return abs((self.short_option.strike - self.long_option.strike) * 100 * self.quantity)

    @property
    def price(self) -> float:
        long_price = decimalize_2(self.long_option.price)
        short_price = decimalize_2(self.short_option.price)
        price = long_price - short_price
        return float(price)

    @property
    def expiration(self) -> datetime.date:
        return self.long_option.expiration

    @property
    def option_type(self) -> str:
        return self.long_option.option_type

    def get_dte(self) -> int | None:
        return self.long_option.get_dte()

    def get_trade_price(self) -> float | None:
        if OptionStatus.INITIALIZED ==  self.long_option.status:
            return None
        else:
            long_price = decimalize_2(self.long_option.trade_open_info.price)
            short_price = decimalize_2(self.short_option.trade_open_info.price)
            trade_price = long_price - short_price
            return float(trade_price)

    def get_closed_price(self) -> float | None:
        if OptionStatus.TRADE_IS_CLOSED not in self.long_option.status:
            return None
        long_price = decimalize_2(self.long_option.trade_close_info.price)
        short_price = decimalize_2(self.short_option.trade_close_info.price)
        closed_price = long_price - short_price
        return float(closed_price)


    @property
    def closed_value(self) -> float | None:
        closed_value = super(Vertical, self).closed_value
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            if closed_value > self.max_profit:
                closed_value = self.max_profit
            elif closed_value < self.max_loss * -1:
                closed_value = self.max_loss * -1

        return closed_value

    def get_profit_loss(self) -> float:
        profit_loss = super(Vertical, self).get_profit_loss()
        if all(OptionStatus.TRADE_IS_CLOSED in o.status for o in self.options):
            closed_value = self.closed_value
            if closed_value > self.max_profit or closed_value < self.max_loss * -1:
                profit_loss = closed_value

        return profit_loss

    def get_history(self) -> list[dict]:
        if (OptionStatus.TRADE_IS_OPEN not in self.long_option.status
                and OptionStatus.TRADE_IS_CLOSED not in self.long_option.status):
            raise RuntimeError("Cannot get price history: trade has not been opened.")

        if OptionStatus.TRADE_IS_CLOSED in self.long_option.status:
            last_date = self.long_option.trade_close_info.date
        else:
            last_date = self.long_option.quote_datetime

        long_open_price = self.long_option.trade_open_info.price
        long_open_qty = self.long_option.trade_open_info.quantity
        long_close_records = self.long_option.trade_close_records

        short_open_price = self.short_option.trade_open_info.price
        short_open_qty = self.short_option.trade_open_info.quantity
        short_close_records = self.short_option.trade_close_records

        keys = sorted(
            set(self.long_option.updates.keys()) & set(self.short_option.updates.keys())
        )
        keys = [k for k in keys if k <= last_date]

        history = []
        for k in keys:
            long_update = self.long_option.updates[k]
            short_update = self.short_option.updates[k]

            long_closes = sum(r.quantity for r in long_close_records if r.date <= k)
            long_remaining = abs(long_open_qty) - long_closes
            long_signed = long_remaining * (1 if long_open_qty > 0 else -1)
            long_price = round(float(long_update['price']), 2)
            long_pnl = round((long_price - long_open_price) * 100 * long_signed, 2)

            short_closes = sum(r.quantity for r in short_close_records if r.date <= k)
            short_remaining = abs(short_open_qty) - short_closes
            short_signed = short_remaining * (1 if short_open_qty > 0 else -1)
            short_price = round(float(short_update['price']), 2)
            short_pnl = round((short_price - short_open_price) * 100 * short_signed, 2)

            spread_price = round(long_price - short_price, 2)
            spread_pnl = round(long_pnl + short_pnl, 2)
            trade_price = abs(self.get_trade_price() or 0)
            open_premium = trade_price * 100 * long_remaining
            pnl_pct = round(spread_pnl / open_premium, 4) if open_premium != 0 else 0.0

            def net(field):
                lv = long_update.get(field)
                sv = short_update.get(field)
                return round(float(lv) - float(sv), 4) if lv is not None and sv is not None else None

            history.append({
                'quote_datetime': k,
                'price': spread_price,
                'spot_price': long_update.get('spot_price'),
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
        keys = sorted(
            set(self.long_option.updates.keys()) & set(self.short_option.updates.keys())
        )

        start_long_price = self.long_option.updates[keys[0]]['price']
        start_short_price = self.short_option.updates[keys[0]]['price']

        premium = round((start_long_price - start_short_price) * 100, 2)

        updates = []
        for k in keys:
            long_update = self.long_option.updates[k]
            short_update = self.short_option.updates[k]

            long_price = round(float(long_update['price']), 2)
            long_pnl = round((long_price - start_long_price) * 100 , 2)

            short_price = round(float(short_update['price']), 2)
            short_pnl = round((short_price - start_short_price) * 100, 2)

            spread_price = round(long_price - short_price, 2)
            spread_pnl = round(long_pnl + short_pnl, 2)
            pnl_pct = round(spread_pnl / premium, 4) if premium != 0 else 0.0

            updates.append({
               'quote_datetime': k,
               'price': spread_price,
               'pnl': spread_pnl,
               'pnl_pct': pnl_pct
            })

        return updates