from mocks import *
import pytest

@pytest.fixture
def mock_settings():
    start_date = datetime.datetime.strptime('2014-02-05', '%Y-%m-%d')
    end_date = datetime.datetime.strptime('2014-02-10', '%Y-%m-%d')
    return start_date, end_date


def test_initialize_mock_data_loader(mock_settings):
    start_date, end_date = mock_settings
    mock_dl = MockIntegrationDataLoader(start=start_date, end=end_date)

    test_pickle_file = None

    def mock_data_loaded(quote_datetime: datetime.datetime, pickle: str, datetimes: list[datetime.datetime]):
        nonlocal test_pickle_file
        test_pickle_file = pickle

    mock_dl.bind(option_chain_loaded=mock_data_loaded)
    mock_dl.load_option_chain_data('AAPL', start_date, end_date)

    assert test_pickle_file.exists()

