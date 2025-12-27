import datetime
import pytest
import copy

from options_framework.option import Option
from options_framework.option_types import OptionPositionType, OptionSpreadType
from options_framework.spreads.straddle import Straddle


@pytest.mark.parametrize("strike, quantity, position_type, expected_repr", [(110.0, 1, OptionPositionType.LONG, '<STRADDLE({0}) AAPL 110.0 2015-01-17{1}>'),
                                                                  (120.0, -1, OptionPositionType.SHORT, '<STRADDLE({0}) AAPL 120.0 2015-01-17{1}>'),
                                                                          ])
def test_repr(option_chain_data, strike, quantity, position_type, expected_repr):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = strike

    straddle = Straddle.create(option_chain=option_chain,
                               strike=strike,
                               expiration=expiration,
                               option_position_type=position_type)

    # straddle that is closed - does not have long or short type yet
    test_repr = expected_repr.format(straddle.position_id, '')
    repr_ = straddle.__repr__()
    assert test_repr == repr_


    straddle.open_trade(quantity=quantity)
    type_ = " LONG" if quantity > 0 else " SHORT"
    test_repr = expected_repr.format(straddle.position_id, type_)
    repr_ = straddle.__repr__()
    assert test_repr == repr_


def test_instantiate_straddle_with_not_two_options_raises_error(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    
    with pytest.raises(ValueError):
        straddle = Straddle(options=[option1], spread_type=OptionSpreadType.STRADDLE)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00010000')
    option_data = copy.deepcopy(data)
    option2 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00012000')
    option_data = copy.deepcopy(data)
    option3 = Option(**option_data)

    with pytest.raises(ValueError):
        straddle = Straddle(options=[option1, option2, option3], spread_type=OptionSpreadType.STRADDLE)

def test_instantiate_with_same_option_type(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00012000')
    option_data = copy.deepcopy(data)
    option2 = Option(**option_data)

    # with two calls
    with pytest.raises(ValueError):
        straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00012000')
    option_data = copy.deepcopy(data)
    option2 = Option(**option_data)

    # with two puts
    with pytest.raises(ValueError):
        straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)

def test_instantiate_with_different_strikes(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    # option 1 strike == 100, option 2 strike == 120
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00012000')
    option_data = copy.deepcopy(data)
    option2 = Option(**option_data)

    with pytest.raises(ValueError):
        straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)

def test_instantiate_with_one_long_and_one_short(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00010000')
    option_data = copy.deepcopy(data)
    option2 = Option(**option_data)

    # buy call, sell put
    option1.open_trade(quantity=1)
    option2.open_trade(quantity=-1)

    with pytest.raises(ValueError):
        straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)


def test_instantiate_with_different_quantities(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00010000')
    option_data = copy.deepcopy(data)
    option2 = Option(**option_data)

    # buy 1 call, buy 2 put
    option1.open_trade(quantity=1)
    option2.open_trade(quantity=2)

    with pytest.raises(ValueError):
        straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)

def test_instantiate_with_different_symbol(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00010000')
    option_data = copy.deepcopy(data)
    option_data['symbol'] = 'MSFT'
    option2 = Option(**option_data)

    with pytest.raises(ValueError):
        straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)


def test_instantiate_with_different_expirations(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    # option 1 expires 1/2, option 2 expires 1/17
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150117P00010000')
    option_data = copy.deepcopy(data)
    option2 = Option(**option_data)

    with pytest.raises(ValueError):
        straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)

def test_instantiate_with_wrong_spread_type_raises_error(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00010000')
    option_data = copy.deepcopy(data)
    option2 = Option(**option_data)

    with pytest.raises(ValueError):
        straddle = Straddle([option1, option2], spread_type=OptionSpreadType.CUSTOM)

def test_instantiate_with_correct_parameters_creates_straddle_object(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option_data = copy.deepcopy(data)
    option1 = Option(**option_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00010000')
    option_data = copy.deepcopy(data)
    option2 = Option(**option_data)

    # instantiate straddle with options not opened yet
    straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)
    assert straddle.spread_type == OptionSpreadType.STRADDLE

    option1.open_trade(quantity=1)
    option2.open_trade(quantity=1)

    # instantiate straddle with options opened
    straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)
    assert straddle.spread_type == OptionSpreadType.STRADDLE

def test_create(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    strike = 110
    expiration = datetime.date(2015, 1, 17)

    straddle = Straddle.create(option_chain, expiration, strike)

    assert straddle.expiration == expiration
    assert straddle.strike == strike
    assert len(straddle.options) == 2

def test_create_with_close_values_finds_next_properties(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    strike = 108
    expiration = datetime.date(2015, 1, 15)

    straddle = Straddle.create(option_chain, expiration, strike)

    assert straddle.expiration == datetime.date(2015, 1, 17)
    assert straddle.strike == 110.0
    assert len(straddle.options) == 2

def test_open_long(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    strike = 110
    expiration = datetime.date(2015, 1, 17)

    straddle = Straddle.create(option_chain, expiration, strike)

    straddle.open_trade(quantity=1)

    assert straddle.quantity == 1
    assert straddle.call.quantity == 1
    assert straddle.put.quantity == 1
    assert straddle.position_type == OptionPositionType.LONG


def test_open_short(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    strike = 110
    expiration = datetime.date(2015, 1, 17)

    straddle = Straddle.create(option_chain, expiration, strike)

    straddle.open_trade(quantity=-1)

    assert straddle.quantity == -1
    assert straddle.call.quantity == -1
    assert straddle.put.quantity == -1
    assert straddle.position_type == OptionPositionType.SHORT

def test_price(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option1_data = copy.deepcopy(data)
    call_price = option1_data['price']
    option1 = Option(**option1_data)
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00010000')
    option2_data = copy.deepcopy(data)
    put_price = option2_data['price']
    option2 = Option(**option2_data)

    # create straddle
    straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)
    assert straddle.price == call_price + put_price

    # open long position
    straddle.open_trade(quantity=1)

    assert straddle.price == call_price + put_price

    # create straddle, open short position
    option1, option2 = Option(**option1_data), Option(**option2_data)
    straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)
    straddle.open_trade(quantity=-1)

    assert straddle.price == call_price + put_price

def test_premium(option_chain_data):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)

    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102C00010000')
    option1_data = copy.deepcopy(data)
    call_price = option1_data['price']
    option1 = Option(**option1_data)
    option1.incur_fees = False
    data = next(x for x in option_chain.options if x['option_id'] == 'AAPL20150102P00010000')
    option2_data = copy.deepcopy(data)
    put_price = option2_data['price']
    option2 = Option(**option2_data)
    option2.incur_fees = False

    premium = (call_price + put_price) * 100

    # create straddle. No open positions, so trade premium is undefined
    straddle = Straddle(options=[option1, option2], spread_type=OptionSpreadType.STRADDLE)
    assert straddle.get_trade_premium() == None

    # open long position
    straddle.open_trade(quantity=1)
    assert straddle.get_trade_premium() == premium

