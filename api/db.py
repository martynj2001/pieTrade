import os
import sqlite3
from pathlib import Path
from typing import Iterator

DEFAULT_DB = Path(__file__).resolve().parent.parent / "Trades_db" / "pytrade.db"


def db_path() -> Path:
    return Path(os.environ.get("PYTRADE_DB", DEFAULT_DB))


def get_conn() -> Iterator[sqlite3.Connection]:
    """Per-request read-only connection."""
    conn = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
