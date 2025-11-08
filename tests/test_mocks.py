from mocks import *
import pytest
from options_framework.config import settings
from options_framework.option_types import SelectFilter

@pytest.fixture
def mock_settings():
    start_date = datetime.datetime.strptime('2014-02-05', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2014-02-10', '%Y-%m-%d')
    select_filter = SelectFilter()
    return start_date, end_date, select_filter


def test_initialize_mock_data_loader(mock_settings):
    start_date, end_date, filter = mock_settings
    mock_dl = MockIntegrationDataLoader(start=start_date, end=end_date, select_filter=filter)

    test_pickle_file = None

    def mock_data_loaded(symbol: str, quote_datetime: datetime.datetime, pickle: str):
        nonlocal test_pickle_file
        test_pickle_file = pickle

    mock_dl.bind(option_chain_loaded=mock_data_loaded)
    mock_dl.load_option_chain_data('AAPL', start_date, end_date)

    assert test_pickle_file.exists()

