import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query

from .. import analytics as an
from ..db import get_conn
from ..filters import TradeFilters, trade_filters

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def closed_trades(conn: sqlite3.Connection, f: TradeFilters) -> list[dict]:
    """Closed trades matching filters, each with the latest signal's atr14."""
    f.status = None
    where, params = f.where("t")
    where += (" AND" if where else " WHERE") + " t.status = 'CLOSED'"
    rows = conn.execute(
        f"""SELECT t.*, s.atr14 AS atr14 FROM trades t
            LEFT JOIN trade_signals s ON s.id = (
                SELECT MAX(id) FROM trade_signals WHERE trade_id = t.trade_id)
            {where}""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


Trades = Depends(lambda conn=Depends(get_conn), f=Depends(trade_filters): closed_trades(conn, f))


@router.get("/summary")
def summary(trades=Trades):
    return an.overall(trades)


@router.get("/by-instrument")
def by_instrument(trades=Trades):
    return an.group_by(trades, "instrument")


@router.get("/by-session")
def by_session(trades=Trades):
    return an.group_by(trades, "session")


@router.get("/by-direction")
def by_direction(trades=Trades):
    return an.group_by(trades, "direction")


@router.get("/holding-time")
def holding_time(group_by: Optional[str] = Query(None, pattern="^(instrument|session|direction)$"),
                 trades=Trades):
    return an.holding_time(trades, group_by)


@router.get("/atr-ranges")
def atr_ranges(buckets: int = Query(4, ge=1, le=20), trades=Trades):
    return an.atr_ranges(trades, buckets)


@router.get("/exit-reasons")
def exit_reasons(trades=Trades):
    return an.exit_reasons(trades)


@router.get("/drawdown")
def drawdown(starting_balance: Optional[float] = Query(None, gt=0), trades=Trades):
    return an.drawdown(trades, starting_balance)
