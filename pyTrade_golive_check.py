"""Evaluate walk-forward and optional holdout backtest results for demo readiness."""

import argparse
import csv
import math
import re
import sys
from pathlib import Path
from typing import Any


RESULTS = Path(__file__).resolve().parent / "results"
PRIMARY_STRATEGY = "EMA_TrendFollowing"
SECONDARY_STRATEGIES = {
    "breakout": "Breakout",
    "breakout_v2": "Breakout_V2",
    "range": "Range_Reversion",
}


def _read_trades(path: Path, require_window: bool = False) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"file not found: {path}")
    with path.open(newline="", encoding="utf-8") as trade_file:
        reader = csv.DictReader(trade_file)
        fields = set(reader.fieldnames or ())
        required = {"r", "strategy", "exit_time"}
        if require_window:
            required.add("window")
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
        rows = []
        for line, row in enumerate(reader, start=2):
            try:
                value = float(row["r"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{line} has an invalid R value") from exc
            if not math.isfinite(value):
                raise ValueError(f"{path}:{line} has a non-finite R value")
            rows.append({**row, "r_value": value})
    return rows


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: row.get("exit_time", ""))
    values = [row["r_value"] for row in ordered]
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    return {
        "trades": len(values),
        "avg_r": sum(values) / len(values) if values else 0.0,
        "total_r": sum(values),
        "profit_factor": gains / losses if losses else math.inf if gains else 0.0,
    }


def _drawdown_and_streak(rows: list[dict[str, Any]]) -> tuple[float, int]:
    ordered = sorted(rows, key=lambda row: row.get("exit_time", ""))
    equity = peak = max_drawdown = 0.0
    streak = longest_streak = 0
    for row in ordered:
        value = row["r_value"]
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if value < 0:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0
    return max_drawdown, longest_streak


def _expected_secondary(run_name: str, rows: list[dict[str, Any]]) -> list[str]:
    expected = [
        SECONDARY_STRATEGIES[name]
        for name in run_name.split("+")
        if name in SECONDARY_STRATEGIES
    ]
    present = sorted({row["strategy"] for row in rows if row["strategy"] != PRIMARY_STRATEGY})
    return list(dict.fromkeys([*expected, *present]))


def _format_number(value: float) -> str:
    return "inf" if math.isinf(value) else f"{value:.3f}"


def _report_gate(name: str, passed: bool, value: str) -> None:
    print(f"{name} {'PASS' if passed else 'FAIL'} | {value}")


def _holdout_gate(name: str, path_value: str | None) -> tuple[bool, str]:
    if path_value is None:
        return False, "not supplied"
    path = Path(path_value).expanduser()
    try:
        rows = _read_trades(path)
        summary = _metrics(rows)
        return summary["avg_r"] > 0, f"avg R={summary['avg_r']:.3f} ({summary['trades']} trades)"
    except (OSError, ValueError) as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Walk-forward run name")
    parser.add_argument("--baseline", default="none", help="Baseline walk-forward run name (default: none)")
    parser.add_argument("--stress", help="Optional stress-test backtest trade CSV")
    parser.add_argument("--unseen", help="Optional unseen-period backtest trade CSV")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_+-]+", args.run):
        parser.error("--run must be a run name, not a path")
    if not re.fullmatch(r"[A-Za-z0-9_+-]+", args.baseline):
        parser.error("--baseline must be a run name, not a path")

    failed: list[str] = []
    run_path = RESULTS / f"wf_{args.run}_trades.csv"
    baseline_path = RESULTS / f"wf_{args.baseline}_trades.csv"
    try:
        trades = _read_trades(run_path, require_window=True)
    except (OSError, ValueError) as exc:
        print(f"Could not read run trades: {exc}", file=sys.stderr)
        trades = []
        run_error = str(exc)
    else:
        run_error = None

    try:
        baseline = _read_trades(baseline_path)
        baseline_total = _metrics(baseline)["total_r"]
        baseline_error = None
    except (OSError, ValueError) as exc:
        baseline_total = None
        baseline_error = str(exc)

    total = _metrics(trades)
    g1_pass = (
        run_error is None and baseline_error is None
        and total["avg_r"] >= 0.05
        and total["profit_factor"] >= 1.15
        and total["total_r"] > baseline_total
    )
    g1_value = (
        f"avg R={total['avg_r']:.3f} (>= 0.050), PF={_format_number(total['profit_factor'])} (>= 1.150), "
        f"total R={total['total_r']:.3f} > baseline={_format_number(baseline_total) if baseline_total is not None else 'unavailable'}"
    )
    if run_error or baseline_error:
        g1_value += f"; input error: {run_error or baseline_error}"
    _report_gate("G1", g1_pass, g1_value)
    if not g1_pass:
        failed.append("G1")

    secondary = _expected_secondary(args.run, trades)
    g2_results = []
    if not secondary:
        g2_pass = True
        g2_value = "no non-primary strategies in this run"
    else:
        g2_details = []
        for strategy in secondary:
            summary = _metrics([row for row in trades if row["strategy"] == strategy])
            passed = (summary["trades"] >= 60 and summary["avg_r"] >= 0.05
                      and summary["profit_factor"] >= 1.10)
            g2_results.append(passed)
            g2_details.append(
                f"{strategy}: {summary['trades']} trades (>= 60), avg R={summary['avg_r']:.3f} (>= 0.050), "
                f"PF={_format_number(summary['profit_factor'])} (>= 1.100)"
            )
        g2_pass = all(g2_results)
        g2_value = "; ".join(g2_details)
    _report_gate("G2", g2_pass, g2_value)
    if not g2_pass:
        failed.append("G2")

    by_window: dict[str, float] = {}
    for row in trades:
        window = str(row["window"])
        by_window[window] = by_window.get(window, 0.0) + row["r_value"]
    window_order = sorted(by_window, key=int) if by_window and all(value.isdigit() for value in by_window) else list(by_window)
    recent_windows = window_order[:4]
    positive_windows = sum(by_window[window] > 0 for window in recent_windows)
    g3_pass = len(recent_windows) == 4 and positive_windows >= 3
    _report_gate("G3", g3_pass, f"{positive_windows}/4 recent windows have positive total R ({len(recent_windows)} available)")
    if not g3_pass:
        failed.append("G3")

    g4_pass, g4_value = _holdout_gate("G4", args.stress)
    _report_gate("G4", g4_pass, g4_value)
    if not g4_pass:
        failed.append("G4")

    g5_pass, g5_value = _holdout_gate("G5", args.unseen)
    _report_gate("G5", g5_pass, g5_value)
    if not g5_pass:
        failed.append("G5")

    max_drawdown, longest_streak = _drawdown_and_streak(trades)
    g6_pass = max_drawdown <= 25 and longest_streak <= 15
    _report_gate("G6", g6_pass, f"max DD R={max_drawdown:.3f} (<= 25), longest loss streak={longest_streak} (<= 15)")
    if not g6_pass:
        failed.append("G6")

    print("GO DEMO" if not failed else f"NO GO: {', '.join(failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
