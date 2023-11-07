from options_framework.option_types import OptionType, TransactionType
from options_framework.option_chain import OptionChain
import os
import pathlib
import datetime

def test_read_all_records_from_daily_option_file():
    test_folder = pathlib.Path(os.getcwd())
    test_data_file = test_folder.joinpath("test_data", "L2_options_20230301.csv")
    chain = OptionChain()
    chain.load_daily_data_from_file(test_data_file)
    test_chain = chain.option_chain

    assert len(test_chain) == 2_190

def test_get_list_of_expirations_in_chain():
    test_folder = pathlib.Path(os.getcwd())
    test_data_file = test_folder.joinpath("test_data", "L2_options_20230301.csv")
    chain = OptionChain()
    chain.load_daily_data_from_file(test_data_file)
    expirations = chain.get_expirations()

    assert len(expirations) == 19

def test_get_chain_for_expiration_range_from_daily_options_file():
    first_exp = datetime.datetime.strptime("03-11-2023", "%m-%d-%Y")
    last_exp = datetime.datetime.strptime("04-06-2023", "%m-%d-%Y")
    test_folder = pathlib.Path(os.getcwd())
    test_data_file = test_folder.joinpath("test_data", "L2_options_20230301.csv")
    chain = OptionChain()
    chain.load_daily_data_from_file(test_data_file, select_expiration_range=[first_exp, last_exp])
    expirations = chain.get_expirations()

    assert len(expirations) == 4
    assert expirations[-1] == last_exp

