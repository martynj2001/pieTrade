"""Persistent SQLite storage for pyTrade trades, signals, and events.

The database file is stored beside this module and created, with its tables,
the first time a database operation is performed. Existing data is preserved.

Example: save a trade after an OANDA market order is filled::

    import pyTrade_trades_db as trade_db

    trade_db.create_database()
    fill = order_response["orderFillTransaction"]
    opened_trade = fill["tradeOpened"]
    trade_db.insert_trade({
        "trade_id": opened_trade["tradeID"],
        "instrument": fill["instrument"],
        "direction": "BUY" if float(opened_trade["units"]) > 0 else "SELL",
        "strategy": "Breakout",
        "entry_time": fill["time"],
        "entry_price": float(fill["price"]),
        "stop_loss": float(order["order"]["stopLossOnFill"]["price"]),
        "take_profit": float(order["order"]["takeProfitOnFill"]["price"]),
        "units": int(opened_trade["units"]),
        "risk_amount": account_balance * 0.02,
        "status": "OPEN",
        "session": "new_york",
    })

When the trade closes, save its realized outcome::

    trade_db.update_trade_close(
        trade_id=opened_trade["tradeID"],
        exit_time=close_fill["time"],
        exit_price=float(close_fill["price"]),
        pnl_currency=float(close_fill["pl"]),
        close_reason="strategy invalidation",
    )
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Dict, Iterator, List, Mapping, Optional, Union


logger = logging.getLogger("pyTrade.TradesDB")

DatabasePath = Optional[Union[str, os.PathLike]]
RowData = Mapping[str, Any]

_DEFAULT_DB_PATH = "/home/martyn/pieTrade/Trades_db/pytrade.db"

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id TEXT UNIQUE,
        instrument TEXT,
        direction TEXT,
        strategy TEXT,
        entry_time DATETIME,
        exit_time DATETIME,
        entry_price REAL,
        exit_price REAL,
        stop_loss REAL,
        take_profit REAL,
        units INTEGER,
        risk_amount REAL,
        status TEXT,
        close_reason TEXT,
        pnl_currency REAL,
        pnl_pips REAL,
        duration_minutes INTEGER,
        session TEXT,
        created_at DATETIME
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trade_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id TEXT,
        ema20 REAL,
        ema50 REAL,
        atr14 REAL,
        adx REAL,
        trend_strength REAL,
        rejection_candle BOOLEAN,
        pullback_detected BOOLEAN,
        close_price REAL,
        high_price REAL,
        low_price REAL,
        signal_timestamp DATETIME
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trade_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id TEXT,
        event_time DATETIME,
        event_type TEXT,
        message TEXT
    )
    """,
)


def _resolve_db_path(db_path: DatabasePath) -> str:
    """Return the absolute path, defaulting to this module's folder."""
    path = os.fspath(db_path) if db_path is not None else _DEFAULT_DB_PATH
    return os.path.abspath(path)


def _normalize_values(data: RowData) -> Dict[str, Any]:
    """Convert common Python values to SQLite-compatible scalar values."""
    values: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, (datetime, date)):
            values[key] = value.isoformat()
        elif isinstance(value, bool):
            values[key] = int(value)
        else:
            values[key] = value
    return values


@contextmanager
def _connection(db_path: DatabasePath = None) -> Iterator[sqlite3.Connection]:
    """Open a connection, ensure the schema exists, and always close it."""
    path = _resolve_db_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        for statement in _SCHEMA:
            connection.execute(statement)
        signal_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(trade_signals)"
            ).fetchall()
        }
        if "adx" not in signal_columns:
            connection.execute("ALTER TABLE trade_signals ADD COLUMN adx REAL")
        yield connection
        connection.commit()
    except Exception as exc:
        connection.rollback()
        if isinstance(exc, sqlite3.Error):
            logger.exception("SQLite operation failed for %s", path)
        raise
    finally:
        connection.close()


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Convert a SQLite row to a dictionary."""
    return dict(row) if row is not None else None


def _quote_identifier(identifier: str) -> str:
    """Quote a SQLite identifier after confirming it exists in the schema."""
    return '"' + identifier.replace('"', '""') + '"'


def create_database(db_path: DatabasePath = None) -> str:
    """Create the local database and required tables if they do not exist.

    Calling this function repeatedly is safe and does not recreate or clear
    existing tables or data.

    Args:
        db_path: Optional database file path. Defaults to ``pytrade.db`` beside
            this module.

    Returns:
        The absolute path to the database file.
    """
    path = _resolve_db_path(db_path)
    with _connection(path):
        pass
    logger.info("Trade database ready: %s", path)
    return path


def insert_row(
    table_name: str,
    data: RowData,
    db_path: DatabasePath = None,
) -> int:
    """Insert a row into an existing database table and return its row ID.

    This generic helper supports adding rows to these tables and to additional
    tables created by future strategy/database extensions. Table and column
    names are checked against the database schema; values are parameterized.

    Args:
        table_name: Existing table name.
        data: Column-name/value mapping for the new row.
        db_path: Optional database file path.

    Raises:
        ValueError: If the table does not exist, data is empty, or a column
            does not exist in the selected table.
        sqlite3.Error: If the database operation fails.
    """
    if not data:
        raise ValueError("Cannot insert an empty row")

    values = _normalize_values(data)
    with _connection(db_path) as connection:
        table = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = ? AND name NOT LIKE 'sqlite_%'
            """,
            (table_name,),
        ).fetchone()
        if table is None:
            raise ValueError(f"Table does not exist: {table_name}")

        quoted_table = _quote_identifier(table_name)
        columns = {
            row["name"]
            for row in connection.execute(
                f"PRAGMA table_info({quoted_table})"
            ).fetchall()
        }
        unknown_columns = set(values) - columns
        if unknown_columns:
            raise ValueError(
                f"Unknown column(s) for {table_name}: "
                f"{', '.join(sorted(unknown_columns))}"
            )

        column_names = ", ".join(
            _quote_identifier(column) for column in values
        )
        placeholders = ", ".join("?" for _ in values)
        query = (
            f"INSERT INTO {quoted_table} ({column_names}) "
            f"VALUES ({placeholders})"
        )
        cursor = connection.execute(query, tuple(values.values()))
        logger.debug(
            "Inserted row into %s with row ID %s",
            table_name,
            cursor.lastrowid,
        )
        return int(cursor.lastrowid)


def insert_trade(trade_data: RowData, db_path: DatabasePath = None) -> int:
    """Insert a newly opened trade and return its database row ID.

    ``trade_data`` keys should match the ``trades`` table columns. ``trade_id``
    should be the OANDA trade ID. If omitted, ``created_at`` is set to the
    current local time and ``status`` defaults to ``"OPEN"``.
    """
    values = dict(trade_data)
    values.setdefault("created_at", datetime.now().astimezone())
    values.setdefault("status", "OPEN")
    if not values.get("trade_id"):
        raise ValueError("trade_data must include a non-empty trade_id")
    return insert_row("trades", values, db_path)


def update_trade_close(
    trade_id: str,
    exit_time: Union[str, datetime],
    exit_price: float,
    pnl_currency: float,
    pnl_pips: Optional[float] = None,
    close_reason: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    db_path: DatabasePath = None,
) -> bool:
    """Record close details for a trade.

    If ``duration_minutes`` is omitted, it is calculated from the stored entry
    time when that value is an ISO-formatted datetime.

    Returns:
        ``True`` if a trade was updated, otherwise ``False``.
    """
    close_time = (
        exit_time.isoformat()
        if isinstance(exit_time, datetime)
        else exit_time
    )
    with _connection(db_path) as connection:
        row = connection.execute(
            "SELECT entry_time FROM trades WHERE trade_id = ?",
            (trade_id,),
        ).fetchone()
        if row is None:
            logger.warning("Cannot close unknown trade ID %s", trade_id)
            return False

        if duration_minutes is None and row["entry_time"] and close_time:
            try:
                entry = datetime.fromisoformat(row["entry_time"])
                exit_at = datetime.fromisoformat(close_time)
                duration_minutes = max(
                    0, int((exit_at - entry).total_seconds() // 60)
                )
            except (TypeError, ValueError):
                logger.warning(
                    "Could not calculate duration for trade %s "
                    "from its timestamps",
                    trade_id,
                )

        cursor = connection.execute(
            """
            UPDATE trades
            SET exit_time = ?,
                exit_price = ?,
                pnl_currency = ?,
                pnl_pips = ?,
                duration_minutes = ?,
                close_reason = ?,
                status = 'CLOSED'
            WHERE trade_id = ?
            """,
            (
                close_time,
                exit_price,
                pnl_currency,
                pnl_pips,
                duration_minutes,
                close_reason,
                trade_id,
            ),
        )
        updated = cursor.rowcount > 0
        logger.info("Updated close details for trade %s", trade_id)
        return updated


def update_trade_status(
    trade_id: str,
    status: str,
    close_reason: Optional[str] = None,
    db_path: DatabasePath = None,
) -> bool:
    """Update a trade's status and optionally its close reason.

    Returns ``True`` if a trade was updated, otherwise ``False``.
    """
    with _connection(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE trades
            SET status = ?, close_reason = COALESCE(?, close_reason)
            WHERE trade_id = ?
            """,
            (status, close_reason, trade_id),
        )
        if cursor.rowcount == 0:
            logger.warning(
                "Cannot update status for unknown trade ID %s",
                trade_id,
            )
            return False
        logger.info("Updated trade %s status to %s", trade_id, status)
        return True


def insert_signal_data(
    signal_data: RowData,
    db_path: DatabasePath = None,
) -> int:
    """Insert signal/indicator values associated with a trade."""
    return insert_row("trade_signals", signal_data, db_path)


def insert_trade_event(
    trade_id: str,
    event_type: str,
    message: str,
    event_time: Optional[Union[str, datetime]] = None,
    db_path: DatabasePath = None,
) -> int:
    """Insert a timestamped event for a trade and return its row ID."""
    timestamp = event_time or datetime.now().astimezone()
    return insert_row(
        "trade_events",
        {
            "trade_id": trade_id,
            "event_time": timestamp,
            "event_type": event_type,
            "message": message,
        },
        db_path,
    )


def get_open_trades(db_path: DatabasePath = None) -> List[Dict[str, Any]]:
    """Return all trades whose status is ``OPEN``."""
    with _connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM trades WHERE UPPER(status) = 'OPEN' ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def get_closed_trades(db_path: DatabasePath = None) -> List[Dict[str, Any]]:
    """Return all trades whose status is ``CLOSED``."""
    with _connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM trades WHERE UPPER(status) = 'CLOSED' ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def get_trade_by_id(
    trade_id: str,
    db_path: DatabasePath = None,
) -> Optional[Dict[str, Any]]:
    """Return a trade by its OANDA trade ID, or ``None`` if not found."""
    with _connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM trades WHERE trade_id = ?",
            (trade_id,),
        ).fetchone()
        return _row_to_dict(row)


def calculate_win_rate(db_path: DatabasePath = None) -> float:
    """Return the closed-trade win rate as a percentage from 0 to 100."""
    with _connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN pnl_currency > 0 THEN 1 ELSE 0 END) AS wins
            FROM trades
            WHERE UPPER(status) = 'CLOSED'
            """
        ).fetchone()
        if not row["total"]:
            return 0.0
        return float(row["wins"] or 0) / row["total"] * 100.0


def calculate_average_rr(db_path: DatabasePath = None) -> Optional[float]:
    """Return mean realized R-multiple (P&L divided by risk amount).

    Closed trades without a positive ``risk_amount`` are excluded. Returns
    ``None`` if there are no closed trades with a usable risk amount.
    """
    with _connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT AVG(pnl_currency / risk_amount) AS average_rr
            FROM trades
            WHERE UPPER(status) = 'CLOSED'
              AND risk_amount > 0
              AND pnl_currency IS NOT NULL
            """
        ).fetchone()
        if row["average_rr"] is not None:
            return float(row["average_rr"])
        return None


def calculate_total_pnl(db_path: DatabasePath = None) -> float:
    """Return the sum of realized P&L in account currency for closed trades."""
    with _connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(pnl_currency), 0.0) AS total_pnl
            FROM trades
            WHERE UPPER(status) = 'CLOSED'
            """
        ).fetchone()
        return float(row["total_pnl"])


def calculate_profit_factor(db_path: DatabasePath = None) -> Optional[float]:
    """Return gross profits divided by absolute gross losses for closed trades.

    Returns ``None`` when there are no closed trades or no losing trades
    (profit factor is undefined when its denominator is zero).
    """
    with _connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT
                SUM(CASE WHEN pnl_currency > 0 THEN pnl_currency ELSE 0 END)
                    AS gross_profit,
                SUM(CASE WHEN pnl_currency < 0 THEN -pnl_currency ELSE 0 END)
                    AS gross_loss,
                COUNT(*) AS total
            FROM trades
            WHERE UPPER(status) = 'CLOSED'
            """
        ).fetchone()
        if not row["total"] or not row["gross_loss"]:
            return None
        return float(row["gross_profit"] / row["gross_loss"])
