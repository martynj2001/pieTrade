import sqlite3
from typing import Any

PRICE_IN_PER_M = 0.10
PRICE_OUT_PER_M = 0.50
MIN_HOURS = 150
MIN_OK_PCT = 95
MIN_BEAT_FIXED_PCT = 55
MIN_SESSION_HOURS = 20
USD_TO_GBP = 0.76  # update manually

_UNAVAILABLE_MESSAGE = (
    "AI-agent analysis data is not available. Run the bot with the AI agent toggle ON, "
    "and run pyTrade_agent_outcomes.py."
)
_REQUIRED_OBJECTS = ("agent_decisions", "agent_outcomes", "v_agent_eval", "trades")
_DECISION_COLUMNS = (
    "id, target_hour, mode, status, market, instrument, fixed_instrument, "
    "baseline_instrument, reason, latency_s, error"
)


def _validate_filters(mode: str, days: int | None) -> None:
    if mode not in {"all", "shadow", "live"}:
        raise ValueError("mode must be all, shadow, or live")
    if days is not None and days < 1:
        raise ValueError("days must be at least 1")


def _where(mode: str, days: int | None, alias: str) -> tuple[str, list[Any]]:
    clauses = []
    params: list[Any] = []
    if mode != "all":
        clauses.append(f"{alias}mode = ?")
        params.append(mode)
    if days is not None:
        clauses.append(
            f"{alias}target_hour >= strftime('%Y-%m-%dT%H:%M:%S', 'now', ?)"
        )
        params.append(f"-{days} days")
    return (" WHERE " + " AND ".join(clauses) if clauses else "", params)


def _fetch_dicts(
    conn: sqlite3.Connection, query: str, params: tuple[Any, ...] | list[Any] = ()
) -> list[dict[str, Any]]:
    cursor = conn.execute(query, params)
    columns = [description[0] for description in cursor.description or ()]
    return [
        dict(row) if isinstance(row, sqlite3.Row) else dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def _average(rows: list[dict[str, Any]], column: str, digits: int) -> float | None:
    value = _mean(rows, column)
    return round(value, digits) if value is not None else None


def _mean(rows: list[dict[str, Any]], column: str) -> float | None:
    values = [float(row[column]) for row in rows if row[column] is not None]
    return sum(values) / len(values) if values else None


def _percent(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 1) if denominator else None


def _comparison(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [
        row for row in rows
        if row["agent_eff"] is not None
        and row["fixed_eff"] is not None
        and row["base_eff"] is not None
    ]
    ranges = [
        row for row in eligible
        if row["agent_range_atr"] is not None
        and row["fixed_range_atr"] is not None
        and row["base_range_atr"] is not None
    ]
    count = len(eligible)
    range_count = len(ranges)
    return {
        "n": count,
        "agent_eff": _average(eligible, "agent_eff", 3),
        "fixed_eff": _average(eligible, "fixed_eff", 3),
        "base_eff": _average(eligible, "base_eff", 3),
        "any_eff": _average(eligible, "avg_eff", 3),
        "agent_range_atr": _average(ranges, "agent_range_atr", 2),
        "fixed_range_atr": _average(ranges, "fixed_range_atr", 2),
        "base_range_atr": _average(ranges, "base_range_atr", 2),
        "any_range_atr": _average(ranges, "avg_range_atr", 2),
        "pct_beats_fixed_eff": _percent(
            sum(row["agent_eff"] > row["fixed_eff"] for row in eligible), count
        ),
        "pct_beats_base_eff": _percent(
            sum(row["agent_eff"] > row["base_eff"] for row in eligible), count
        ),
        "pct_beats_fixed_range": _percent(
            sum(row["agent_range_atr"] > row["fixed_range_atr"] for row in ranges),
            range_count,
        ),
        "pct_beats_base_range": _percent(
            sum(row["agent_range_atr"] > row["base_range_atr"] for row in ranges),
            range_count,
        ),
    }


def _unavailable(message: str = _UNAVAILABLE_MESSAGE) -> dict[str, Any]:
    return {"available": False, "message": message}


def _go_live(
    comparison: dict[str, Any],
    eval_rows: list[dict[str, Any]],
    ok_pct: float | None,
    raw_ok_pct: float | None,
):
    eligible = [
        row for row in eval_rows
        if row["agent_eff"] is not None
        and row["fixed_eff"] is not None
        and row["base_eff"] is not None
    ]
    eligible_markets = sorted({row["market"] for row in eligible if row["market"] is not None})
    qualifying_markets = []
    for market in eligible_markets:
        rows = [row for row in eligible if row["market"] == market]
        if len(rows) >= MIN_SESSION_HOURS:
            qualifying_markets.append(rows)
    beating_markets = [
        rows for rows in qualifying_markets
        if _mean(rows, "agent_eff") > _mean(rows, "fixed_eff")
    ]
    enough_markets = len(qualifying_markets) >= 2
    market_value = (
        f"{len(beating_markets)} of {len(qualifying_markets)} qualifying markets beat fixed"
        if enough_markets else "not enough data"
    )
    agent_average = _mean(eligible, "agent_eff")
    fixed_average = _mean(eligible, "fixed_eff")
    baseline_average = _mean(eligible, "base_eff")
    raw_beats_fixed_pct = (
        100 * sum(row["agent_eff"] > row["fixed_eff"] for row in eligible) / len(eligible)
        if eligible else None
    )
    checks = [
        {
            "name": "Usable hours",
            "passed": comparison["n"] >= MIN_HOURS,
            "value": f"{comparison['n']} hours",
            "target": f"at least {MIN_HOURS} hours",
        },
        {
            "name": "Successful decisions",
            "passed": raw_ok_pct is not None and raw_ok_pct >= MIN_OK_PCT,
            "value": "not enough data" if ok_pct is None else f"{ok_pct:.1f}%",
            "target": f"at least {MIN_OK_PCT}%",
        },
        {
            "name": "Average efficiency",
            "passed": (
                agent_average is not None
                and fixed_average is not None
                and baseline_average is not None
                and agent_average > fixed_average
                and agent_average > baseline_average
            ),
            "value": (
                "not enough data"
                if agent_average is None or fixed_average is None or baseline_average is None
                else f"agent {comparison['agent_eff']:.3f}; fixed {comparison['fixed_eff']:.3f}; baseline {comparison['base_eff']:.3f}"
            ),
            "target": "agent above fixed and baseline",
        },
        {
            "name": "Hours beating fixed",
            "passed": (
                raw_beats_fixed_pct is not None
                and raw_beats_fixed_pct >= MIN_BEAT_FIXED_PCT
            ),
            "value": (
                "not enough data"
                if comparison["pct_beats_fixed_eff"] is None
                else f"{comparison['pct_beats_fixed_eff']:.1f}%"
            ),
            "target": f"at least {MIN_BEAT_FIXED_PCT}%",
        },
        {
            "name": "Markets beating fixed",
            "passed": enough_markets and len(beating_markets) >= 2,
            "value": market_value,
            "target": f"at least 2 markets with {MIN_SESSION_HOURS}+ hours",
        },
    ]
    return {"ready": all(check["passed"] for check in checks), "checks": checks}


def build_report(conn: sqlite3.Connection, mode: str = "all", days: int | None = None) -> dict[str, Any]:
    """Build read-only AI-agent reliability and outcome analysis."""
    _validate_filters(mode, days)
    try:
        for name in _REQUIRED_OBJECTS:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
                (name,),
            ).fetchone()
            if exists is None:
                return _unavailable()

        decision_count = conn.execute("SELECT COUNT(*) FROM agent_decisions").fetchone()[0]
        if decision_count == 0:
            return _unavailable("No AI-agent decisions have been recorded. " + _UNAVAILABLE_MESSAGE)

        decision_where, decision_params = _where(mode, days, "d.")
        decision_rows = _fetch_dicts(
            conn,
            "SELECT d.status, d.latency_s FROM agent_decisions d" + decision_where,
            decision_params,
        )
        total = len(decision_rows)
        ok_count = sum(row["status"] == "ok" for row in decision_rows)
        ok_pct = _percent(ok_count, total)
        status_counts = _fetch_dicts(
            conn,
            "SELECT d.status, COUNT(*) AS count FROM agent_decisions d"
            + decision_where
            + " GROUP BY d.status ORDER BY d.status",
            decision_params,
        )
        reliability = {
            "total": total,
            "ok_pct": ok_pct,
            "avg_latency_s": _average(decision_rows, "latency_s", 2),
            "by_status": status_counts,
        }

        eval_where, eval_params = _where(mode, days, "v.")
        eval_rows = _fetch_dicts(conn, "SELECT * FROM v_agent_eval v" + eval_where, eval_params)
        agreements = [
            row for row in eval_rows
            if row["agent_pair"] is not None
            and row["fixed_instrument"] is not None
            and row["baseline_instrument"] is not None
        ]
        agreement_count = len(agreements)
        agreement = {
            "n": agreement_count,
            "pct_same_as_fixed": _percent(
                sum(row["agent_pair"] == row["fixed_instrument"] for row in agreements),
                agreement_count,
            ),
            "pct_same_as_baseline": _percent(
                sum(row["agent_pair"] == row["baseline_instrument"] for row in agreements),
                agreement_count,
            ),
        }

        comparison = _comparison(eval_rows)
        disagreements = _comparison([
            row for row in eval_rows
            if row["agent_pair"] is not None
            and row["fixed_instrument"] is not None
            and row["agent_pair"] != row["fixed_instrument"]
        ])
        markets = sorted({row["market"] for row in eval_rows if row["market"] is not None})
        by_market = []
        for market in markets:
            by_market.append({
                "market": market,
                **_comparison([row for row in eval_rows if row["market"] == market]),
            })

        news_row = conn.execute(
            "SELECT COUNT(CASE WHEN excluded_news NOT IN ('', '[]') THEN 1 END) AS decisions_with_news_exclusion, "
            "COALESCE(SUM(input_tokens), 0) AS input_tokens, "
            "COALESCE(SUM(output_tokens), 0) AS output_tokens "
            "FROM agent_decisions d" + decision_where,
            decision_params,
        ).fetchone()
        input_tokens = int(news_row["input_tokens"] if isinstance(news_row, sqlite3.Row) else news_row[1])
        output_tokens = int(news_row["output_tokens"] if isinstance(news_row, sqlite3.Row) else news_row[2])
        exclusion_count = int(
            news_row["decisions_with_news_exclusion"]
            if isinstance(news_row, sqlite3.Row) else news_row[0]
        )
        news_cost = {
            "decisions_with_news_exclusion": exclusion_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "est_cost_usd": round(
                input_tokens * PRICE_IN_PER_M / 1_000_000
                + output_tokens * PRICE_OUT_PER_M / 1_000_000,
                6,
            ),
        }
        news_cost["est_cost_gbp"] = round(news_cost["est_cost_usd"] * USD_TO_GBP, 6)

        decision_day_clause = ""
        live_params: list[Any] = [mode, mode]
        if days is not None:
            decision_day_clause = (
                " AND d.target_hour >= strftime('%Y-%m-%dT%H:%M:%S', 'now', ?)"
            )
            live_params.append(f"-{days} days")
        live_pnl = _fetch_dicts(
            conn,
            "WITH live_decisions AS ("
            "SELECT DISTINCT market, instrument, substr(target_hour, 1, 13) AS target_hour "
            "FROM agent_decisions d WHERE d.mode = 'live' AND d.status = 'ok'"
            + decision_day_clause
            + "), matched AS ("
            "SELECT DISTINCT d.market, t.trade_id, t.pnl_currency "
            "FROM live_decisions d JOIN trades t ON t.instrument = d.instrument "
            "AND substr(t.entry_time, 1, 13) = d.target_hour WHERE t.status = 'CLOSED'"
            ") SELECT market, COUNT(*) AS trades, ROUND(SUM(pnl_currency), 2) AS pnl, "
            "ROUND(100.0 * SUM(CASE WHEN pnl_currency > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct "
            "FROM matched WHERE (? = 'all' OR ? = 'live') GROUP BY market ORDER BY market",
            [live_params[-1]] + live_params[:-1] if days is not None else live_params,
        )

        raw_ok_pct = 100 * ok_count / total if total else None
        return {
            "available": True,
            "message": None,
            "filters": {"mode": mode, "days": days},
            "reliability": reliability,
            "agreement": agreement,
            "comparison": comparison,
            "disagreements": disagreements,
            "by_market": by_market,
            "news_cost": news_cost,
            "live_pnl": live_pnl,
            "go_live": _go_live(comparison, eval_rows, ok_pct, raw_ok_pct),
        }
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower() or "no such view" in str(exc).lower():
            return _unavailable()
        raise


def recent_decisions(
    conn: sqlite3.Connection,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    mode: str = "all",
    days: int | None = None,
) -> dict[str, Any]:
    """Return a page of recent decisions using the same mode and date filters."""
    _validate_filters(mode, days)
    if limit < 1 or offset < 0:
        raise ValueError("limit must be at least 1 and offset cannot be negative")
    where, params = _where(mode, days, "d.")
    if status is not None:
        where += (" AND" if where else " WHERE") + " d.status = ?"
        params.append(status)
    total = conn.execute(
        "SELECT COUNT(*) FROM agent_decisions d" + where, params
    ).fetchone()[0]
    items = _fetch_dicts(
        conn,
        f"SELECT {_DECISION_COLUMNS} FROM agent_decisions d{where} "
        "ORDER BY d.target_hour DESC, d.id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    return {"total": total, "limit": limit, "offset": offset, "items": items}