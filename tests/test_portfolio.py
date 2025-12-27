import datetime

import pytest
import copy

from options_framework.option import Option
from options_framework.portfolio import OptionPortfolio
from options_framework.option_types import OptionSpreadType, OptionPositionType, OptionStatus
from options_framework.spreads.single import Single
from options_framework.config import settings

def test_create_portfolio_settings():
    start_date = datetime.datetime.strptime('2014-12-31 00:00', '%Y-%m-%d %H:%M')
    end_date = datetime.datetime.strptime('2015-01-05 00:00', '%Y-%m-%d %H:%M')
    starting_cash = 100_000

    portfolio = OptionPortfolio(starting_cash, start_date, end_date)

    assert portfolio.cash == starting_cash
    assert portfolio.start_date == start_date
    assert portfolio.end_date == end_date
    assert len(portfolio.option_chains.keys()) == 0
    assert str(portfolio) == '<OptionPortfolio cash=$100,000.00 portfolio_value=$100,000.00>'

def test_initialize_ticker_for_daily_add_option_chain_to_portfolio(daily_file_settings):
    symbol = 'AAPL'
    quote_datetime = datetime.datetime(2014, 12, 30, 0, 0)
    end_datetime = datetime.datetime(2015, 1, 7, 0, 0)
    cash = 10_000

    portfolio = OptionPortfolio(cash, quote_datetime, end_datetime)
    portfolio.initialize_ticker(symbol, quote_datetime)

    assert symbol in portfolio.option_chains.keys()

def test_open_long_position_adds_to_open_positions(daily_file_settings):
    symbol = 'AAPL'
    quote_datetime = datetime.datetime(2014, 12, 30, 0, 0)
    end_datetime = datetime.datetime(2015, 1, 7, 0, 0)
    cash = 10_000

    portfolio = OptionPortfolio(cash, quote_datetime, end_datetime)
    portfolio.initialize_ticker(symbol, quote_datetime)

    option_data = copy.deepcopy(portfolio.option_chains[symbol].options[0])
    o = Option(**option_data)
    single = Single(options=[o], spread_type=OptionSpreadType.SINGLE)
    portfolio.open_position(single, quantity=10)

    assert len(portfolio.positions) == 1

def test_close_position_removes_from_open_positions_adds_to_closed_positions(daily_file_settings):
    symbol = 'AAPL'
    quote_datetime = datetime.datetime(2014, 12, 30, 0, 0)
    end_datetime = datetime.datetime(2015, 1, 7, 0, 0)
    cash = 10_000

    portfolio = OptionPortfolio(cash, quote_datetime, end_datetime)
    portfolio.initialize_ticker(symbol, quote_datetime)

    option_data = copy.deepcopy(portfolio.option_chains[symbol].options[0])
    o = Option(**option_data)
    single = Single(options=[o], spread_type=OptionSpreadType.SINGLE)
    portfolio.open_position(single, quantity=5)

    assert len(portfolio.positions) == 1
    assert len(portfolio.closed_positions) == 0

    portfolio.close_position(single.position_id, quantity=5)

    assert len(portfolio.positions) == 0
    assert len(portfolio.closed_positions) == 1

def test_portfolio_events_are_emitted(option_chain_data):
    quote_datetime = datetime.datetime(2014, 12, 30, 0, 0)
    end_datetime = datetime.datetime(2015, 1, 7, 0, 0)
    cash = 10_000
    portfolio = OptionPortfolio(cash, quote_datetime, end_datetime)
    data = option_chain_data('daily', quote_datetime)
    option_data = copy.deepcopy(data.options[4])
    option = Option(**option_data)
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)
    portfolio.open_position(single, 1)
    #portfolio.positions[single.position_id] = single

    on_next_fired = None
    on_options_next_fired = None
    on_position_closed_fired = None
    on_position_expired_fired = None
    class Listener:

        @staticmethod
        def on_next(quote_datetime):
            nonlocal on_next_fired
            on_next_fired = quote_datetime

        @staticmethod
        def on_options_next(options):
            nonlocal on_options_next_fired
            on_options_next_fired = options

        @staticmethod
        def on_position_closed(position):
            nonlocal on_position_closed_fired
            on_position_closed_fired = position

        @staticmethod
        def on_expired(position):
            nonlocal on_position_expired_fired
            on_position_expired_fired = position

    listener = Listener()

    # next event
    next_quote = quote_datetime + datetime.timedelta(days=1)
    portfolio.bind(next=listener.on_next)
    portfolio.next(next_quote)
    assert on_next_fired == next_quote

    # next_options event
    portfolio.bind(next_options=listener.on_options_next)
    portfolio.next(next_quote)
    assert on_options_next_fired[0] is option

    # position_closed event
    portfolio.bind(position_closed=listener.on_position_closed)
    portfolio.close_position(single.position_id, 1)
    assert on_position_closed_fired is single

    # position_expired event
    option.status = OptionStatus.INITIALIZED
    portfolio.open_position(single, 1)
    option.status |= OptionStatus.EXPIRED
    portfolio.bind(position_expired=listener.on_expired)
    portfolio.on_option_expired(option.option_id)
    assert on_position_expired_fired is single


def test_portfolio_cash_and_value_with_open_positions(option_chain_data):
    symbol = 'AAPL'
    quote_datetime = datetime.datetime(2014, 12, 30, 0, 0)
    end_datetime = datetime.datetime(2015, 1, 7, 0, 0)
    starting_cash = 10_000

    portfolio = OptionPortfolio(starting_cash, quote_datetime, end_datetime)
    portfolio.initialize_ticker(symbol, quote_datetime)

    data = option_chain_data('daily', quote_datetime)
    option_data = copy.deepcopy(data.options[7])
    option = Option(**data.options[7])
    option.incur_fees = False
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)
    portfolio.open_position(single, 1)

    assert portfolio.cash == 9_875.0
    assert portfolio.current_value == starting_cash

def test_portfolio_value_when_option_value_changes(daily_file_settings):
    symbol = 'AAPL'
    quote_datetime = datetime.datetime(2014, 12, 30, 0, 0)
    end_datetime = datetime.datetime(2015, 1, 7, 0, 0)
    starting_cash = 10_000

    portfolio = OptionPortfolio(starting_cash, quote_datetime, end_datetime)
    portfolio.initialize_ticker(symbol, quote_datetime)

    option_data = portfolio.option_chains[symbol].options[61]
    option = Option(**option_data)
    option.incur_fees = False
    single = Single(options=[option], spread_type=OptionSpreadType.SINGLE)

    portfolio.open_position(single, 1)
    quote_datetime = quote_datetime + datetime.timedelta(days=1)
    portfolio.next(quote_datetime)

    unrealized_pnl = single.get_unrealized_profit_loss()

    assert portfolio.current_value == starting_cash + unrealized_pnl


