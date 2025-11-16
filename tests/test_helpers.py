import pandas as pd
import datetime
from tempfile import NamedTemporaryFile
from options_framework.option import Option
from options_framework.option_types import OptionType
from options_framework.utils.helpers import *
from test_data.test_option_daily import daily_option_data

column_names = ['data_date', 'option_id', 'symbol', 'underlying_price', 'option_type', 'expiration',
                    'strike', 'bid', 'ask', 'mid', 'volume', 'open_interest', 'iv', 'delta', 'gamma', 'theta', 'vega',
                    'rho']
daily_col_mapping = {
        'data_date': 'quote_datetime',
        'option_id': 'option_id',
        'symbol': 'symbol',
        'underlying_price': 'spot_price',
        'option_type': 'option_type',
        'expiration': 'expiration',
        'strike': 'strike',
        'bid': 'bid',
        'ask': 'ask',
        'mid': 'price',
        'volume': 'volume',
        'open_interest': 'open_interest',
        'iv': 'implied_volatility',
        'delta': 'delta',
        'gamma': 'gamma',
        'theta': 'theta',
        'vega': 'vega',
        'rho': 'rho',
    }

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

def dump(o):
    #datetime.date(2016, 3, 2)
    op_inst = f'Option(option_id=\'{o.option_id}\', symbol=\'{o.symbol}\', '
    op_inst += f'expiration=datetime.date({o.expiration.year}, {o.expiration.month}, {o.expiration.day}), strike={o.strike},'
    op_inst += f'option_type={o.option_type}, quote_datetime=datetime.datetime({o.quote_datetime.year}, '
    op_inst += f'{o.quote_datetime.month}, {o.quote_datetime.day}, {o.quote_datetime.hour}, {o.quote_datetime.minute}),'
    op_inst += f'spot_price={o.spot_price},'
    op_inst += f'bid={o.bid}, ask={o.ask}, price={o.price}, delta={o.delta}, gamma={o.gamma}, theta={o.theta},'
    op_inst += f'vega={o.vega}, rho={o.rho}, open_interest={o.open_interest}, implied_volatility={o.implied_volatility}),'
    print('    ', op_inst)

def daily_quote_datetime_to_datetime(x):
    return {**x, 'quote_datetime': datetime.datetime.strptime(x['quote_datetime'], "%Y-%m-%d")}

def daily_option_type_from_str(x):
    return {**x, 'option_type': OptionType.CALL if x['option_type'] == 'call' else OptionType.PUT}

def expiration_to_date(x):
    return {**x, 'expiration': datetime.datetime.strptime(x['expiration'], "%Y-%m-%d").date()}

def create_option_objects(option_data):
    options = []
    for item in option_data:
        option = Option(**item)
        options.append(option)
    return options
def get_daily_fields():

    col_mapping = {
        'data_date': 'quote_datetime',
        'option_id': 'option_id',
        'symbol': 'symbol',
        'underlying_price': 'spot_price',
        'option_type': 'option_type',
        'expiration': 'expiration',
        'strike': 'strike',
        'bid': 'bid',
        'ask': 'ask',
        'mid': 'price',
        'volume': 'volume',
        'open_interest': 'open_interest',
        'iv': 'implied_volatility',
        'delta': 'delta',
        'gamma': 'gamma',
        'theta': 'theta',
        'vega': 'vega',
        'rho': 'rho',
    }
    fields = [col_mapping[f] for f in column_names if f in col_mapping.keys()]
    return fields

def get_daily_option_chain_items(quote_date):
    df = get_daily_test_df()
    df = df[df['quote_datetime'] == quote_date]
    option_data = get_daily_option_data()
    option_data = [x for x in option_data if x['quote_datetime'] == quote_date]
    test_options = create_option_objects(option_data)
    expirations = [x for x in list(df['expiration'].unique())]
    exp_str = df[['expiration', 'strike']].drop_duplicates().to_numpy().tolist()
    expiration_strikes = {exp: [s for (e, s) in exp_str if e == exp] for exp in expirations}
    return test_options, expirations, expiration_strikes



def get_daily_option_data():
    data = list(map(lambda x: dict(zip(get_daily_fields(), x)), daily_option_data))
    data = list(map(daily_quote_datetime_to_datetime, data))
    data = list(map(expiration_to_date, data))
    data = list(map(daily_option_type_from_str, data))
    return data

def get_daily_test_df():
    df = pd.DataFrame(daily_option_data, columns=column_names)
    df = df.rename(columns=daily_col_mapping)
    df = df.sort_values(by=['quote_datetime', 'expiration', 'strike'])
    df['quote_datetime'] = pd.to_datetime(df['quote_datetime'])
    df['expiration'] = pd.to_datetime(df['expiration']).dt.date
    return df

