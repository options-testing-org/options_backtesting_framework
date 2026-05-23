"""
Daily Prices:
Put Credit Spread (Vertical) Strategy Rules:

    * Get the options with the closest expiration to 90 dte
    * Find the short put option closest to -0.15 delta
    * Find the long put option closest to 80 points further OTM
    * The stop loss is 2x the credit received
    * The profit target is 70% of the credit received
    * Only open if MSFT open price is greater than the 200 SMA
    * Risk 10% of portfolio per trade
    * Only one active trade

"""

from options_framework import OptionPortfolio, Vertical, OptionPositionType, settings, get_market_dates
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import talib

# Overriding settings.toml here so this script will run.
# See the readme doc for how to set up the options directory structure
# the stock data files setting, along with any other item you want in your settings, are not
# required by the options library
settings["options_directory"] = str(Path(__file__).parent / "data")
settings["stock_data_files"] = str(Path(__file__).parent / "data" / "daily" / "MSFT")
settings['data_frequency'] = 'daily' # override the settings file value

# Custom event handlers can be created for portfolio or option events
# See the readme for events that can be handled.
def position_is_expiring(my_position):
    # add the user_defined "exit_reason" to the position. Later, when getting the trade records,
    # this field is expected to be present. Handling this event is how you can inject
    # your own logic
    my_position.user_defined['exit_reason'] = 'expired'

# set up test parameters
starting_equity = 100_000
start_date = datetime(2023, 1, 3)
end_date = datetime(2024, 12, 31)
target_dte = 90
target_delta = -0.15
spread_width = 80
position_risk = 0.10
profit_percent = 0.70

df_daily = pd.read_parquet(Path(settings["stock_data_files"]).joinpath("MSFT.parquet"))
df_daily = df_daily.set_index("quote_datetime")
df_daily = df_daily.sort_index()

# take the 200 ma of the close price - take the price from the previous day to avoid
# peeking into the future
df_daily['ma200'] = talib.SMA(df_daily['close'].shift(1).to_numpy(), timeperiod=200)
df_daily = df_daily.loc[start_date:end_date]

# Helper function to get market dates. All non-market days are skipped. Optionally, you can
# skip economic and half-days as well by adding the settings to the settings.toml file
test_dates = get_market_dates(start_date=start_date, end_date=end_date)

portfolio = OptionPortfolio(cash=starting_equity, start_date=start_date, end_date=end_date)

# Optionally bind to position_closed or position_expired events to capture this event in your test
portfolio.bind(position_expired=position_is_expiring)

print(f'{test_dates[0].date().isoformat()} portfolio value: ${portfolio.current_value:,.2f}')

for dt in test_dates:
    open_price = df_daily.loc[dt, 'open']
    ma_200 = df_daily.loc[dt, 'ma200']

    # Pass current dt to the portfolio so the correct option chains will be fetched
    # If you are trading with multiple symbols, you can pass an array of symbols
    portfolio.next(dt, 'MSFT')

    # get the option chain from the portfolio. It will have the quotes from its "current_datetime" property
    # which is set when "next" is called on the portfolio
    option_chain = portfolio.option_chains['MSFT']

    # check if trades are closing today. Make a copy so the open positions list
    # so the list isn't changing as you're looping through it. Closing removes items from the portfolio's list
    positions = portfolio.positions.copy()
    for position in positions:
        pnl = position.get_profit_loss()
        pnl_pct = position.get_profit_loss_percent()
        exit_trade = False

        max_loss = position.user_defined['max_loss_premium']
        if pnl < max_loss:
            exit_trade = True
            exit_reason = 'stop loss'

        if pnl_pct >= profit_percent:
            exit_trade = True
            exit_reason = 'profit'

        if exit_trade:
            # close the trade from the portfolio. Adding the user_defined "exit_reason"
            portfolio.close_position(option_spread=position, exit_reason=exit_reason)
            print(f'{dt.date().isoformat()} closed position {position.instance_id}: for {-position.price}, portfolio value: ${portfolio.current_value:,.2f}')

    if open_price >= ma_200 and len(portfolio.positions) == 0:
        # find the expiration closest to the target dte
        expirations = option_chain.expirations
        exp_target_dt = dt + timedelta(days=target_dte)
        expiration = min(expirations, key=lambda x: abs(x - exp_target_dt.date()).days)

        # get option quotes for the selected expiration. Since we only want puts, we can select on that as well.
        options = [x for x in option_chain.options if x['expiration'] == expiration and x['option_type'] == 'put']

        # Short option: find the option with the delta closest to the target
        deltas = [x['delta'] for x in options]
        delta = min(deltas, key=lambda x: abs(x - target_delta))
        short_strike = next(x['strike'] for x in options if x['delta'] == delta)

        # Long option: find the option with the closest strike that is at least 10 points away
        # first get the strikes available for the selected expiration
        strikes = option_chain.expiration_strikes[expiration]
        strikes.sort(reverse=True)
        long_strike = next(x for x in strikes if x <= (short_strike - spread_width))

        # define the option spread using the create function of the spread type, in this case, VERTICAL
        put_credit_spread = Vertical.create(
            option_chain=option_chain,
            expiration=expiration,
            option_type="put",
            short_strike=short_strike,
            long_strike=long_strike,
            position_type=OptionPositionType.SHORT)

        # calculate the number of contracts to open
        max_position_risk = portfolio.current_value * position_risk
        risk_per_contract = -(put_credit_spread.price * 100 * 3)
        shares = max(1, int(round((max_position_risk / risk_per_contract), 0)))

        # open the position in the portfolio. You can add any user-defined values by just adding it to the kwargs
        # option_spread and quantity are required. Any keyword arguments added will be available in a dictionary
        # named user_defined
        portfolio.open_position(option_spread=put_credit_spread, quantity=shares, ma_200=ma_200)

        # You can add items directly to "user_defined"
        # Since the max loss is 2x premium received, we need to use 3 for the multiplier, the
        # cash received is not considered to be a part of the max loss
        max_loss_premium = put_credit_spread.get_trade_premium() * 3
        put_credit_spread.user_defined["max_loss_premium"] = max_loss_premium

        print(f'{dt.date().isoformat()} opened position {put_credit_spread.instance_id}: {put_credit_spread.quantity} contracts for {-put_credit_spread.price}')

# after looping through all the dates, you can close any remaining open positions
positions = portfolio.positions.copy()
for position in positions:
    portfolio.close_position(option_spread=position, exit_reason='end of test')

# When the portfolio closes positions, it moves them to the "closed_positions" list
# We can use this list to analyze the test results
trades = [{
    'id': x.instance_id, # Each position is identified by a unique id
    'symbol': x.symbol,
    'entry_date': x.get_open_datetime(),
    'exit_date': x.get_close_datetime(),
    'open_premium': x.get_trade_premium(),
    'expiration': x.expiration,
    'long_option_id': x.long_option.instance_id, # Each option is also identified by its own unique id
    'long_strike': x.long_option.strike,
    'short_strike': x.short_option.strike,
    'short_option_id': x.short_option.instance_id,
    'open_spot_price': x.short_option.trade_open_info.spot_price,
    'close_spot_price': x.spot_price,
    'vertical_open_price': x.get_trade_price(),
    'gross_pnl': x.get_profit_loss(),
    'net_pnl': (x.get_profit_loss() - x.get_fees()),
    'pnl_pct': x.get_profit_loss_percent(),
    'days_in_trade': x.get_days_in_trade(),
    'fees': x.get_fees(),
    'ma_200': x.user_defined['ma_200'],
    'exit_reason': x.user_defined['exit_reason'], }
    for x in portfolio.closed_positions]

# Now you can use the trade data to analyze the test
df_trades = pd.DataFrame(trades)

print(f'Ending portfolio value: ${portfolio.current_value:,.2f}')
