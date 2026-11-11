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


def _print_report(conn: sqlite3.Connection) -> None:
    """Print per-strategy results using the latest signal for each trade."""
    rows = conn.execute(
        """SELECT t.strategy, t.pnl_currency, t.risk_amount, t.duration_minutes,
                  strftime('%H', t.entry_time) AS entry_hour, s.adx, s.trend_strength
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
        multiples = [row["pnl_currency"] / row["risk_amount"] for row in trades
                     if row["pnl_currency"] is not None and row["risk_amount"] is not None
                     and row["risk_amount"] > 0]
        print(f"Average R: {_average(multiples)}")
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