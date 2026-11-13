"""Summarize backtest results and compare secondary strategies."""

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


PRIMARY_STRATEGIES = {"EMA_TrendFollowing", "TrendFollowing"}
SECONDARIES = ("breakout_v2", "breakout", "range", "none")


def _run_parts(name: str) -> tuple[str | None, str]:
    """Split a run name into its secondary and optional group suffix."""
    for secondary in SECONDARIES:
        if name == secondary or name.startswith(f"{secondary}_"):
            return secondary, name[len(secondary):]
    return None, ""


def metrics(trades: pd.DataFrame, weeks: float | None) -> dict[str, Any]:
    """Calculate closed-trade statistics in chronological exit order."""
    ordered = trades.sort_values("exit_time", kind="stable")
    values = ordered["r"].tolist()
    wins = [value for value in values if value > 0]
    losses = [-value for value in values if value < 0]
    equity = peak = drawdown = 0.0
    streak = longest_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        streak = streak + 1 if value < 0 else 0
        longest_streak = max(longest_streak, streak)
    count = len(values)
    profit_factor = sum(wins) / sum(losses) if losses else math.inf if wins else None
    breakeven = 100 / (1 + (sum(wins) / len(wins)) / (sum(losses) / len(losses))) if wins and losses else None
    return {
        "trades": count,
        "trades_week": count / weeks if weeks and weeks > 0 else None,
        "win_pct": 100 * len(wins) / count if count else None,
        "avg_r": sum(values) / count if count else None,
        "total_r": sum(values), "profit_factor": profit_factor,
        "drawdown": drawdown, "losing_streak": longest_streak,
        "breakeven": breakeven,
    }


def load_run(path: Path, sample: str) -> pd.DataFrame:
    """Read and validate a backtest CSV, then select the requested sample."""
    trades = pd.read_csv(path)
    required = {"pair", "strategy", "entry_time", "exit_time", "r", "exit_reason", "sample"}
    if not required.issubset(trades.columns):
        raise ValueError(f"missing columns: {', '.join(sorted(required - set(trades.columns)))}")
    if trades.empty:
        return trades
    if trades[list(required)].isna().any().any():
        raise ValueError("required trade data contains missing values")
    if not trades["sample"].isin(["in", "out"]).all():
        raise ValueError("sample must be in or out")
    trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True, errors="raise")
    trades["exit_time"] = pd.to_datetime(trades["exit_time"], utc=True, errors="raise")
    trades["r"] = pd.to_numeric(trades["r"], errors="raise")
    if not trades["r"].map(math.isfinite).all() or (trades["exit_time"] < trades["entry_time"]).any():
        raise ValueError("invalid R value or trade timestamps")
    return trades if sample == "all" else trades.loc[trades["sample"] == sample].copy()


def _number(value: float | None, decimals: int = 2) -> str:
    """Format optional statistics for the report."""
    if value is None:
        return "-"
    return f"{value:.{decimals}f}"


def _table(headers: list[str], rows: list[list[object]]) -> None:
    """Print aligned columns."""
    values = [[str(value) for value in row] for row in rows]
    widths = [max([len(header), *(len(row[index]) for row in values)]) for index, header in enumerate(headers)]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in values:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _metric_row(result: dict[str, Any]) -> list[object]:
    """Format the shared performance columns."""
    return [result["trades"], _number(result["trades_week"]), _number(result["win_pct"], 1),
            _number(result["avg_r"]), _number(result["total_r"]), _number(result["profit_factor"]),
            _number(result["drawdown"]), result["losing_streak"]]


def _plot_equity(path: Path, trades: pd.DataFrame, sample: str) -> None:
    """Save the selected sample's combined-strategy equity curve."""
    figure, axis = plt.subplots(figsize=(10, 4))
    if not trades.empty:
        ordered = trades.sort_values("exit_time", kind="stable")
        times = [ordered["entry_time"].min(), *ordered["exit_time"].tolist()]
        equity = [0.0, *ordered["r"].cumsum().tolist()]
        axis.plot(times, equity, color="#167849", linewidth=1.5)
    else:
        axis.text(0.5, 0.5, "No trades", ha="center", va="center", transform=axis.transAxes)
    axis.axhline(0, color="#777777", linewidth=0.7)
    axis.set_title(f"{path.stem} - {sample} sample")
    axis.set_xlabel("Exit time (UTC)")
    axis.set_ylabel("Cumulative R")
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(path.with_name(f"{path.stem}_equity.png"))
    plt.close(figure)


def main() -> int:
    """Print the report and save one equity curve for each available run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", choices=("in", "out", "all"), default="out")
    sample = parser.parse_args().sample
    paths = sorted(Path("results").glob("*.csv"))
    if not paths:
        print("No backtest CSV files found in results/.")
        print("Keep EMA only")
        return 0

    runs: dict[str, pd.DataFrame] = {}
    for path in paths:
        try:
            runs[path.stem] = load_run(path, sample)
            _plot_equity(path, runs[path.stem], sample)
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            print(f"Skipping {path}: {exc}", file=sys.stderr)
            runs.pop(path.stem, None)

    print(f"Backtest report: {sample} sample")
    print("Trades/week uses each run's observed first entry to last exit; CSVs do not include test-period boundaries.")
    print("Baseline comparisons assume matching backtest periods and pairs.")
    metric_headers = ["Trades", "Trades/week", "Win %", "Avg R", "Total R", "PF", "Max DD R", "Loss streak"]
    run_results: dict[str, dict[str, Any]] = {}
    run_weeks: dict[str, float | None] = {}
    for name, trades in runs.items():
        weeks = (trades["exit_time"].max() - trades["entry_time"].min()).total_seconds() / (7 * 86400) if not trades.empty else None
        run_weeks[name] = weeks
        run_results[name] = metrics(trades, weeks)

    print("\nAll strategies")
    _table(["Run", *metric_headers], [[name, *_metric_row(result)] for name, result in run_results.items()])

    secondary_pass: dict[str, bool] = {}
    secondary_rows = []
    breakdowns = []
    for name, trades in runs.items():
        if _run_parts(name)[0] == "none":
            continue
        secondary = trades.loc[~trades["strategy"].isin(PRIMARY_STRATEGIES)]
        secondary_pass[name] = not secondary.empty
        if secondary.empty:
            result = metrics(secondary, run_weeks[name])
            secondary_rows.append([name, "(no secondary trades)", *_metric_row(result), "-", "FAIL", "FAIL", "FAIL"])
        for strategy, group in secondary.groupby("strategy", sort=True):
            result = metrics(group, run_weeks[name])
            avg_ok = result["avg_r"] is not None and result["avg_r"] >= 0.10
            pf_ok = result["profit_factor"] is not None and result["profit_factor"] >= 1.2
            count_ok = result["trades"] >= 60
            secondary_pass[name] = secondary_pass[name] and avg_ok and pf_ok and count_ok
            secondary_rows.append([name, strategy, *_metric_row(result), _number(result["breakeven"], 1),
                                   "PASS" if avg_ok else "FAIL", "PASS" if pf_ok else "FAIL",
                                   "PASS" if count_ok else "FAIL"])
            for label, column in (("Pair", "pair"), ("UTC hour", "hour"), ("Exit reason", "exit_reason")):
                grouped = group.assign(hour=group["entry_time"].dt.strftime("%H:00")) if column == "hour" else group
                for value, subset in grouped.groupby(column, sort=True):
                    breakdowns.append([name, strategy, label, value, len(subset), _number(subset["r"].mean())])

    print("\nSecondary strategies")
    _table(["Run", "Strategy", *metric_headers, "Break-even %", "Avg R >= 0.10", "PF >= 1.2", "Trades >= 60"], secondary_rows)

    print("\nVersus none")
    comparisons = []
    eligible = []
    zero_baselines = set()
    for name, result in run_results.items():
        secondary, group = _run_parts(name)
        if secondary == "none":
            continue
        baseline_name = f"none{group}" if secondary is not None else None
        baseline = run_results.get(baseline_name) if baseline_name else None
        difference = ratio = None
        if baseline and baseline["trades"] and result["trades"]:
            difference = result["total_r"] - baseline["total_r"]
            if baseline["drawdown"] > 0:
                ratio = result["drawdown"] / baseline["drawdown"]
            elif result["drawdown"] > 0:
                ratio = math.inf
            if baseline["drawdown"] == 0:
                zero_baselines.add(baseline_name)
        passed = difference is not None and difference > 0 and ratio is not None and ratio <= 1.5
        comparisons.append([name, baseline_name or "-", _number(difference), _number(ratio), "PASS" if passed else "FAIL"])
        if passed and secondary_pass.get(name, False):
            eligible.append((result["total_r"], name))
    _table(["Run", "Baseline", "Total R difference", "Drawdown ratio", "Result"], comparisons)
    if zero_baselines:
        print("A zero baseline drawdown makes the ratio undefined or infinite; comparison fails: " + ", ".join(sorted(zero_baselines)))

    print("\nSecondary breakdowns")
    _table(["Run", "Strategy", "Group", "Value", "Trades", "Avg R"], breakdowns)
    print(max(eligible)[1] if eligible else "Keep EMA only")
    return 0


if __name__ == "__main__":
    sys.exit(main())