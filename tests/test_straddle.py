import datetime
import pytest

from options_framework.option_types import OptionPositionType
from options_framework.spreads.straddle import Straddle


@pytest.mark.parametrize("strike, position_type, expected_repr", [(110.0, OptionPositionType.LONG, '<STRADDLE({0}) AAPL 110.0 2015-01-17 LONG>'),
                                                                  (120.0, OptionPositionType.SHORT, '<STRADDLE({0}) AAPL 120.0 2015-01-17 SHORT>'),
                                                                          ])
def test_repr(option_chain_data, strike, position_type, expected_repr):
    quote_date = datetime.datetime(2014, 12, 30, 0, 0)
    option_chain = option_chain_data('daily', quote_date)
    expiration = datetime.date(2015, 1, 17)
    strike = strike

    straddle = Straddle.create(option_chain=option_chain,
                               strike=strike,
                               expiration=expiration,
                               option_position_type=position_type)

    expected_repr = expected_repr.format(straddle.position_id)
    repr_ = straddle.__repr__()

    assert expected_repr == repr_


