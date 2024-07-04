import datetime
from options_framework.option import Option, TradeOpenInfo
from options_framework.option_portfolio import OptionPortfolio
from options_framework.option_types import OptionType, OptionCombinationType, OptionPositionType
from options_framework.spreads.single import Single

from mocks import *
from test_data.spx_test_options import *

class TestDispatch:
    options_df = None
    def on_option_open(self, trade_open_info: TradeOpenInfo):
        print('test dispatch option opened')

    def on_options_opened(portfolio, options: list[Option]) -> None:
        nonlocal options_df
        for o in options:
            cache = options_df[options_df.option_id == o.option_id]
            o.update_cache = cache
        pass

option_id = '1'
exp = datetime.date(2021, 7, 16)
qd = datetime.datetime(2021, 7, 1, 9, 45)
end_dt = qd + datetime.timedelta(days=2)
ticker = 'XYZ'
strike, spot_price, bid, ask, price = (100.0, 90.0, 1.0, 2.0, 1.5)

option = Option(option_id=option_id, symbol=ticker, strike=strike, expiration=exp,
                         option_type=OptionType.CALL, quote_datetime=qd,
                         spot_price=spot_price, bid=bid, ask=ask, price=price)
test_dispatch = TestDispatch()

option.bind(open_transaction_completed=test_dispatch.on_option_open)
option.open_trade(quantity=1)


option = next((x for x in t1_options if x.option_id == 382520), None)
start_date = datetimes[0]
end_date = datetimes[-1]
single = Single([option],  OptionCombinationType.SINGLE, OptionPositionType.LONG)
df = pd.DataFrame(df_values, index=df_index, columns=df_columns)
df.sort_index()

test_dispatch.options_df = df[df['option_id'] == 382520]

data_loader = MockSPXDataLoader()


pass
