import datetime

import pytest

from options_framework.option import Option
from options_framework.option_types import OptionType, OptionPositionType, SelectFilter
from options_framework.spreads.vertical import Vertical

from tests.test_data.test_option_daily import *
from test_data.test_options_intraday import *
from mocks import MockEventDispatcher, MockOptionChain
#
# @pytest.fixture(scope='function')
# def option_chain_data():
#     def get_option_data():
#     option_data = [x for x in daily_test_data if x['quote_datetime']]
#     pass
#     # # 'AAPL140207C00510000' 'AAPL140207P00520000'
#     # vals_510 = next(x for x in daily_test_data if x['option_id'] == 'AAPL140207C00510000')
#     # vals_520 = next(x for x in daily_test_data if x['option_id'] == 'AAPL140207C00520000')
#     # option_510 = Option(option_id=vals_510['option_id'], symbol=vals_510['symbol'], strike=vals_510['strike'],
#     #                 expiration=vals_510['expiration'], option_type=vals_510['option_type'],
#     #                 quote_datetime=vals_510['quote_datetime'],spot_price=vals_510['spot_price'],bid=vals_510['bid'],
#     #                 ask=vals_510['ask'], price=vals_510['price'],delta=vals_510['delta'], )
#     # option_520 = Option(option_id=vals_520['option_id'], symbol=vals_520['symbol'], strike=vals_520['strike'],
#     #                 expiration=vals_520['expiration'], option_type=vals_520['option_type'],
#     #                 quote_datetime=vals_520['quote_datetime'],spot_price=vals_520['spot_price'],bid=vals_520['bid'],
#     #                 ask=vals_520['ask'], price=vals_520['price'],delta=vals_520['delta'], )
#     # return option_510, option_520
#
#
# @pytest.fixture
# def test_values_put(scope='function'):
#     vals_510 = next(x for x in daily_test_data if x['option_id'] == 'AAPL140207P00510000')
#     vals_520 = next(x for x in daily_test_data if x['option_id'] == 'AAPL140207P00520000')
#     option1 = Option(option_id=vals_510['option_id'], symbol=vals_510['symbol'], strike=vals_510['strike'],
#                      expiration=vals_510['expiration'], option_type=vals_510['option_type'],
#                      quote_datetime=vals_510['quote_datetime'], spot_price=vals_510['spot_price'], bid=vals_510['bid'],
#                      ask=vals_510['ask'], price=vals_510['price'], delta=vals_510['delta'], )
#     option2 = Option(option_id=vals_520['option_id'], symbol=vals_520['symbol'], strike=vals_520['strike'],
#                      expiration=vals_520['expiration'], option_type=vals_520['option_type'],
#                      quote_datetime=vals_520['quote_datetime'], spot_price=vals_520['spot_price'], bid=vals_520['bid'],
#                      ask=vals_520['ask'], price=vals_520['price'], delta=vals_520['delta'], )
#     return option1, option2
#
# def get_mock_option_chain(scope='function'):
#     pass
#
#
# def test_get_call_debit_spread():
#     option_510, option_520 = test_options_call
#     quote_datetime = datetime.datetime(2014, 2, 5)
#     option_chain = MockOptionChain('AAPL')
#
#     expiration = datetime.date(2014, 2, 7)
#     long_strike = 510
#     short_strike = 520
#
#     vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
#                                             option_type=OptionType.CALL,
#                                             long_strike=long_strike, short_strike=short_strike)
#
#     assert vertical_spread.option_type == OptionType.CALL
#     assert vertical_spread.option_position_type == OptionPositionType.LONG
#     assert vertical_spread.long_option.strike == 510 # 3.25
#     assert vertical_spread.long_option.option_type == OptionType.CALL
#     assert vertical_spread.short_option.strike == 520 # 0.57
#     assert vertical_spread.short_option.option_type == OptionType.CALL
#     assert vertical_spread.max_profit == 732.0
#     assert vertical_spread.max_loss == 268.0
#
# def test_get_call_credit_spread(option_chain_daily):
#     quote_datetime = datetime.datetime(2014, 2, 5)
#     option_chain = option_chain_daily(quote_datetime)
#
#     expiration = datetime.date(2014, 2, 7)
#     long_strike = 520
#     short_strike = 510
#
#     vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
#                                             option_type=OptionType.CALL,
#                                             long_strike=long_strike, short_strike=short_strike)
#
#     assert vertical_spread.option_position_type == OptionPositionType.SHORT
#     assert vertical_spread.long_option.strike == 520
#     assert vertical_spread.short_option.strike == 510
#     assert vertical_spread.max_profit == 268.0
#     assert vertical_spread.max_loss == 732.0
#
#
# def test_get_put_debit_spread(option_chain_daily):
#     quote_datetime = datetime.datetime(2014, 2, 5)
#     option_chain = option_chain_daily(quote_datetime)
#
#     expiration = datetime.date(2014, 2, 7)
#     long_strike = 520
#     short_strike = 510
#
#     vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
#                                             option_type=OptionType.PUT,
#                                             long_strike=long_strike, short_strike=short_strike)
#
#     assert vertical_spread.option_position_type == OptionPositionType.LONG
#     assert vertical_spread.option_type == OptionType.PUT
#     assert vertical_spread.long_option.strike == 520 # 11.1
#     assert vertical_spread.short_option.strike == 510 # 3.68
#     assert vertical_spread.max_profit == 258.0
#     assert vertical_spread.max_loss == 742.0
#
#
# def test_get_put_credit_spread(option_chain_daily):
#     quote_datetime = datetime.datetime(2014, 2, 5)
#     option_chain = option_chain_daily(quote_datetime)
#
#     expiration = datetime.date(2014, 2, 7)
#     long_strike = 510
#     short_strike = 520
#
#     vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
#                                                       option_type=OptionType.PUT,
#                                                       long_strike=long_strike, short_strike=short_strike)
#
#     assert vertical_spread.option_position_type == OptionPositionType.SHORT
#     assert vertical_spread.option_type == OptionType.PUT
#     assert vertical_spread.long_option.strike == 510  # 11.1
#     assert vertical_spread.short_option.strike == 520  # 3.68
#     assert vertical_spread.max_profit == 742.0
#     assert vertical_spread.max_loss == 258.0

# def test_vertical_spread_updates():
#     expiration = datetime.date(2016, 3, 2)
#     long_strike = 1940
#     short_strike = 1970
#     update_date = df_index[-3]
#     option_chain = MockSPXOptionChain()
#     data_loader = MockSPXDataLoader(start=datetime.datetime(2016, 3, 1, 9, 31),
#                                     end=datetime.datetime(2016, 3, 2, 16, 15),
#                                     select_filter=SelectFilter(),
#                                     extended_option_attributes=[])
#     spread_width = 30
#     vertical_spread = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
#                                             option_type=OptionType.CALL,
#                                             long_strike=long_strike, short_strike=short_strike)
#
#     # Open position and get updates
#     portfolio = MockPortfolio()
#     portfolio.bind(new_position_opened=data_loader.on_options_opened)
#     portfolio.open_position(vertical_spread)
#
#     # Advance a couple of date slots and get updates
#     assert vertical_spread.current_value == 1262.0
#     portfolio.next(update_date)
#     assert vertical_spread.current_value == 1190.0
#     # portfolio.next(data_loader.datetimes_list[2])
#     # assert vertical_spread.current_value == 1270.0
#
# def test_get_max_profit_after_closed():
#     pass
#
# def test_get_max_loss_after_closed():
#     pass
#
# def test_credit_spread_required_margin():
#     expiration = datetime.date(2016, 3, 2)
#     long_strike = 1985
#     short_strike = 1955
#     option_chain = MockSPXOptionChain()
#     vertical_spread: Vertical = Vertical.get_vertical(option_chain=option_chain, expiration=expiration,
#                                                       option_type=OptionType.CALL,
#                                                       long_strike=long_strike, short_strike=short_strike)
#
#     quantity = -10
#     expected_margin = 30_000
#
#     vertical_spread.open_trade(quantity=quantity)
#
#     assert vertical_spread.required_margin == expected_margin
#
# def test_get_long_call_vertical_by_delta():
#     expiration = datetime.date(2016, 3, 2)
#     option_chain = MockSPXOptionChain()
#     long_delta = .26
#     short_delta = .11
#
#     call_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration, option_type=OptionType.CALL,
#                                                  long_delta=long_delta, short_delta=short_delta)
#
#     assert call_spread.option_position_type == OptionPositionType.LONG
#     assert call_spread.max_loss == 160.0 # 2.65 - 1.68
#     assert call_spread.max_profit == 840.0 # 5 (spread) - (2.65 - 1.68)
#
# def test_get_short_call_vertical_by_delta():
#     expiration = datetime.date(2016, 3, 2)
#     option_chain = MockSPXOptionChain()
#     short_delta = .26 # 1965 strike, price 2.65 delta 21.65
#     long_delta = .11 # 1970 strike, price 1.68 delta 15.22
#
#     call_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration,
#                                                  option_type=OptionType.CALL,
#                                                  long_delta=long_delta, short_delta=short_delta)
#
#     assert call_spread.option_position_type == OptionPositionType.SHORT
#     assert call_spread.max_profit == 160.0 # 2.65 - 1.68
#     assert call_spread.max_loss == 840.0 # 5 (spread) - (2.65 - 1.68)
#
# def test_get_long_put_vertical_by_delta():
#     expiration = datetime.date(2016, 3, 2)
#     option_chain = MockSPXOptionChain()
#     long_delta = .26
#     short_delta = .16
#
#     put_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration,
#                                                 option_type=OptionType.PUT,
#                                                 long_delta=long_delta, short_delta=short_delta)
#
#     assert put_spread.option_position_type == OptionPositionType.LONG
#
# def test_get_short_put_vertical_by_delta():
#     expiration = datetime.date(2016, 3, 2)
#     option_chain = MockSPXOptionChain()
#     short_delta = .26
#     long_delta = .16
#
#     put_spread = Vertical.get_vertical_by_delta(option_chain=option_chain, expiration=expiration,
#                                                 option_type=OptionType.PUT,
#                                                 long_delta=long_delta, short_delta=short_delta)
#
#     assert put_spread.option_position_type == OptionPositionType.SHORT
#
# def test_long_call_spread_by_delta_and_strike():
#     expiration = datetime.date(2016, 3, 2)
#     option_chain = MockSPXOptionChain()
#     delta = .40
#
#     debit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=option_chain, expiration=expiration,
#                                                                     option_type=OptionType.CALL,
#                                                                     option_position_type=OptionPositionType.LONG,
#                                                                     delta=delta, spread_width=5)
#     assert debit_spread.option_position_type == OptionPositionType.LONG
#     assert debit_spread.long_option.strike < debit_spread.short_option.strike
#     assert abs(debit_spread.long_option.strike - debit_spread.short_option.strike) == 5
#     assert debit_spread.long_option.delta < delta
#
# def test_SHORT_call_spread_by_delta_and_strike():
#     expiration = datetime.date(2016, 3, 2)
#     option_chain = MockSPXOptionChain()
#     delta = .40
#
#     credit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=option_chain, expiration=expiration,
#                                                                     option_type=OptionType.CALL,
#                                                                     option_position_type=OptionPositionType.SHORT,
#                                                                     delta=delta, spread_width=5)
#
#     assert credit_spread.option_position_type == OptionPositionType.SHORT
#     assert credit_spread.short_option.strike == 1955
#     assert credit_spread.long_option.strike == 1960
#
# def test_long_put_spread_by_delta_and_strike():
#     expiration = datetime.date(2016, 3, 2)
#     option_chain = MockSPXOptionChain()
#     delta = .40
#
#     debit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=option_chain, expiration=expiration,
#                                                                     option_type=OptionType.PUT,
#                                                                     option_position_type=OptionPositionType.LONG,
#                                                                     delta=delta, spread_width=5)
#
#     assert debit_spread.option_position_type == OptionPositionType.LONG
#     assert debit_spread.short_option.strike == 1935
#     assert debit_spread.long_option.strike == 1940
#
# def test_SHORT_put_spread_by_delta_and_strike():
#     expiration = datetime.date(2016, 3, 2)
#     option_chain = MockSPXOptionChain()
#     delta = .40
#
#     credit_spread = Vertical.get_vertical_by_delta_and_spread_width(option_chain=option_chain, expiration=expiration,
#                                                                     option_type=OptionType.PUT,
#                                                                     option_position_type=OptionPositionType.SHORT,
#                                                                     delta=delta, spread_width=5)
#
#     assert credit_spread.option_position_type == OptionPositionType.SHORT
#     assert credit_spread.short_option.strike == 1940
#     assert credit_spread.long_option.strike == 1935
