import datetime
import dill
from pydispatch import Dispatcher
from mocks import MockIntegrationDataLoader, Nexter
import pytest
from options_framework.option_chain import OptionChain
from options_framework.option_types import OptionType, SelectFilter
from options_framework.config import settings




@pytest.fixture
# Bind option chain to the mock data loader
def setup():
    symbol = 'AAPL'
    start_date = datetime.datetime.strptime('2014-02-05', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2014-02-10', '%Y-%m-%d')
    data_loader = MockIntegrationDataLoader(start=start_date, end=end_date, select_filter=SelectFilter())
    option_chain = OptionChain(symbol, start_date)
    data_loader.bind(option_chain_loaded=option_chain.on_option_chain_loaded)
    data_loader.load_option_chain_data(symbol, start_date, end_date)
    return symbol, start_date, end_date, option_chain, data_loader

def test_option_chain_contains_only_quotedate_option_records(setup):
    quote_date = datetime.datetime.strptime('2014-02-05', '%Y-%m-%d')
    #sf = SelectFilter(option_type=OptionType.CALL)
    symbol, start_date, end_date, option_chain, dl = setup

    assert all([x for x in option_chain.option_chain if x.quote_datetime == quote_date])

def test_option_chain_has_new_options_after_next_event_is_emitted(setup):
    symbol, start_date, end_date, option_chain, dl = setup

    next_day = datetime.datetime.strptime('2014-02-06', '%Y-%m-%d')

    nexter = Nexter()
    nexter.bind(next=option_chain.on_next)
    nexter.do_next(next_day)

    assert all([x for x in option_chain.option_chain if x.quote_datetime == next_day])

def test_open_option(setup):
    symbol, start_date, end_date, option_chain, dl = setup

    nexter = Nexter()

    op = option_chain.option_chain[2]
    nexter.bind(new_position_opened=dl.on_options_opened)
    nexter.bind(next=op.next_update)

    nexter.open_option_position([op])

    first_price = op.price
    price2 = round(2.305, 2)
    price3 = round(7.175, 2)

    next_day = start_date + datetime.timedelta(days=1)
    nexter.do_next(next_day)

    assert op.quote_datetime == next_day
    assert op.price == price2

    next_day = next_day + datetime.timedelta(days=1)
    nexter.do_next(next_day)

    assert op.quote_datetime == next_day
    assert op.price == price3


