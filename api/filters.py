from dataclasses import dataclass
from typing import Optional

from fastapi import Query


@dataclass
class TradeFilters:
    instrument: Optional[str] = None
    strategy: Optional[str] = None
    status: Optional[str] = None
    direction: Optional[str] = None
    session: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    def where(self, alias: str = "t") -> tuple[str, list]:
        clauses, params = [], []
        for col in ("instrument", "strategy", "status", "direction", "session"):
            val = getattr(self, col)
            if val:
                clauses.append(f"UPPER({alias}.{col}) = UPPER(?)")
                params.append(val)
        if self.date_from:
            clauses.append(f"{alias}.entry_time >= ?")
            params.append(self.date_from)
        if self.date_to:
            clauses.append(f"{alias}.entry_time <= ?")
            params.append(self.date_to)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def trade_filters(
    instrument: Optional[str] = None,
    strategy: Optional[str] = None,
    status: Optional[str] = None,
    direction: Optional[str] = Query(None, description="BUY or SELL"),
    session: Optional[str] = None,
    date_from: Optional[str] = Query(None, description="ISO date/time, entry_time >="),
    date_to: Optional[str] = Query(None, description="ISO date/time, entry_time <="),
) -> TradeFilters:
    return TradeFilters(instrument, strategy, status, direction, session, date_from, date_to)
