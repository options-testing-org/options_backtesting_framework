import pytest
from options_framework.option_types import OptionType, TransactionType
from options_framework.option_chain import OptionChain
import os
import pathlib
import datetime

@pytest.mark.xfail(raises=FileNotFoundError)
def test_read_all_records_from_daily_option_file():
    test_folder = pathlib.Path(os.getcwd())
    test_data_file = test_folder.joinpath("test_data", "L2_options_20230301.csv")
    chain = OptionChain()
    chain.load_delta_neutral_data_from_file(test_data_file)
    test_chain = chain.option_chain

    assert len(test_chain) == 2_190

@pytest.mark.xfail(raises=FileNotFoundError)
def test_get_list_of_expirations_in_chain():
    test_folder = pathlib.Path(os.getcwd())
    test_data_file = test_folder.joinpath("test_data", "L2_options_20230301.csv")
    chain = OptionChain()
    chain.load_delta_neutral_data_from_file(test_data_file)
    expirations = chain.get_expirations()

    assert len(expirations) == 19

@pytest.mark.xfail(raises=FileNotFoundError)
def test_get_chain_for_expiration_range_from_daily_options_file():
    first_exp = datetime.datetime.strptime("03-11-2023", "%m-%d-%Y")
    last_exp = datetime.datetime.strptime("04-06-2023", "%m-%d-%Y")
    exp_range = {"low": first_exp, "high": last_exp}
    test_folder = pathlib.Path(os.getcwd())
    test_data_file = test_folder.joinpath("test_data", "L2_options_20230301.csv")
    chain = OptionChain()
    chain.load_delta_neutral_data_from_file(test_data_file, expiration_range=exp_range)
    expirations = chain.get_expirations()

    assert len(expirations) == 4
    assert expirations[-1] == last_exp

@pytest.mark.xfail(raises=FileNotFoundError)
def test_get_chain_with_option_type_filter():
    first_exp = datetime.datetime.strptime("03-03-2023", "%m-%d-%Y")
    last_exp = datetime.datetime.strptime("03-03-2023", "%m-%d-%Y")
    exp_range = {"low": first_exp, "high": last_exp}
    test_folder = pathlib.Path(os.getcwd())
    test_data_file = test_folder.joinpath("test_data", "L2_options_20230301.csv")
    chain = OptionChain()
    chain.load_delta_neutral_data_from_file(test_data_file, option_type_filter=OptionType.CALL,
                                            expiration_range=exp_range)
    options = chain.option_chain

    assert all(o.option_type == OptionType.CALL for o in options)
