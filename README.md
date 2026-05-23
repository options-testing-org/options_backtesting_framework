# options-framework

A Python library for backtesting options trading strategies. You provide historical options data in DuckDB format, describe your strategy in plain Python, and the framework handles position tracking, P&L accounting, fees, and event-driven portfolio management.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start — Daily Data](#quick-start--daily-data)
- [Quick Start — Intraday Data](#quick-start--intraday-data)
- [Setting Up Your Data](#setting-up-your-data)
- [Configuration Reference](#configuration-reference)
- [Available Spread Types](#available-spread-types)
- [Portfolio Usage](#portfolio-usage)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

```bash
pip install options-framework
```

Requires Python 3.10 or higher.

---

## Quick Start — Daily Data

> **Coming soon.** A complete daily backtesting example will be added here.
>
> It will cover:
> - Loading a DuckDB data file
> - Configuring `settings.toml` for daily data
> - Opening and managing a position through `OptionPortfolio`
> - Reading P&L results at the end of the backtest

---

## Quick Start — Intraday Data

> **Coming soon.** A complete intraday backtesting example will be added here.
>
> It will cover:
> - Loading an intraday DuckDB data file
> - Configuring `settings.toml` for intraday data with `minute_granularity`
> - Iterating through intraday bars with `OptionPortfolio.next()`
> - Handling intraday open and close times

---

## Setting Up Your Data

The framework reads options price data from [DuckDB](https://duckdb.org/) files. Data is split across multiple files to keep file sizes manageable and lookups fast.

### Directory Layout

```
options_data/
├── daily/
│   ├── SPY/
│   │   ├── SPY_options.duckdb
│   │   └── SPY_by_contract.duckdb        ← optional, improves performance
│   └── MSFT/
│       ├── MSFT_options.duckdb
│       └── MSFT_by_contract.duckdb       ← optional, improves performance
└── intraday/
    ├── SPY/
    │   ├── SPY_2020_01_options.duckdb
    │   ├── SPY_2020_01_by_contract.duckdb ← optional, improves performance
    │   ├── SPY_2020_02_options.duckdb
    │   └── SPY_2020_02_by_contract.duckdb
    └── MSFT/
        ├── MSFT_2020_01_options.duckdb
        └── MSFT_2020_01_by_contract.duckdb
```

Point `options_directory` in your `settings.toml` at the root folder (`options_data/` above). The `daily/` and `intraday/` subfolders are expected automatically — you do not need to configure them separately.

### File Naming Convention

**Daily data** — one pair of files per symbol:

| File | Description |
|---|---|
| `SPY_options.duckdb` | Required. All option quotes sorted by `quote_datetime`. |
| `SPY_by_contract.duckdb` | Optional. Same data sorted by `option_id`. Used to retrieve all price updates for a specific contract when a trade is opened. Significantly faster for large datasets. |

**Intraday data** — one pair of files per symbol per month:

| File | Description |
|---|---|
| `SPY_2020_01_options.duckdb` | Required. All option quotes for January 2020, sorted by `quote_datetime`. |
| `SPY_2020_01_by_contract.duckdb` | Optional. Same data sorted by `option_id`. |

The year and month in the filename must be zero-padded (`2020_01`, not `2020_1`).

When the `_by_contract` file is present, the framework uses it automatically for contract-level lookups. If it is absent, the framework falls back to the `_options` file. The two files must always contain identical data — the only difference is sort order.

### DuckDB Schema

Your DuckDB tables must include these columns. Column names and types must match exactly.

**Required columns:**

| Column | Type | Description |
|---|---|---|
| `quote_datetime` | `TIMESTAMP` | Date/time of the price quote |
| `option_id` | `VARCHAR` | Unique contract identifier (e.g. `SPY20260121P00450000`) |
| `symbol` | `VARCHAR` | Underlying ticker symbol (e.g. `SPY`) |
| `strike` | `DOUBLE` | Strike price |
| `expiration` | `DATE` | Expiration date |
| `option_type` | `VARCHAR` | `'call'` or `'put'` |
| `spot_price` | `DOUBLE` | Underlying price at quote time |
| `bid` | `DOUBLE` | Bid price |
| `ask` | `DOUBLE` | Ask price |
| `price` | `DOUBLE` | Mid price — `(bid + ask) / 2` |

**Optional columns:**

| Column | Type | Description |
|---|---|---|
| `delta` | `DOUBLE` | Option delta |
| `gamma` | `DOUBLE` | Option gamma |
| `theta` | `DOUBLE` | Option theta |
| `vega` | `DOUBLE` | Option vega |
| `rho` | `DOUBLE` | Option rho |
| `implied_volatility` | `DOUBLE` | Implied volatility |
| `open_interest` | `BIGINT` | Open interest |
| `volume` | `BIGINT` | Daily volume |

> **Important:** Do not include any columns beyond those listed above. The framework constructs `Option` objects directly from query results using `Option(**row)`. Any extra columns will cause a `TypeError` at runtime.

---

## Configuration Reference

The framework is configured via a `settings.toml` file. By default it looks for this file in the directory where you run your backtest, or you can set the `OPTIONS_FRAMEWORK_CONFIG_FOLDER` environment variable to point to its location.

The settings file is read using Python's built-in tomllib library and is available throughout the framework as a plain dictionary. You can add your own custom keys and access them in your strategy code via the same settings dictionary. However, since there is one settings file per project, custom settings are best suited for parameters that apply consistently across your project — things like your data directory path or default fee settings. Strategy-specific parameters that vary between scripts are better defined directly in your script.

```toml
# settings.toml

data_frequency = "daily"        # "daily" or "intraday"
incur_fees = false              # whether to charge per-contract fees
standard_fee = 0.65             # fee per contract in dollars
fill_factor = 0                 # 0 = use bid/ask, 1 = use mid price
minute_granularity = 30         # minutes between intraday bars (intraday only)
start_time = "0930"             # market open time (intraday only)
end_time = "1600"               # market close time (intraday only)
options_directory = "path/to/data"  # root folder containing daily/ and intraday/ subfolders
exclude_shortdays = false       # exclude early market close days (day before holidays, etc.)
exclude_witching = false        # exclude quadruple witching days
exclude_fomc = false            # exclude Federal Reserve FOMC meeting days
exclude_ppi = false             # exclude Producer Price Index release days
exclude_cpi = false             # exclude Consumer Price Index release days
```

### Setting Details

**`data_frequency`** — Controls which subfolder the framework reads from. Set to `"daily"` for end-of-day data or `"intraday"` for tick/bar data.

**`fill_factor`** — Controls how fills are simulated. `0` is the conservative default: buys fill at the ask and sells fill at the bid. `1` uses the mid price for all fills, which assumes perfect execution and will overstate returns. Values between 0 and 1 interpolate between the two.

**`incur_fees`** — When `true`, the `standard_fee` amount is deducted per contract per open and close transaction and tracked in P&L.

**`minute_granularity`** — Only used when `data_frequency = "intraday"`. Set this to match the bar frequency in your data (e.g. `30` for 30-minute bars, `1` for 1-minute bars).

---

## Available Spread Types

The framework supports the following spread structures, all accessible from `options_framework`:

| Spread | Description |
|---|---|
| `Single` | A single long or short option leg |
| `Vertical` | Two legs at different strikes, same expiration — call or put debit/credit spreads |
| `Straddle` | Long or short call and put at the same strike and expiration |
| `Strangle` | Long or short call and put at different strikes, same expiration |
| `Butterfly` | Three-leg spread with equal wing widths — call or put |
| `IronButterfly` | Four-leg spread combining a straddle with a strangle |
| `Condor` | Four legs at four different strikes — call or put |
| `IronCondor` | Four legs combining two verticals of opposite types |
| `Calendar` | Two legs at the same strike, different expirations. Supports rolling the near-term leg. |
| `Diagonal` | Two legs at different strikes and different expirations. Supports rolling the near-term leg. |
| `Ratio` | Two legs with unequal quantities at different strikes |
| `Custom` | Arbitrary collection of legs with user-specified quantities |

All spreads are created through a `create()` classmethod that accepts an `OptionChain` and returns the spread object ready to be opened via `OptionPortfolio.open_position()`.

---

## Portfolio Usage

`OptionPortfolio` is the central object that manages your positions over the life of a backtest. It tracks open and closed positions, handles cash accounting, and advances time through your data.

### Core Workflow

```python
from options_framework import OptionPortfolio

# Create a portfolio with a starting cash balance
portfolio = OptionPortfolio(symbol="SPY", starting_cash=100_000)

# Each iteration of your backtest loop, advance time by passing the current datetime
portfolio.next(quote_datetime=current_datetime)

# Open a position by passing a spread and quantity
portfolio.open_position(spread=my_spread, quantity=1)

# Close a position by passing the spread object and an optional quantity
# Omitting quantity (or passing None) closes the entire position
portfolio.close_position(spread=my_spread)
portfolio.close_position(spread=my_spread, quantity=1)  # partial close
```

### Accessing Position State

```python
# All currently open positions
portfolio.open_positions

# All closed positions
portfolio.closed_positions

# Current cash balance (starting cash adjusted for all opens, closes, and fees)
portfolio.cash
```

### Event System

The framework uses an event-driven architecture built on [python-dispatch](https://github.com/nocarryr/python-dispatch). You can subscribe to events on both `Option` and `OptionPortfolio` to trigger strategy logic, logging, or reporting.

**`OptionPortfolio` events:**

| Event | When it fires |
|---|---|
| `next` | After each call to `portfolio.next()` |
| `position_closed` | When a position is fully closed |
| `position_expired` | When a position expires worthless or at intrinsic value |

**`Option` events:**

| Event | When it fires |
|---|---|
| `open_transaction_completed` | After a leg is opened or scaled into |
| `close_transaction_completed` | After a leg is fully or partially closed |
| `option_expired` | When an option reaches expiration |
| `fees_incurred` | When a fee is charged |

> **Note:** The event system stores callbacks as weak references. Always bind to named methods on objects that will remain in scope for the duration of your backtest. Lambdas will be silently garbage collected and never fire.

```python
# Correct — named method on a long-lived object
class MyStrategy:
    def on_position_closed(self, trade_close_info):
        print(f"Closed: {trade_close_info}")

strategy = MyStrategy()
portfolio.bind(position_closed=strategy.on_position_closed)
```

### Scaling Into and Out of Positions

Positions can be scaled incrementally. Call `open_trade()` multiple times on the same option to add contracts; call `close_trade()` with a specific quantity to reduce the position partially.

```python
# Scale in: open 2 contracts, then add 3 more later
option._open_trade(quantity=-2)
# ... time passes ...
option._open_trade(quantity=-3)  # now short 5 contracts

# Scale out: close 2 of the 5 contracts
option._close_trade(quote_datetime=current_datetime, quantity=2)
```

`trade_open_info` always reflects the weighted average price and total quantity across all open lots.

---

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request so the change can be discussed first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-change`)
3. Write tests for your change
4. Run the test suite (`pytest`)
5. Submit a pull request

---

## License

MIT License. See [LICENSE](LICENSE) for details.
