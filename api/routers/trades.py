import sqlite3
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import get_conn
from ..filters import TradeFilters, trade_filters

router = APIRouter(prefix="/api", tags=["trades"])

SORTABLE = {
    "id", "trade_id", "instrument", "direction", "strategy", "entry_time", "exit_time",
    "entry_price", "exit_price", "units", "status", "pnl_currency", "pnl_pips",
    "duration_minutes", "session",
}


@router.get("/health")
def health(conn: sqlite3.Connection = Depends(get_conn)):
    conn.execute("SELECT 1 FROM trades LIMIT 1")
    return {"status": "ok"}


@router.get("/trades")
def list_trades(
    f: TradeFilters = Depends(trade_filters),
    sort: str = "entry_time",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_conn),
):
    if sort not in SORTABLE:
        raise HTTPException(400, f"sort must be one of {sorted(SORTABLE)}")
    where, params = f.where("t")
    total = conn.execute(f"SELECT COUNT(*) FROM trades t{where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM trades t{where} ORDER BY t.{sort} {order}, t.id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return {"total": total, "limit": limit, "offset": offset, "items": [dict(r) for r in rows]}


@router.get("/trades/{trade_id}")
def get_trade(trade_id: str, conn: sqlite3.Connection = Depends(get_conn)):
    trade = conn.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,)).fetchone()
    if not trade:
        raise HTTPException(404, "Trade not found")
    signals = conn.execute(
        "SELECT * FROM trade_signals WHERE trade_id = ? ORDER BY signal_timestamp, id", (trade_id,)
    ).fetchall()
    events = conn.execute(
        "SELECT * FROM trade_events WHERE trade_id = ? ORDER BY event_time, id", (trade_id,)
    ).fetchall()
    return {"trade": dict(trade), "signals": [dict(s) for s in signals],
            "events": [dict(e) for e in events]}


@router.get("/meta")
def meta(conn: sqlite3.Connection = Depends(get_conn)):
    def distinct(col):
        return [r[0] for r in conn.execute(
            f"SELECT DISTINCT {col} FROM trades WHERE {col} IS NOT NULL ORDER BY {col}")]
    return {c: distinct(c) for c in ("instrument", "strategy", "status", "direction", "session")}
