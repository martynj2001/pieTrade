import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from fastapi import APIRouter

from ..db import get_conn

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/bot-status")
def bot_status():
    """Return the latest bot heartbeat and its freshness."""
    try:
        with closing(get_conn()) as connections:
            row = next(connections).execute("SELECT * FROM bot_status WHERE id = 1").fetchone()
    except sqlite3.OperationalError:
        return {"status": "unknown"}
    if row is None:
        return {"status": "unknown"}

    now = datetime.now(timezone.utc)
    age = max(0, (now - datetime.fromisoformat(row["updated_at"])).total_seconds())
    state = row["state"]
    status = "stopped" if state == "stopped" else "running" if age <= 45 else "delayed" if age <= 120 else "offline"
    uptime = None if state == "stopped" or not row["started_at"] else max(
        0, (now - datetime.fromisoformat(row["started_at"])).total_seconds()
    )
    return {
        "status": status, "state": state, "age_seconds": age, "uptime_seconds": uptime,
        "market": row["market"], "instrument": row["instrument"],
        "last_signal_check": row["last_signal_check"], "updated_at": row["updated_at"],
    }