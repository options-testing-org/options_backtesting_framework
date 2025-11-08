import datetime

import pytest
import copy

from conftest import create_update_cache
from options_framework.option_portfolio import OptionPortfolio
from options_framework.option_types import OptionCombinationType, OptionPositionType, SelectFilter
from options_framework.spreads.single import Single
from options_framework.config import settings
from test_data.test_options_intraday import *

@pytest.fixture
def test_position_1():
    option = next((x for x in t1_options if x.option_id == 382520), None)
    test_option = copy.copy(option)
    start_date = datetimes[0]
    end_date = datetimes[-1]
    single = Single([test_option],  OptionCombinationType.SINGLE, OptionPositionType.LONG)
    return single, start_date, end_date

@pytest.fixture
def test_position_2():
    option = next((x for x in t1_options if x.option_id == 427182), None)
    test_option = copy.copy(option)
    start_date = datetimes[0]
    end_date = start_date + datetime.timedelta(days=1)
    single = Single([test_option], OptionCombinationType.SINGLE, OptionPositionType.LONG)
    return single, start_date, end_date

@pytest.fixture
def test_cache():
    df = pd.DataFrame(df_values, index=df_index, columns=df_columns)
    df.sort_index()
    return df

# def test_new_portfolio_cash_balance(test_position_1):
#     position, start, end = test_position_1
#
#     pf = OptionPortfolio(100_000.0, start, end)
#
#     assert pf.cash == 100_000.0
#     assert pf.portfolio_value == 100_000.0
#
# def test_open_long_option_position(test_position_1, test_cache):
#     position, start, end = test_position_1
#     options_df = test_cache
#     pf = OptionPortfolio(100_000.0, start, end)
#
#     def on_options_opened(portfolio, options: list[Option]) -> None:
#         nonlocal options_df
#         for o in options:
#             cache = options_df[options_df.option_id == o.option_id]
#             o.update_cache = cache
#         pass
#
#     pf.bind(new_position_opened=on_options_opened)
#     pf.open_position(option_position=position, quantity=1)
#     assert pf.cash == 97_849.5
#     assert pf.portfolio_value == 99_999.5
#
# def test_get_portfolio_value_with_open_positions(test_position_1, test_position_2, test_cache):
#     position1, start, end = test_position_1
#     position2, start, end = test_position_2
#     options_df = test_cache
#     pf = OptionPortfolio(100_000.0, start, end)
#
#     def on_options_opened(portfolio, options: list[Option]) -> None:
#         nonlocal options_df
#         for o in options:
#             cache = options_df[options_df.option_id == o.option_id]
#             o.update_cache = cache
#         pass
#
#     pf.bind(new_position_opened=on_options_opened)
#     pf.open_position(option_position=position1, quantity=1)
#     pf.open_position(option_position=position2, quantity=1)
#
#     assert pf.cash == 96_224.0
#     assert pf.portfolio_value == 99_999.0
#
# def test_portfolio_updates_when_option_values_are_updated(test_position_1, test_position_2, test_cache):
#     position1, start, end = test_position_1
#     position2, start, end = test_position_2
#     update_date = df_index[-3]
#
#     options_df = test_cache
#     pf = OptionPortfolio(100_000.0, start, end)
#     def on_options_opened(portfolio, options: list[Option]) -> None:
#         nonlocal options_df
#         for o in options:
#             cache = options_df[options_df.option_id == o.option_id]
#             o.update_cache = cache
#         pass
#
#     pf.bind(new_position_opened=on_options_opened)
#     pf.open_position(option_position=position1, quantity=1)
#     pf.open_position(option_position=position2, quantity=1)
#
#     pf.next(update_date)
#     assert pf.portfolio_value == 99_999.0
#     assert pf.cash == 96_224.0
#
# def test_portfolio_values_when_position_is_closed(test_position_1, test_cache):
#     position1, start, end = test_position_1
#     update_date = df_index[-3]
#     pf = OptionPortfolio(100_000.0, start, end)
#     options_df = test_cache
#
#     def on_options_opened(portfolio, options: list[Option]) -> None:
#         nonlocal options_df
#         for o in options:
#             cache = options_df[options_df.option_id == o.option_id]
#             o.update_cache = cache
#         pass
#
#     pf.bind(new_position_opened=on_options_opened)
#
#     # spend $2150 x 2 + fee to open options worth $4301
#     pf.open_position(option_position=position1, quantity=2)
#     assert pf.cash == 95_699.0
#     assert pf.portfolio_value == 99_999
#
#     # options now worth $4_140 Cash remains unchanged
#     pf.next(update_date)
#
#     assert pf.portfolio_value == 99_839.0
#     assert pf.cash == 95_699.0
#
#     # close options. No open options, so worth $0.00. Cash added $2000.00 for selling options
#     pf.close_position(position1, quantity=2)
#     assert pf.cash == 99_838.0
#     assert pf.portfolio_value == 99_838.0
#
#
# def test_portfolio_values_with_multiple_positions(test_position_1, test_position_2, test_cache):
#     position1, start, end = test_position_1
#     position2, start, end = test_position_2
#     update_date = df_index[-3]
#
#     options_df = test_cache
#     pf = OptionPortfolio(100_000.0, start, end)
#
#     def on_options_opened(portfolio, options: list[Option]) -> None:
#         nonlocal options_df
#         for o in options:
#             cache = options_df[options_df.option_id == o.option_id]
#             o.update_cache = cache
#         pass
#
#     pf.bind(new_position_opened=on_options_opened)
#
#     # open two positions
#     pf.open_position(option_position=position1, quantity=1)
#     pf.open_position(option_position=position2, quantity=1)
#
#     assert pf.cash == 96_224.0
#     assert pf.portfolio_value == 99_999.0
#
#     # update both positions
#     pf.next(update_date)
#     assert pf.portfolio_value == 99_999.0
#     assert pf.cash == 96_224.0
#
#     # close one position
#     pf.close_position(position1, quantity=1)
#     assert pf.cash == 98_293.5
#     assert pf.portfolio_value == 99_998.5
#
# def test_expired_position_closes_position(test_position_1, test_cache):
#     position1, start, end = test_position_1
#     options_df = test_cache
#     exp_quote_date = df_index[-1]
#     pf = OptionPortfolio(100_000.0, start, end)
#
#     def on_options_opened(portfolio, options: list[Option]) -> None:
#         nonlocal options_df
#         for o in options:
#             cache = options_df[options_df.option_id == o.option_id]
#             o.update_cache = cache
#         pass
#
#     pf.bind(new_position_opened=on_options_opened)
#
#     # open position
#     pf.open_position(option_position=position1, quantity=1)
#
#     # position expires
#     pf.next(exp_quote_date)
#
#     assert len(pf.positions) == 0
#     assert len(pf.closed_positions) == 1
#
#
#
#
