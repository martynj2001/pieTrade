"""Walk-forward parameter optimisation for pyTrade strategies."""

import argparse
import calendar
import copy
import csv
import json
import math
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
BACKTEST = ROOT / "pyTrade_backtest.py"
RESULTS = ROOT / "results"
SECONDARY_STRATEGIES = {
    "breakout": "Breakout",
    "breakout_v2": "Breakout_V2",
    "range": "Range_Reversion",
}
TRADE_COLUMNS = [
    "pair", "strategy", "direction", "entry_time", "exit_time", "r",
    "bars_held", "exit_reason", "sample",
]
METRICS = ("trades", "win_pct", "avg_r", "total_r", "profit_factor", "max_dd_r")


def _merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge right over left without mutating either input."""
    merged = copy.deepcopy(left)
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _set_path(params: dict[str, Any], path: str, value: Any) -> None:
    """Set a dotted parameter path, creating missing mapping levels."""
    parts = path.split(".")
    if not all(parts):
        raise ValueError(f"Invalid step path: {path!r}")
    current = params
    for part in parts[:-1]:
        child = current.setdefault(part, {})
        if not isinstance(child, dict):
            raise ValueError(f"Step path {path!r} crosses non-object key {part!r}")
        current = child
    current[parts[-1]] = value


def _add_months(value: date, months: int) -> date:
    """Shift a date by calendar months, clamping at the target month's end."""
    month_index = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def _read_grid(path: Path) -> tuple[str, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    with path.open(encoding="utf-8") as grid_file:
        grid = json.load(grid_file)
    if not isinstance(grid, dict):
        raise ValueError("Grid file must contain a JSON object")

    secondary = str(grid.get("secondary", "none")).strip().lower()
    names = [name.strip() for name in secondary.split(",") if name.strip()]
    if names == ["none"]:
        names = []
        secondary = "none"
    if any(name not in SECONDARY_STRATEGIES for name in names) or len(set(names)) != len(names):
        raise ValueError("secondary must be none or a comma-separated list of supported strategies")
    secondary = "+".join(names) if names else "none"

    base_from: dict[str, Any] = {}
    base_from_path = grid.get("base_from")
    if base_from_path is not None:
        if not isinstance(base_from_path, str):
            raise ValueError("base_from must be a params-file path")
        source = Path(base_from_path).expanduser()
        if not source.is_absolute():
            source = path.parent / source
        with source.open(encoding="utf-8") as params_file:
            base_from = json.load(params_file)
        if not isinstance(base_from, dict):
            raise ValueError("base_from params file must contain a JSON object")

    base = grid.get("base", {})
    steps = grid.get("steps", [])
    backtest_args = grid.get("args", {})
    if not isinstance(base, dict) or not isinstance(steps, list) or not isinstance(backtest_args, dict):
        raise ValueError("base and args must be objects and steps must be an array")
    normalized_args = {}
    reserved_args = {"pairs", "months", "secondary", "jobs", "live-validation", "params", "from", "to", "tag"}
    for key, value in backtest_args.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key):
            raise ValueError(f"Invalid backtest arg key: {key!r}")
        option = key.replace("_", "-")
        if option in reserved_args or option in normalized_args:
            raise ValueError(f"Backtest arg {option!r} is reserved or duplicated")
        if isinstance(value, (dict, list)) or value is None:
            raise ValueError(f"Backtest arg {option!r} must have a scalar value")
        normalized_args[option] = value
    for step in steps:
        if (not isinstance(step, dict) or not isinstance(step.get("path"), str)
                or not isinstance(step.get("values"), list) or not step["values"]):
            raise ValueError("Each step requires a dotted path and a non-empty values array")
    return secondary, _merge(base_from, base), steps, normalized_args


def _read_trades(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise RuntimeError(f"Backtest did not create its trade CSV: {path}")
    with path.open(newline="", encoding="utf-8") as trade_file:
        return list(csv.DictReader(trade_file))


def _summarize(rows: list[dict[str, str]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: row.get("exit_time", ""))
    values = [float(row["r"]) for row in ordered]
    wins = sum(value > 0 for value in values)
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    equity = peak = max_drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    profit_factor: float | str | None = (
        gross_profit / gross_loss if gross_loss else "inf" if gross_profit else None
    )
    count = len(values)
    return {
        "trades": count,
        "win_pct": 100 * wins / count if count else 0.0,
        "avg_r": sum(values) / count if count else 0.0,
        "total_r": sum(values),
        "profit_factor": profit_factor,
        "max_dd_r": max_drawdown,
    }


def _summaries(rows: list[dict[str, str]], strategies: list[str]) -> dict[str, dict[str, Any]]:
    return {
        strategy: _summarize([row for row in rows if row.get("strategy") == strategy])
        for strategy in strategies
    }


def _score(summary: dict[str, Any]) -> float:
    if summary["trades"] < 30:
        return -math.inf
    return summary["avg_r"] * math.sqrt(summary["trades"])


def _run_backtest(
    secondary: str,
    pairs: str,
    months: int,
    jobs: int,
    params: dict[str, Any],
    start: date,
    end: date,
    params_path: Path,
    backtest_args: dict[str, Any],
) -> list[dict[str, str]]:
    params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")
    command = [
        sys.executable, str(BACKTEST), "--pairs", pairs,
        "--months", str(months), "--secondary", secondary.replace("+", ","),
        "--jobs", str(jobs), "--live-validation", "--params", str(params_path),
        "--from", start.isoformat(), "--to", end.isoformat(), "--tag", "wf_tmp",
    ]
    for key, value in backtest_args.items():
        command.extend((f"--{key}", str(value)))
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout)[-3000:]
        raise RuntimeError(f"Backtest failed for {start} through {end}:\n{detail}")
    stem = secondary if secondary != "none" else "none"
    return _read_trades(RESULTS / f"{stem}_wf_tmp.csv")


def _write_results(
    secondary: str,
    windows: list[dict[str, Any]],
    test_trades: list[dict[str, str]],
    strategies: list[str],
) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary_path = RESULTS / f"wf_{secondary}.csv"
    columns = ["window", "train_from", "train_to", "test_from", "test_to", "chosen_params"]
    columns += [f"{sample}_{strategy}_{metric}" for sample in ("train", "test")
                for strategy in strategies for metric in METRICS]
    with summary_path.open("w", newline="", encoding="utf-8") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=columns)
        writer.writeheader()
        for window in windows:
            row: dict[str, Any] = {
                "window": window["window"],
                "train_from": window["train_from"],
                "train_to": window["train_to"],
                "test_from": window["test_from"],
                "test_to": window["test_to"],
                "chosen_params": json.dumps(window["params"], sort_keys=True),
            }
            for sample in ("train", "test"):
                for strategy in strategies:
                    metrics = window[sample][strategy]
                    for metric in METRICS:
                        row[f"{sample}_{strategy}_{metric}"] = metrics[metric]
            writer.writerow(row)

    trades_path = RESULTS / f"wf_{secondary}_trades.csv"
    with trades_path.open("w", newline="", encoding="utf-8") as trades_file:
        writer = csv.DictWriter(trades_file, fieldnames=["window", *TRADE_COLUMNS])
        writer.writeheader()
        for trade in test_trades:
            writer.writerow(trade)

    final_path = RESULTS / f"wf_{secondary}_final.json"
    final_path.write_text(json.dumps(windows[-1]["params"], indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", required=True)
    parser.add_argument("--pairs", default="EUR_USD,GBP_USD")
    parser.add_argument("--months", type=int, default=24)
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    if args.months < 15:
        parser.error("--months must provide at least 12 training months and 3 test months")
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    pairs = [pair.strip().upper() for pair in args.pairs.split(",")]
    if not pairs or any(not re.fullmatch(r"[A-Z]{3}_[A-Z]{3}", pair) for pair in pairs):
        parser.error("--pairs must contain comma-separated currency pairs such as EUR_USD")

    try:
        grid_path = Path(args.grid).expanduser().resolve()
        secondary, base, steps, backtest_args = _read_grid(grid_path)
        secondary_names = [] if secondary == "none" else secondary.split("+")
        score_strategy = (
            "EMA_TrendFollowing" if not secondary_names
            else SECONDARY_STRATEGIES[secondary_names[0]]
        )
        strategies = list(dict.fromkeys(["EMA_TrendFollowing", *(SECONDARY_STRATEGIES[name] for name in secondary_names)]))
        windows_count = (args.months - 12) // 3
        last_day = datetime.now(timezone.utc).date()
        end_exclusive = last_day + timedelta(days=1)
        RESULTS.mkdir(parents=True, exist_ok=True)

        tag_stem = secondary
        transient_paths = (
            RESULTS / f"{tag_stem}_wf_tmp.csv",
            RESULTS / f"{tag_stem}_wf_tmp_summary.json",
        )
        backups = {path: path.read_bytes() if path.exists() else None for path in transient_paths}
        windows: list[dict[str, Any]] = []
        all_test_trades: list[dict[str, str]] = []
        try:
            with tempfile.TemporaryDirectory(prefix="pytrade-wf-") as temp_dir:
                params_path = Path(temp_dir) / "params.json"
                for index in range(windows_count):
                    test_end_exclusive = _add_months(end_exclusive, -3 * index)
                    test_start = _add_months(test_end_exclusive, -3)
                    train_end_exclusive = test_start
                    train_start = _add_months(train_end_exclusive, -12)
                    train_end = train_end_exclusive - timedelta(days=1)
                    test_end = test_end_exclusive - timedelta(days=1)
                    chosen = copy.deepcopy(base)

                    for step in steps:
                        best_value = step["values"][0]
                        best_score = -math.inf
                        for value in step["values"]:
                            candidate = copy.deepcopy(chosen)
                            _set_path(candidate, step["path"], value)
                            rows = _run_backtest(
                                secondary, args.pairs, args.months, args.jobs,
                                candidate, train_start, train_end, params_path, backtest_args,
                            )
                            score = _score(_summarize(
                                [row for row in rows if row.get("strategy") == score_strategy]
                            ))
                            if score > best_score:
                                best_value, best_score = value, score
                        _set_path(chosen, step["path"], best_value)

                    train_rows = _run_backtest(
                        secondary, args.pairs, args.months, args.jobs,
                        chosen, train_start, train_end, params_path, backtest_args,
                    )
                    test_rows = _run_backtest(
                        secondary, args.pairs, args.months, args.jobs,
                        chosen, test_start, test_end, params_path, backtest_args,
                    )
                    window_number = index + 1
                    for trade in test_rows:
                        all_test_trades.append({"window": str(window_number), **trade})
                    windows.append({
                        "window": window_number,
                        "train_from": train_start.isoformat(),
                        "train_to": train_end.isoformat(),
                        "test_from": test_start.isoformat(),
                        "test_to": test_end.isoformat(),
                        "params": chosen,
                        "train": _summaries(train_rows, strategies),
                        "test": _summaries(test_rows, strategies),
                    })
                    print(f"Window {window_number}/{windows_count}: {test_start} to {test_end}", flush=True)
        finally:
            for path, content in backups.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)

        _write_results(secondary, windows, all_test_trades, strategies)
        return 0
    except Exception as exc:
        print(f"Optimisation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())