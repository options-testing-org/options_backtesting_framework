from options_framework.option_types import OptionType, TransactionType
from options_framework.option_chain import OptionChain
import os
import pathlib

def test_read_option_file():
    test_folder = pathlib.Path(os.getcwd())
    test_data_file = test_folder.joinpath("test_data", "L2_options_20230301.csv")
    chain = OptionChain()
    chain.load_data_from_file(test_data_file)
