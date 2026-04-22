"""
DuckDB Options Query Helper
=============================
Lightweight query interface for per-ticker DuckDB option databases.
Designed for integration into an existing options testing framework.

Usage:
    from duckdb_options_query import OptionsDB, IntradayOptionsDB

    # Create from symbol (uses settings from config)
    db = OptionsDB.from_symbol("AAPL")
    db = IntradayOptionsDB.from_symbol("SPX")

    # Or create from explicit path
    db = OptionsDB("/path/to/options/daily/AAPL/data/options.duckdb")
    db = IntradayOptionsDB("/path/to/options/intraday/SPX/data")

    # Get all updates for a contract from a start datetime forward
    updates = db.get_contract_updates("AAPL20250620C00150000", start_dt="2025-03-15")

    # Get the full chain for a datetime
    chain = db.get_chain_at("2025-03-15")

    # Get expirations and strikes for a timeslot
    expirations = db.get_expirations_at("2025-03-15")
    exp_strikes = db.get_expiration_strikes_at("2025-03-15")

    # As context manager
    with OptionsDB.from_symbol("AAPL") as db:
        updates = db.get_contract_updates("AAPL20250620C00150000", start_dt="2025-03-15")

    with IntradayOptionsDB.from_symbol("SPX") as db:
        updates = db.get_contract_updates("SPX20250620C05000", start_dt="2025-03-15 09:30:00")
"""

import duckdb
from pathlib import Path
import datetime


class OptionsDB:
    """Query interface for a per-ticker DuckDB options database (daily)."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        self._con = duckdb.connect(str(self.db_path), read_only=True)

        # Open contract-ordered DB if available, otherwise fall back
        contract_path = self.db_path.parent / f"{self.db_path.stem}_by_contract.duckdb"
        if contract_path.exists():
            self._contract_con = duckdb.connect(str(contract_path), read_only=True)
        else:
            self._contract_con = self._con

    @classmethod
    def from_symbol(cls, symbol: str) -> "OptionsDB":
        from options_framework.config import settings
        db_path = Path(settings['options_directory']) / "daily" / symbol / f"{symbol}_options.duckdb"
        return cls(db_path)

    def close(self):
        if self._contract_con and self._contract_con is not self._con:
            self._contract_con.close()
        self._contract_con = None
        if self._con:
            self._con.close()
            self._con = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── Contract-level queries ──────────────────────────────────────────

    def get_contract_updates(self, option_id: str, start_dt: str = None) -> list[dict]:
        """
        Get all updates for a contract from start_dt forward, ordered by datetime.
        Data naturally ends at or before expiration.

        Args:
            option_id: The contract identifier (e.g., "AAPL20250620C00150000")
            start_dt: Starting datetime string. If None, returns all updates.
        """
        if start_dt:
            result = self._contract_con.execute(
                """
                SELECT * FROM options
                WHERE option_id = ?
                  AND quote_datetime >= ?
                ORDER BY quote_datetime
                """,
                [option_id, start_dt],
            )
        else:
            result = self._contract_con.execute(
                """
                SELECT * FROM options
                WHERE option_id = ?
                ORDER BY quote_datetime
                """,
                [option_id],
            )
        columns = [desc[0] for desc in result.description]
        results = result.fetchall()
        contract_dicts = [dict(zip(columns, row)) for row in results]
        contracts = {x['quote_datetime']: x for x in contract_dicts}
        return contracts

    def get_contract_updates_df(self, option_id: str, start_dt: str = None):
        """Same as get_contract_updates but returns a DataFrame."""
        if start_dt:
            return self._contract_con.execute(
                """
                SELECT * FROM options
                WHERE option_id = ?
                  AND quote_datetime >= ?
                ORDER BY quote_datetime
                """,
                [option_id, start_dt],
            ).fetchdf()
        else:
            return self._contract_con.execute(
                """
                SELECT * FROM options
                WHERE option_id = ?
                ORDER BY quote_datetime
                """,
                [option_id],
            ).fetchdf()

    def get_contract_at(self, option_id: str, dt: str) -> dict | None:
        """Get the exact update for a contract at a specific datetime."""
        result = self._contract_con.execute(
            """
            SELECT * FROM options
            WHERE option_id = ? AND quote_datetime = ?
            """,
            [option_id, dt],
        )
        columns = [desc[0] for desc in result.description]
        row = result.fetchone()
        return dict(zip(columns, row)) if row else None

    # ── Chain-level queries ─────────────────────────────────────────────
    def get_chain_at(self, dt: str) -> list[dict]:
        """Get the full option chain at a specific datetime."""
        result = self._con.execute(
            """
            SELECT * FROM options
            WHERE quote_datetime = ?
            ORDER BY expiration, option_type, strike
            """,
            [dt],
        )
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def get_chain_at_df(self, dt: str):
        """Same as get_chain_at but returns a DataFrame."""
        return self._con.execute(
            """
            SELECT * FROM options
            WHERE quote_datetime = ?
            ORDER BY expiration, option_type, strike
            """,
            [dt],
        ).fetchdf()

    def get_expirations_at(self, dt: str) -> list:
        """Get all unique expiration dates available at a given timeslot."""
        result = self._con.execute(
            """
            SELECT DISTINCT expiration FROM options
            WHERE quote_datetime = ?
            ORDER BY expiration
            """,
            [dt],
        )
        return [row[0] for row in result.fetchall()]

    def get_expiration_strikes_at(self, dt: str) -> dict:
        """
        Get strikes available per expiration at a given timeslot.
        Returns {expiration: [strike1, strike2, ...], ...}
        """
        result = self._con.execute(
            """
            SELECT DISTINCT expiration, strike FROM options
            WHERE quote_datetime = ?
            ORDER BY expiration, strike
            """,
            [dt],
        )
        exp_strikes = {}
        for exp, strike in result.fetchall():
            exp_strikes.setdefault(exp, []).append(strike)
        return exp_strikes

    # ── Discovery queries ───────────────────────────────────────────────

    def list_contracts(self) -> list[str]:
        """List all unique option IDs in the database."""
        result = self._con.execute(
            "SELECT DISTINCT option_id FROM options ORDER BY option_id"
        )
        return [row[0] for row in result.fetchall()]

    def list_expirations(self) -> list:
        """List all unique expiration dates."""
        result = self._con.execute(
            "SELECT DISTINCT expiration FROM options ORDER BY expiration"
        )
        return [row[0] for row in result.fetchall()]

    def list_datetimes(self) -> list:
        """List all unique quote datetimes (timeslots)."""
        result = self._con.execute(
            "SELECT DISTINCT quote_datetime FROM options ORDER BY quote_datetime"
        )
        return [row[0] for row in result.fetchall()]

    def contract_count(self) -> int:
        """Count of unique contracts."""
        return self._con.execute(
            "SELECT COUNT(DISTINCT option_id) FROM options"
        ).fetchone()[0]

    def row_count(self) -> int:
        """Total row count."""
        return self._con.execute("SELECT COUNT(*) FROM options").fetchone()[0]

    def schema(self) -> list[tuple[str, str]]:
        """Return the table schema as (column_name, type) tuples."""
        result = self._con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'options' ORDER BY ordinal_position"
        )
        return result.fetchall()


class IntradayOptionsDB:
    """
    Query interface for per-ticker intraday DuckDB databases (monthly files).

    Automatically opens the correct monthly file(s) based on the datetime
    parameters in each query. Uses contract-ordered files for contract
    lookups when available.

    File naming:
        <TICKER>_YYYY_MM_options.duckdb
        <TICKER>_YYYY_MM_by_contract.duckdb
    """

    def __init__(self, ticker_dir: str | Path):
        self.ticker_dir = Path(ticker_dir)
        if not self.ticker_dir.is_dir():
            raise FileNotFoundError(f"Directory not found: {self.ticker_dir}")
        self.ticker = self.ticker_dir.name
        self._connections: dict[str, duckdb.DuckDBPyConnection] = {}
        self._contract_connections: dict[str, duckdb.DuckDBPyConnection] = {}

    @classmethod
    def from_symbol(cls, symbol: str) -> "IntradayOptionsDB":
        from options_framework.config import settings
        ticker_dir = Path(settings['options_directory']) / "intraday" / symbol
        return cls(ticker_dir)

    def close(self):
        for con in self._contract_connections.values():
            con.close()
        self._contract_connections.clear()
        for con in self._connections.values():
            con.close()
        self._connections.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _db_path(self, year: int, month: int) -> Path:
        return self.ticker_dir / f"{self.ticker}_{year:04d}_{month:02d}_options.duckdb"

    def _contract_db_path(self, year: int, month: int) -> Path:
        return self.ticker_dir / f"{self.ticker}_{year:04d}_{month:02d}_by_contract.duckdb"

    def _get_connection(self, year: int, month: int):
        """Get or open a read-only connection for a monthly database."""
        key = f"{year:04d}_{month:02d}"
        if key not in self._connections:
            db_path = self._db_path(year, month)
            if not db_path.exists():
                return None
            self._connections[key] = duckdb.connect(str(db_path), read_only=True)
        return self._connections[key]

    def _get_contract_connection(self, year: int, month: int):
        """Get or open a contract-ordered connection, falling back to regular."""
        key = f"{year:04d}_{month:02d}"
        if key not in self._contract_connections:
            contract_path = self._contract_db_path(year, month)
            if contract_path.exists():
                self._contract_connections[key] = duckdb.connect(
                    str(contract_path), read_only=True
                )
            else:
                con = self._get_connection(year, month)
                if con is not None:
                    self._contract_connections[key] = con
                else:
                    return None
        return self._contract_connections[key]

    def _month_range(self, start_dt: str, end_dt: str = None) -> list[tuple[int, int]]:
        """
        Return list of (year, month) tuples covering the date range.
        If end_dt is None, returns all months from start_dt through the
        latest available database file.
        """
        from datetime import datetime as dt

        start = dt.fromisoformat(start_dt)
        months = []

        if end_dt:
            end = dt.fromisoformat(end_dt)
        else:
            available = self.list_months()
            if not available:
                return []
            end_key = available[-1]
            end = dt(end_key[0], end_key[1], 28)

        year, month = start.year, start.month
        while (year, month) <= (end.year, end.month):
            months.append((year, month))
            month += 1
            if month > 12:
                month = 1
                year += 1

        return months

    def list_months(self) -> list[tuple[int, int]]:
        """List all available (year, month) tuples based on existing DB files."""
        import re
        months = []
        pattern = f"{self.ticker}_*_*_options.duckdb"
        for f in sorted(self.ticker_dir.glob(pattern)):
            match = re.search(r"_(\d{4})_(\d{2})_options\.duckdb$", f.name)
            if match:
                months.append((int(match[1]), int(match[2])))
        return months

    # ── Contract-level queries (use contract-ordered DB) ────────────────

    def get_contract_updates(self, option_id: str, start_dt: str = None, end_dt: str = None) -> list[dict]:
        """
        Get all updates for a contract from start_dt forward.
        Queries across monthly files as needed using contract-ordered DBs.
        """
        if start_dt:
            months = self._month_range(start_dt, end_dt)
        else:
            months = self.list_months()

        all_rows = []
        columns = None

        for year, month in months:
            con = self._get_contract_connection(year, month)
            if con is None:
                continue

            if start_dt:
                result = con.execute(
                    """
                    SELECT * FROM options
                    WHERE option_id = ? AND quote_datetime >= ?
                    ORDER BY quote_datetime
                    """,
                    [option_id, start_dt],
                )
            else:
                result = con.execute(
                    """
                    SELECT * FROM options
                    WHERE option_id = ?
                    ORDER BY quote_datetime
                    """,
                    [option_id],
                )

            if columns is None:
                columns = [desc[0] for desc in result.description]

            rows = result.fetchall()
            all_rows.extend(rows)

        if not columns:
            return {}
        columns = [desc[0] for desc in result.description]

        contract_dicts = [dict(zip(columns, row)) for row in all_rows]
        contracts = {x['quote_datetime']: x for x in contract_dicts}
        return contracts
        #return [dict(zip(columns, row)) for row in all_rows]

    def get_contract_updates_df(self, option_id: str, start_dt: str = None):
        """Same as get_contract_updates but returns a DataFrame."""
        import pandas as pd

        updates = self.get_contract_updates(option_id, start_dt)
        if not updates:
            return pd.DataFrame()
        return pd.DataFrame(updates)

    def get_contract_at(self, option_id: str, dt: str) -> dict | None:
        """Get the exact update for a contract at a specific datetime."""
        from datetime import datetime as _dt

        parsed = _dt.fromisoformat(dt)
        con = self._get_contract_connection(parsed.year, parsed.month)
        if con is None:
            return None

        result = con.execute(
            """
            SELECT * FROM options
            WHERE option_id = ? AND quote_datetime = ?
            """,
            [option_id, dt],
        )
        columns = [desc[0] for desc in result.description]
        row = result.fetchone()
        return dict(zip(columns, row)) if row else None

    # ── Chain-level queries (use datetime-ordered DB) ───────────────────

    def get_chain_at(self, dt: str) -> list[dict]:
        """Get the full option chain at a specific datetime."""
        from datetime import datetime as _dt

        parsed = _dt.fromisoformat(dt)
        con = self._get_connection(parsed.year, parsed.month)
        if con is None:
            return []

        result = con.execute(
            """
            SELECT * FROM options
            WHERE quote_datetime = ?
            ORDER BY expiration, option_type, strike
            """,
            [dt],
        )
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def get_expirations_at(self, dt: str) -> list:
        """Get all unique expiration dates available at a given timeslot."""
        from datetime import datetime as _dt

        parsed = _dt.fromisoformat(dt)
        con = self._get_connection(parsed.year, parsed.month)
        if con is None:
            return []

        result = con.execute(
            """
            SELECT DISTINCT expiration FROM options
            WHERE quote_datetime = ?
            ORDER BY expiration
            """,
            [dt],
        )
        return [row[0] for row in result.fetchall()]

    def get_expiration_strikes_at(self, dt: str) -> dict:
        """
        Get strikes available per expiration at a given timeslot.
        Returns {expiration: [strike1, strike2, ...], ...}
        """
        from datetime import datetime as _dt

        parsed = _dt.fromisoformat(dt)
        con = self._get_connection(parsed.year, parsed.month)
        if con is None:
            return {}

        result = con.execute(
            """
            SELECT DISTINCT expiration, strike FROM options
            WHERE quote_datetime = ?
            ORDER BY expiration, strike
            """,
            [dt],
        )
        exp_strikes = {}
        for exp, strike in result.fetchall():
            exp_strikes.setdefault(exp, []).append(strike)
        return exp_strikes