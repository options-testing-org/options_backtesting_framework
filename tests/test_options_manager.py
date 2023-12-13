import datetime

from options_framework.option_types import SelectFilter, OptionType, FilterRange
from options_framework.spreads.single import Single
from options_framework.test_manager import OptionTestManager
from options_framework.data.data_loader import DataLoader
from options_framework.option_chain import OptionChain

def test_get_sql_data_loader_test_manager():
    start_date = datetime.datetime(2016, 3, 1, 9, 31)
    end_date = datetime.datetime(2016, 3, 1, 16,15)
    starting_cash = 100_000.0
    select_filter = SelectFilter(symbol='SPXW')

    option_test_manager = OptionTestManager(start_datetime=start_date, end_datetime=end_date,
                                            select_filter=select_filter, starting_cash=starting_cash)
    assert option_test_manager is not None

def test_manager_portfolio_open_triggers_option_updates_load():
    start_date = datetime.datetime(2016, 3, 1, 9, 31)
    end_date = datetime.datetime(2016, 3, 1, 16, 15)
    starting_cash = 100_000.0
    select_filter = SelectFilter(symbol='SPXW', option_type=OptionType.CALL, strike_offset=FilterRange(low=50, high=50))

    option_test_manager = OptionTestManager(start_datetime=start_date, end_datetime=end_date,
                                            select_filter=select_filter, starting_cash=starting_cash)
    option_test_manager.get_current_option_chain(start_date)

    portfolio = option_test_manager.portfolio
    loader = option_test_manager.data_loader

    chain = option_test_manager.option_chain
    expiration = datetime.date(2016, 3, 2)
    single = Single.get_single_position(options=chain.option_chain, expiration=expiration, option_type=OptionType.CALL, strike=1910)
    assert single.option.update_cache is None
    portfolio.open_position(option_position=single, quantity=1)
    assert len(single.option.update_cache) > 0
    assert single.option.quote_datetime == start_date
    next_quote = datetime.datetime(2016, 3, 1, 9, 32)

    # advance to the next quote
    portfolio.next(next_quote)
    assert single.option.quote_datetime == next_quote





