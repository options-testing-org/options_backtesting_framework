import datetime

from mocks import MockEventDispatcher
from options_framework.option import Option
from options_framework.option_chain import OptionChain


def test_load_option_chain_intraday_sets_chain_expiration_and_strikes(intraday_file_settings):
    quote_date = datetime.datetime.strptime('2016-04-28 10:00', '%Y-%m-%d %H:%M')
    end_date = datetime.datetime.strptime('2016-04-29 11:00', '%Y-%m-%d %H:%M')
    option_chain = OptionChain('SPXW', quote_datetime=quote_date, end_datetime=end_date)

    option_chain.on_next(quote_datetime=quote_date)

    assert option_chain.quote_datetime == quote_date
    assert option_chain.end_datetime == end_date
    assert len(option_chain.options) > 0
    assert len(option_chain.expirations) > 0
    assert len(option_chain.expiration_strikes) > 0
    assert len(option_chain.expiration_strikes[option_chain.expirations[0]]) > 0

def test_load_option_chain_daily_sets_chain_expiration_and_strikes(daily_file_settings):
    symbol = 'AAPL'
    start_date = datetime.datetime.strptime('2014-12-30', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2014-12-31', '%Y-%m-%d')
    option_chain = OptionChain(symbol, start_date, end_date)

    option_chain.on_next(start_date)

    assert option_chain.quote_datetime == start_date
    assert option_chain.end_datetime == end_date
    assert len(option_chain.options) > 0
    assert len(option_chain.expirations) > 0
    assert len(option_chain.expiration_strikes) > 0
    assert len(option_chain.expiration_strikes[option_chain.expirations[0]]) > 0


def test_intraday_load_datetimes_list_is_populated_when_same_month(intraday_file_settings):
    quote_date = datetime.datetime.strptime('2016-04-28 10:30', '%Y-%m-%d %H:%M')
    end_date = datetime.datetime.strptime('2016-04-29 11:30', '%Y-%m-%d %H:%M')
    option_chain = OptionChain('SPXW', quote_datetime=quote_date, end_datetime=end_date)

    assert len(option_chain.datetimes) > 0
    assert option_chain.datetimes[0] == quote_date
    assert option_chain.datetimes[-1] == end_date


def test_intraday_load_datetimes_list_is_populated_when_crossing_months(intraday_file_settings):
    quote_date = datetime.datetime.strptime('2016-04-29 10:30', '%Y-%m-%d %H:%M')
    end_date = datetime.datetime.strptime('2016-05-02 13:45', '%Y-%m-%d %H:%M')
    option_chain = OptionChain('SPXW', quote_datetime=quote_date, end_datetime=end_date)

    assert len(option_chain.datetimes) > 0
    assert option_chain.datetimes[0] == quote_date
    assert option_chain.datetimes[-1] == end_date

def test_daily_load_datetimes_list_is_populated_when_same_month(daily_file_settings):
    quote_date = datetime.datetime.strptime('2015-01-02 00:00', '%Y-%m-%d %H:%M')
    end_date = datetime.datetime.strptime('2015-01-05 00:00', '%Y-%m-%d %H:%M')
    option_chain = OptionChain('AAPL', quote_datetime=quote_date, end_datetime=end_date)

    assert len(option_chain.datetimes) > 0
    assert option_chain.datetimes[0] == quote_date
    assert option_chain.datetimes[-1] == end_date


def test_daily_load_datetimes_list_is_populated_when_crossing_months(daily_file_settings):
    quote_date = datetime.datetime.strptime('2014-12-31 00:00', '%Y-%m-%d %H:%M')
    end_date = datetime.datetime.strptime('2015-01-02 00:00', '%Y-%m-%d %H:%M')
    option_chain = OptionChain('AAPL', quote_datetime=quote_date, end_datetime=end_date)

    assert len(option_chain.datetimes) > 0
    assert option_chain.datetimes[0] == quote_date
    assert option_chain.datetimes[-1] == end_date


def test_option_chain_has_new_options_after_on_next_event_is_emitted(daily_file_settings):
    quote_date = datetime.datetime.strptime('2014-12-31 00:00', '%Y-%m-%d %H:%M')
    end_date = datetime.datetime.strptime('2015-01-05 00:00', '%Y-%m-%d %H:%M')
    option_chain = OptionChain('AAPL', quote_datetime=quote_date, end_datetime=end_date)
    option_chain.on_next(quote_date)

    next_day = datetime.datetime.strptime('2015-01-02 00:00', '%Y-%m-%d %H:%M')

    nexter = MockEventDispatcher()
    nexter.bind(next=option_chain.on_next)
    nexter.do_next(next_day)

    assert all([x for x in option_chain.options if x['quote_datetime'] == next_day])

def test_on_next_options(daily_file_settings):
    quote_date = datetime.datetime.strptime('2014-12-31 00:00', '%Y-%m-%d %H:%M')
    end_date = datetime.datetime.strptime('2015-01-05 00:00', '%Y-%m-%d %H:%M')
    option_chain = OptionChain('AAPL', quote_datetime=quote_date, end_datetime=end_date)
    option_chain.on_next(quote_date)

    # get test option
    option = Option(**option_chain.options[2])
    assert option.price == 35.42

    # wire up events
    nexter = MockEventDispatcher()
    nexter.bind(next_options=option_chain.on_next_options)

    # advance option chain to next day
    next_day = datetime.datetime.strptime('2015-01-02 00:00', '%Y-%m-%d %H:%M')
    option_chain.on_next(next_day)

    # trigger next event to update option to new date
    nexter.do_next_options([option])

    assert option.price == 34.3
    assert option.quote_datetime == next_day


