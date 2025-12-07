from dataclasses import field

import options_framework.option
from options_framework.option_types import OptionPositionType, OptionTradeType, OptionCombinationType, \
    TransactionType, OptionStatus
from options_framework.option_chain import OptionChain
from options_framework.spreads.option_combo import OptionCombination
from options_framework.utils.helpers import decimalize_0, decimalize_2
from options_framework.option import Option
import datetime


class IronCondor(OptionCombination):
    """
    An Iron Condor is created with 4 options: A long call option, a short call option, a long put option, and a short
    put option.
    To create an iron condor, supply these four options in a list in this order:
        long call
        short call
        long put
        short put

    To create a long iron condor, which is to buy an iron condor, the two inner options must be the long options,
    and the two outer options are the short options.

    To create a short iron condor, which is to sell an iron condor, the two inner options must be the short options,
    and the two outer options are the long options.
    """

    @classmethod
    def get_iron_condor_by_strike(cls, option_chain: OptionChain, expiration: datetime.date,
                                  long_call_strike: int | float,
                                  short_call_strike: int | float,
                                  long_put_strike: int | float,
                                  short_put_strike: int | float,
                                  quantity: int = 1) -> OptionCombination:
        """
        Create an iron condor by supplying the expiration and strikes. If the exact strikes or expiration are not found,
        the nearest one will be selected.
        :param option_chain: The option chain
        :param expiration:  The desired expiration. If this is not found, the next greatest expiration will be selected.
        :param long_call_strike: The value for the long call strike. If this is not found, the next higher strike
            will be selected
        :param short_call_strike: The value for the short call strike. If this is not found, the next higher strike
            will be selected
        :param long_put_strike: The value for the long put strike. If this is not found, the next lower strike
            will be selected
        :param short_put_strike: The value for the short put strike. If this is not found, the next lower strike
            will be selected
        :param quantity: All four options will have the same quantity. The short options will have a negative quantity
        :return: an IronCondor instance
        """
        if not ((short_call_strike > long_call_strike) and (short_put_strike < long_put_strike) or
                (short_call_strike > long_call_strike) and (short_put_strike < long_put_strike)):
            message = "These strike selections do not form an iron condor. A long iron condor has " \
                      + "the long call strike less than the short call strike, and the long put strike " \
                      + "is greater than the short put strike. A short iron " \
                      + "condor has the short call strike less than the long call strike, and the short put " \
                      + "strike is greater than the long put strike."
            raise ValueError(message)

        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)

        exp_strikes = option_chain.expiration_strikes[expiration].copy()
        options = [o for o in option_chain.option_chain if o.expiration == expiration].copy()
        # Find strikes
        try:
            long_call_strike = next(s for s in exp_strikes if s >= long_call_strike)
            short_call_strike = next(s for s in exp_strikes if s >= short_call_strike)

            exp_strikes.sort(reverse=True)
            long_put_strike = next(s for s in exp_strikes if s <= long_put_strike)
            short_put_strike = next(s for s in exp_strikes if s <= short_put_strike)
        except StopIteration:
            raise ValueError("No matching strike was found in the option chain. Consider changing the selection filter.")

        try:
            long_call_option = next(o for o in options if o.option_type == 'call' and o.strike == long_call_strike)
            short_call_option = next(o for o in options if o.option_type == 'call' and o.strike == short_call_strike)
            long_put_option = next(o for o in options if o.option_type == 'put' and o.strike == long_put_strike)
            short_put_option = next(o for o in option_chain.option_chain if o.option_type == 'put' and o.strike == short_put_strike)
        except StopIteration:
            raise ValueError("No options matching the requirements were found in the option chain. Consider changing the selection filter.")

        long_call_option.quantity, long_call_option.position_type = quantity, OptionPositionType.LONG
        short_call_option.quantity, short_call_option.position_type = quantity * -1, OptionPositionType.SHORT
        long_put_option.quantity, long_put_option.position_type = quantity, OptionPositionType.LONG
        short_put_option.quantity, short_put_option.position_type = quantity * -1, OptionPositionType.SHORT

        spread_options = [long_call_option, short_call_option, long_put_option, short_put_option]
        option_position_type = OptionPositionType.LONG if long_call_option.strike < short_call_option.strike \
            else OptionPositionType.SHORT
        iron_condor = IronCondor(options=spread_options, option_combination_type=OptionCombinationType.IRON_CONDOR,
                                 option_position_type=option_position_type, quantity=quantity)
        return iron_condor

    @classmethod
    def get_iron_condor_by_strike_and_width(cls, option_chain: OptionChain, expiration: datetime.date,
                                            option_position_type: OptionPositionType,
                                            inner_call_strike: int | float,
                                            inner_put_strike: int | float,
                                            spread_width: int | float,
                                            quantity: int = 1) -> OptionCombination:
        """
        Create an iron condor by specifying the inner strikes, and then selecting the wings with a minimum spread
        width
        :param option_chain: the option chain
        :param expiration: The desired expiration. If this is not found, the next greatest expiration will be selected.
        :param inner_call_strike: The closest-to-the-money call strike
        :param inner_put_strike:  The closest-to-the-money put strike
        :param spread_width: The strike with at least the spread width distance further from the money from the
                    inner strikes
        :param quantity: The quantity for each option. The long and short options are determined by the
                    option position type provided. A long position type will have the inner legs be the short legs,
                    and a short position type will have the inner legs be the long legs
        :return: an IronCondor instance
        """

        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)

        exp_strikes = option_chain.expiration_strikes[expiration].copy()
        options = [o for o in option_chain.option_chain if o.expiration == expiration].copy()

        # Define strike targest
        long_call_strike, short_call_strike = (inner_call_strike, inner_call_strike + spread_width) \
            if option_position_type == OptionPositionType.LONG \
            else (inner_call_strike + spread_width, inner_call_strike)
        long_put_strike, short_put_strike = (inner_put_strike, inner_put_strike - spread_width) \
            if option_position_type == OptionPositionType.LONG \
            else (inner_put_strike - spread_width, inner_put_strike)

        try:
            # Find call strikes
            long_call_strike = next(s for s in exp_strikes if s >= long_call_strike)
            short_call_strike = next(s for s in exp_strikes if s >= short_call_strike)

            # Find put strikes
            exp_strikes.sort(reverse=True)
            long_put_strike = next(s for s in exp_strikes if s <= long_put_strike)
            short_put_strike = next(s for s in exp_strikes if s <= short_put_strike)
        except StopIteration:
            message = "No strikes matching the requirements were found in the option chain. Consider changing the selection filter."
            raise ValueError(message)

        try:
            long_call_option = next(
                o for o in options if o.option_type == 'call' and o.strike == long_call_strike)
            short_call_option = next(
                o for o in options if o.option_type == 'call' and o.strike == short_call_strike)
            long_put_option = next(
                o for o in options if o.option_type == 'put' and o.strike == long_put_strike)
            short_put_option = next(o for o in options if
                                    o.option_type == 'put' and o.strike == short_put_strike)
        except StopIteration:
            raise ValueError(
                "No options matching the requirements were found in the option chain. Consider changing the selection filter.")

        long_call_option.quantity, long_call_option.position_type = quantity, OptionPositionType.LONG
        short_call_option.quantity, short_call_option.position_type = quantity * -1, OptionPositionType.SHORT
        long_put_option.quantity, long_put_option.position_type = quantity, OptionPositionType.LONG
        short_put_option.quantity, short_put_option.position_type = quantity * -1, OptionPositionType.SHORT

        spread_options = [long_call_option, short_call_option, long_put_option, short_put_option]
        option_position_type = OptionPositionType.LONG if long_call_option.strike < short_call_option.strike \
            else OptionPositionType.SHORT
        iron_condor = IronCondor(options=spread_options, option_combination_type=OptionCombinationType.IRON_CONDOR,
                                 option_position_type=option_position_type, quantity=quantity)
        return iron_condor

    @classmethod
    def get_iron_condor_by_delta(cls, option_chain: OptionChain, expiration: datetime.date,
                                 long_delta: float,
                                 short_delta: float,
                                 quantity: int = 1) -> OptionCombination:
        """
                Create an iron condor by supplying the expiration and deltas. If the exact deltas or expiration are not found,
                the next one will be selected.
                Call option deltas must be positive numbers, and put option deltas must be negative numbers.
                :param option_chain: The option chain
                :param expiration:  The desired expiration. If this is not found, the next greatest expiration will be selected.
                :param long_call_delta: The value for the long call delta. If the exact value is not found, the next higher delta
                    will be selected
                :param short_call_delta: The value for the short call delta. If the exact value is not found, the next higher delta
                    will be selected
                :param long_put_delta: The value for the long put delta. If the exact value is not found, the next lower delta
                    will be selected
                :param short_put_delta: The value for the short put delta. If this is not found, the next lower delta
                    will be selected
                :param quantity: All four options will have the same quantity. The short options quantity will be a negative value
                :return: an IronCondor instance
                """

        # Find nearest matching expiration
        try:
            expiration = next(e for e in option_chain.expirations if e >= expiration)
        except StopIteration:
            message = "No matching expiration was found in the option chain. Consider changing the selection filter."
            raise ValueError(message)

        options = [o for o in option_chain.option_chain if o.expiration == expiration]
        options.sort(key=lambda x: x.delta, reverse=True)

        # Find nearest long call matching delta
        select_options = [o for o in options if o.option_type == 'call'
                          and o.delta <= long_delta]
        if not select_options:
            raise ValueError(
                "No matching options were found for the long call delta value. Consider changing the selection filter.")
        long_call_option = select_options[0]
        long_call_option.quantity, long_call_option.position_type = quantity, OptionPositionType.LONG

        # Find nearest short call matching delta
        select_options = [o for o in options if o.option_type == 'call'
                          and o.delta <= short_delta]
        if not select_options:
            raise ValueError(
                "No matching options were found for the short call delta value. Consider changing the selection filter.")
        short_call_option = select_options[0]
        short_call_option.quantity, short_call_option.position_type = quantity * -1, OptionPositionType.SHORT

        options.sort(key=lambda x: x.delta)
        # Find nearest long put matching delta
        select_options = [o for o in options if o.option_type == 'put'
                          and o.delta >= -long_delta]
        if not select_options:
            raise ValueError(
                "No matching options were found for the long put delta value. Consider changing the selection filter.")
        long_put_option = select_options[0]
        long_put_option.quantity, long_put_option.position_type = quantity, OptionPositionType.LONG

        # Find nearest short put matching delta
        select_options = [o for o in options if o.option_type == 'put'
                          and o.delta >= -short_delta]
        if not select_options:
            raise ValueError(
                "No matching options were found for the short put delta value. Consider changing the selection filter.")
        short_put_option = select_options[0]
        short_put_option.quantity, short_put_option.position_type = quantity * -1, OptionPositionType.SHORT

        spread_options = [long_call_option, short_call_option, long_put_option, short_put_option]
        option_position_type = OptionPositionType.LONG if long_call_option.strike < short_call_option.strike \
            else OptionPositionType.SHORT
        iron_condor = IronCondor(options=spread_options, option_combination_type=OptionCombinationType.IRON_CONDOR,
                                 option_position_type=option_position_type, quantity=quantity)
        return iron_condor

    short_call_option: Option = field(init=False, default=None)
    long_call_option: Option = field(init=False, default=None)
    short_put_option: Option = field(init=False, default=None)
    long_put_option: Option = field(init=False, default=None)

    def __post_init__(self):
        long_call_option = self.options[0]
        short_call_option = self.options[1]
        long_put_option = self.options[2]
        short_put_option = self.options[3]
        if not ((short_call_option.strike > long_call_option.strike) and (
                short_put_option.strike < long_put_option.strike) or
                (short_call_option.strike < long_call_option.strike) and (
                        short_put_option.strike > long_put_option.strike)):
            raise ValueError(f"{long_call_option.strike}/{short_call_option.strike}/{long_put_option.strike}/{short_put_option.strike} These strike selections do not form an iron condor. A long iron condor has " \
                             + "the long call strike less than the short call strike, and the long put strike " \
                             + "is greater than the short put strike. A short iron " \
                             + "condor has the short call strike less than the long call strike, and the short put " \
                             + "strike is greater than the long put strike.")

        if long_call_option.quantity <= 0 or short_call_option.quantity >= 0 or long_put_option.quantity <= 0 or short_put_option.quantity >= 0:
            raise ValueError(
                "The long options must have a positive quantity, and the short options must have a negative " \
                + "quantity.")

        call_qty = sum(o.quantity for o in self.options if o.option_type == 'call')
        put_qty = sum(o.quantity for o in self.options if o.option_type == 'put')
        if call_qty + put_qty != 0:
            message = "Invalid quantities. An Iron Condor Spread must have a balanced number of long and short options. " \
                      + " This configuration will have naked options."
            raise ValueError(message)

        exp = self.options[0].expiration
        if not all(o for o in self.options if o.expiration == exp):
            message = "Invalid option expirations. All options must have the same expiration."
            raise ValueError(message)

        self.long_call_option = long_call_option
        self.short_call_option = short_call_option
        self.long_put_option = long_put_option
        self.short_put_option = short_put_option
        self.option_position_type = OptionPositionType.LONG if long_call_option.strike < short_call_option.strike \
            else OptionPositionType.SHORT
        self.option_combination_type = OptionCombinationType.IRON_CONDOR

    def update_quantity(self, quantity: int):
        self.quantity = abs(quantity) if self.option_position_type == OptionPositionType.LONG else abs(quantity)*-1
        quantity = abs(quantity)
        self.long_call_option.quantity = quantity
        self.long_put_option.quantity = quantity
        quantity = abs(quantity) * -1
        self.short_call_option.quantity = quantity
        self.short_put_option.quantity = quantity

    def open_trade(self, quantity: int | None = None, **kwargs: dict) -> None:
        quantity = abs(quantity) if quantity else None
        self.long_call_option.open_trade(quantity=quantity if quantity else self.long_call_option.quantity)
        self.long_put_option.open_trade(quantity=quantity if quantity else self.long_put_option.quantity)
        quantity = quantity * -1 if quantity is not None else None
        self.short_call_option.open_trade(quantity=quantity if quantity else self.short_call_option.quantity)
        self.short_put_option.open_trade(quantity=quantity if quantity else self.short_put_option.quantity)
        super(IronCondor, self).open_trade(quantity=quantity, **kwargs)

    def close_trade(self, *, quantity: int | None = None, **kwargs: dict) -> None:
        quantity = abs(quantity) if quantity else None
        self.long_call_option.close_trade(
            quantity=abs(quantity) if quantity is not None else self.long_call_option.quantity)
        self.long_put_option.close_trade(
            quantity=abs(quantity) if quantity is not None else self.long_put_option.quantity)
        quantity = abs(quantity) * -1 if quantity else None
        self.short_call_option.close_trade(
            quantity=quantity if quantity is not None else self.short_call_option.quantity)
        self.short_put_option.close_trade(
            quantity=quantity if quantity is not None else self.short_put_option.quantity)
        self.quantity -= quantity
        super(IronCondor, self).close_trade(quantity=quantity, **kwargs)

    @property
    def max_profit(self) -> float | None:
        if self.option_position_type == OptionPositionType.SHORT:
            max_profit = self.trade_value * -1
        else:

            # Call side
            long_price = self.long_call_option.price if self.long_call_option.status == OptionStatus.INITIALIZED \
                else self.long_call_option.trade_price
            short_price = self.short_call_option.price if self.short_call_option.status == OptionStatus.INITIALIZED \
                else self.short_call_option.trade_price

            call_max_profit = float(
                (abs(decimalize_2(self.long_call_option.strike) - decimalize_2(self.short_call_option.strike))
                 - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100)

            # Put side
            long_price = self.long_put_option.price if self.long_put_option.status == OptionStatus.INITIALIZED \
                else self.long_put_option.trade_price
            short_price = self.short_put_option.price if self.short_put_option.status == OptionStatus.INITIALIZED \
                else self.short_put_option.trade_price

            put_max_profit = float(
                (abs(decimalize_2(self.long_put_option.strike) - decimalize_2(self.short_put_option.strike))
                 - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100)
            max_profit = max(call_max_profit, put_max_profit)

        return max_profit

    @property
    def max_loss(self) -> float | None:
        if self.option_position_type == OptionPositionType.LONG:
            max_loss = self.trade_value
        else:
            # Call side
            long_price = self.long_call_option.trade_price
            short_price = self.short_call_option.trade_price
            quantity = self.long_call_option.trade_open_info.quantity \
                if OptionStatus.TRADE_IS_CLOSED in self.long_call_option.status \
                else self.quantity
            call_max_loss = float(
                (abs(decimalize_2(self.long_call_option.strike) - decimalize_2(self.short_call_option.strike))
                 - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100 * abs(quantity))

            # Put side
            long_price = self.long_put_option.trade_price
            short_price = self.short_put_option.trade_price
            quantity = self.long_put_option.trade_open_info.quantity \
                if OptionStatus.TRADE_IS_CLOSED in self.long_put_option.status \
                else self.quantity
            put_max_loss = float(
                (abs(decimalize_2(self.long_put_option.strike) - decimalize_2(self.short_put_option.strike))
                 - abs(decimalize_2(long_price) - decimalize_2(short_price))) * 100 * abs(quantity))
            max_loss = max(call_max_loss, put_max_loss)
        return max_loss

    @property
    def required_margin(self) -> float:
        if self.option_position_type == OptionPositionType.LONG:
            return 0
        elif self.option_position_type == OptionPositionType.SHORT:
            call_strike_width = abs((self.short_call_option.strike - self.long_call_option.strike)
                                    * 100 * self.long_call_option.quantity)
            put_strike_width = abs((self.short_put_option.strike - self.long_put_option.strike)
                                   * 100 * self.long_put_option.quantity)
            return max(call_strike_width, put_strike_width)

    def get_trade_price(self) -> float | None:
        long_call_price = decimalize_2(self.long_call_option.trade_price)
        short_call_price = decimalize_2(self.short_call_option.trade_price)
        call_price = long_call_price - short_call_price
        long_put_price = decimalize_2(self.long_put_option.trade_price)
        short_put_price = decimalize_2(self.short_put_option.trade_price)
        put_price = long_put_price - short_put_price
        trade_price = call_price + put_price
        return float(trade_price)

    @property
    def price(self) -> float:
        long_call_price = decimalize_2(self.long_call_option.price)
        short_call_price = decimalize_2(self.short_call_option.price)
        call_price = long_call_price - short_call_price
        long_put_price = decimalize_2(self.long_put_option.price)
        short_put_price = decimalize_2(self.short_put_option.price)
        put_price = long_put_price - short_put_price
        price = call_price + put_price
        return float(price)

    @property
    def expiration(self) -> datetime.date:
        return self.long_call_option.expiration
