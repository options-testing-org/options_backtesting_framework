from pathlib import Path
import datetime
from tempfile import NamedTemporaryFile
from options_framework.option import Option
from options_framework.utils.helpers import *

def test_temp_data_dir_cleanup_removes_existing_files_from_temp_dir():
    temp_dir = Path.cwd().joinpath('temp_data')
    if not temp_dir.exists():
        temp_dir.mkdir()

    # create some temp files
    for i in range(5):
        with NamedTemporaryFile(delete=False, dir='./temp_data') as f:
            x = Path(f.name)

    temp_data_dir_cleanup()

    files = [x for x in temp_dir.iterdir() if x.is_file()]
    assert len(files) == 0



def expiration_to_date(x):
    return {**x, 'expiration': datetime.datetime.strptime(x['expiration'], "%Y-%m-%d").date()}

def create_option_objects(option_data):
    options = []
    for item in option_data:
        option_id = item['option_id']
        option = Option(
                option_id=option_id,
                symbol=item['symbol'],
                expiration=item['expiration'],
                strike=item['strike'],
                option_type=item['option_type'],
                quote_datetime=item['quote_datetime'],
                spot_price=item['spot_price'],
                bid=item['bid'],
                ask=item['ask'],
                price=item['price'],
                delta=item['delta'],
                gamma=item['gamma'],
                theta=item['theta'],
                vega=item['vega'],
                rho=item['rho'],
                volume=item['volume'],
                open_interest=item['open_interest'] ,
                implied_volatility=item['implied_volatility'] )
        options.append(option)
    return options

def get_option_chain_items(quote_date, df, test_options):
    df = df[df['quote_datetime'] == quote_date]
    expirations = [x for x in list(df['expiration'].unique())]
    exp_str = df[['expiration', 'strike']].drop_duplicates().to_numpy().tolist()
    expiration_strikes = {exp: [s for (e, s) in exp_str if e == exp] for exp in expirations}
    return test_options, expirations, expiration_strikes