"""Report closed-trade performance by strategy and entry signal."""

import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _percentage(rows: list[sqlite3.Row]) -> str:
    """Return the win rate for trades with known P&L."""
    outcomes = [row["pnl_currency"] for row in rows if row["pnl_currency"] is not None]
    if not outcomes:
        return "- (n=0)"
    return f"{100 * sum(value > 0 for value in outcomes) / len(outcomes):.1f}% (n={len(outcomes)})"


def _average(values: list[float]) -> str:
    """Format an average, or a dash when no values are available."""
    return f"{sum(values) / len(values):.2f} (n={len(values)})" if values else "- (n=0)"


def _multiples(rows: list[sqlite3.Row]) -> list[float]:
    """Return R values where P&L and positive risk are available."""
    return [row["pnl_currency"] / row["risk_amount"] for row in rows
            if row["pnl_currency"] is not None and row["risk_amount"] is not None
            and row["risk_amount"] > 0]


def _print_report(conn: sqlite3.Connection) -> None:
    """Print per-strategy results using the latest signal for each trade."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(trades)")}
    reason_column = next((name for name in ("close_reason", "exit_reason") if name in columns), None)
    reason_select = f"t.{reason_column}" if reason_column else "NULL"
    rows = conn.execute(
        f"""SELECT t.strategy, t.pnl_currency, t.risk_amount, t.duration_minutes,
                  strftime('%H', t.entry_time) AS entry_hour, s.adx, s.trend_strength,
                  {reason_select} AS close_reason
           FROM trades AS t
           LEFT JOIN trade_signals AS s ON s.id = (
               SELECT MAX(id) FROM trade_signals WHERE trade_id = t.trade_id
           )
           WHERE UPPER(t.status) = 'CLOSED'
           ORDER BY t.strategy, t.id"""
    ).fetchall()
    strategies: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        strategies[row["strategy"] or "Unknown"].append(row)

    if not strategies:
        print("No closed trades found.")
        return

    for strategy, trades in strategies.items():
        print(f"\n{strategy}\n{'-' * len(strategy)}")
        print(f"Closed trades: {len(trades)}")
        print(f"Win rate: {_percentage(trades)}")
        multiples = _multiples(trades)
        print(f"Average R: {_average(multiples)}")
        print(f"Average R (wins): {_average([value for value in multiples if value > 0])}")
        print(f"Average R (losses): {_average([value for value in multiples if value < 0])}")
        print(f"Total R: {sum(multiples):.2f} (n={len(multiples)})" if multiples else "Total R: - (n=0)")
        outcomes = [row["pnl_currency"] for row in trades if row["pnl_currency"] is not None]
        gross_profit = sum(value for value in outcomes if value > 0)
        gross_loss = -sum(value for value in outcomes if value < 0)
        profit_factor = f"{gross_profit / gross_loss:.2f}" if gross_loss else "inf" if gross_profit else "-"
        print(f"Profit factor (P&L): {profit_factor}")
        for label, winning in (("Wins", True), ("Losses", False)):
            minutes = [row["duration_minutes"] for row in trades
                       if row["pnl_currency"] is not None and row["duration_minutes"] is not None
                       and (row["pnl_currency"] > 0 if winning else row["pnl_currency"] < 0)]
            print(f"Average minutes held ({label.lower()}): {_average(minutes)}")
        losses = [row for row in trades if row["pnl_currency"] is not None
                  and row["pnl_currency"] < 0 and row["duration_minutes"] is not None]
        early = (f"{100 * sum(row['duration_minutes'] <= 60 for row in losses) / len(losses):.1f}% "
                 f"(n={len(losses)})") if losses else "- (n=0)"
        print(f"Losses closed within 60 minutes: {early}")

        print("Win rate by UTC entry hour:")
        hours: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for row in trades:
            if row["entry_hour"] is not None:
                hours[row["entry_hour"]].append(row)
        for hour, hour_trades in sorted(hours.items()):
            print(f"  {hour}:00: {_percentage(hour_trades)}")
        if not hours:
            print("  -")

        print("Win rate by UTC session:")
        sessions: dict[str, list[sqlite3.Row]] = {"Asia": [], "London": [], "NY": [], "Other": []}
        unknown = []
        for row in trades:
            if row["entry_hour"] is None:
                unknown.append(row)
                continue
            hour = int(row["entry_hour"])
            session = "Asia" if hour <= 6 else "London" if hour <= 10 else "NY" if 12 <= hour <= 15 else "Other"
            sessions[session].append(row)
        if unknown:
            sessions["Unknown"] = unknown
        for session, session_trades in sessions.items():
            print(f"  {session}: {_percentage(session_trades)}")

        if reason_column:
            print("Close reasons (count, average R):")
            reasons: dict[str, list[sqlite3.Row]] = defaultdict(list)
            for row in trades:
                reasons[row["close_reason"] or "Unknown"].append(row)
            for reason, reason_trades in sorted(reasons.items()):
                print(f"  {reason}: {len(reason_trades)}, {_average(_multiples(reason_trades))}")

        for column, title, lower, upper in (("adx", "ADX", 25, 35),
                                             ("trend_strength", "Trend strength", 1, 2)):
            print(f"Win rate by {title}:")
            buckets: dict[str, list[sqlite3.Row]] = {
                f"<{lower}": [], f"{lower}-{upper}": [], f">{upper}": [],
            }
            for row in trades:
                value: Any = row[column]
                if value is not None:
                    key = f"<{lower}" if value < lower else f">{upper}" if value > upper else f"{lower}-{upper}"
                    buckets[key].append(row)
            for label, bucket in buckets.items():
                print(f"  {label}: {_percentage(bucket)}")


def main() -> int:
    """Open the configured database read-only and print the report."""
    default = Path(__file__).resolve().parent.parent / "Trades_db" / "pytrade.db"
    path = Path(os.environ.get("PYTRADE_DB", default)).resolve()
    try:
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            _print_report(conn)
    except sqlite3.Error as exc:
        print(f"Cannot read trade database: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())