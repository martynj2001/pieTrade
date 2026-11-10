import sqlite3
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import agent_analysis
from ..db import get_conn

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/report")
def report(
    mode: Literal["all", "shadow", "live"] = "all",
    days: Optional[int] = Query(None, ge=1, le=365),
    conn: sqlite3.Connection = Depends(get_conn),
):
    return agent_analysis.build_report(conn, mode=mode, days=days)


@router.get("/decisions")
def decisions(
    mode: Literal["all", "shadow", "live"] = "all",
    days: Optional[int] = Query(None, ge=1, le=365),
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_conn),
):
    return agent_analysis.recent_decisions(
        conn, mode=mode, days=days, status=status, limit=limit, offset=offset
    )


@router.get("/outcomes-readme")
def outcomes_readme():
    path = Path(__file__).resolve().parents[2] / "AI_Outcomes_README.md"
    try:
        return {"markdown": path.read_text(encoding="utf-8")}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Outcomes guide not found") from exc