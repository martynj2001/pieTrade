"""Replay the bot's strategies against historical OANDA candles."""

import math
import argparse
import importlib
import json
import logging
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from oandapyV20 import API
from oandapyV20.contrib.factories import InstrumentsCandlesFactory

import config
import pyTrade_instruments
import pyTrade_market_session as market
from pyTrade_TrendFollowing_Strategy import TrendFollowingEngine
from pyTrade_trade_guards import TradeGuards
from pyTrade_validation import Validation


SPREAD_PIPS: dict[str, float] = {}

SECONDARIES = {
    "breakout": ("pyTrade_Breakout_Strategy", "BreakoutEngine"),
    "breakout_v2": ("pyTrade_BreakoutV2_Strategy", "BreakoutV2Engine"),
    "range": ("pyTrade_RangeReversion_Strategy", "RangeReversionEngine"),
}
RESULT_COLUMNS = ["pair", "strategy", "direction", "entry_time", "exit_time", "r", "bars_held", "exit_reason", "sample"]


class BacktestValidation(Validation):
    """Use the simulated candle close for time and session checks."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.candle_close = None

    def check_time_invalidation(self, pos, candle_time=None):
        return super().check_time_invalidation(pos, self.candle_close)

    def check_session_invalidation(self, current_market, utc_now=None):
        return super().check_session_invalidation(current_market, self.candle_close)


def load_candles(pair: str, granularity: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Download missing candle history and retain a deduplicated CSV cache."""
    path = Path("data") / f"{pair}_{granularity}.csv"
    columns = ["time", "open", "high", "low", "close"]
    cached = pd.read_csv(path, parse_dates=["time"]) if path.exists() else pd.DataFrame(columns=columns)
    cached["time"] = pd.to_datetime(cached["time"], utc=True)
    interval = pd.Timedelta(minutes=15) if granularity == "M15" else pd.Timedelta(hours=1)
    ranges = []
    if cached.empty:
        ranges.append((start, end))
    else:
        if start < cached["time"].min():
            ranges.append((start, cached["time"].min()))
        if cached["time"].max() + interval < end:
            ranges.append((cached["time"].max() + interval, end))

    downloaded = []
    if ranges:
        token = getattr(config, "OANDA_API_KEY", "").strip()
        if not token:
            raise ValueError("OANDA_API_KEY is required to download candles")
        client = API(access_token=token, environment=getattr(config, "OANDA_ENVIRON", "practice"))
        for range_start, range_end in ranges:
            params = {"from": range_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "to": range_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "granularity": granularity, "price": "M", "count": 5000}
            for request in InstrumentsCandlesFactory(instrument=pair, params=params):
                for candle in client.request(request).get("candles", []):
                    if candle.get("complete"):
                        mid = candle["mid"]
                        downloaded.append({"time": candle["time"], "open": float(mid["o"]),
                                           "high": float(mid["h"]), "low": float(mid["l"]),
                                           "close": float(mid["c"])})
    if downloaded:
        new = pd.DataFrame(downloaded, columns=columns)
        new["time"] = pd.to_datetime(new["time"], utc=True)
        cached = new if cached.empty else pd.concat([cached, new], ignore_index=True)
        cached = cached.drop_duplicates(subset="time", keep="last").sort_values("time").reset_index(drop=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        cached.to_csv(path, index=False)
    return cached.loc[(cached["time"] >= start) & (cached["time"] + interval <= end)].reset_index(drop=True)


def make_engines(secondary: list[str] | str, primary_kwargs: dict[str, Any] | None = None,
                 secondary_kwargs: dict[str, Any] | None = None) -> list[Any]:
    """Create the primary and requested secondary engines in fallback order."""
    if isinstance(secondary, str):
        secondary = [] if secondary == "none" else [secondary]
    engines: list[Any] = [TrendFollowingEngine(**(primary_kwargs or {}))]
    for name in secondary:
        module_name, class_name = SECONDARIES[name]
        try:
            module = importlib.import_module(module_name)
            engine_class = getattr(module, class_name)
        except (ModuleNotFoundError, AttributeError) as exc:
            raise ValueError(f"Secondary engine {name!r} is unavailable: expected {module_name}.{class_name}") from exc
        engines.append(engine_class(**((secondary_kwargs or {}).get(name, {}))))
    return engines


class _LastMessageHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.message = ""

    def emit(self, record: logging.LogRecord) -> None:
        self.message = record.getMessage()

def _guard_passes(guards: TradeGuards, engine: Any, candles: pd.DataFrame,
                  hourly: pd.DataFrame, direction: str) -> bool:
    """Apply the same qualification checks as the live bot."""
    name = engine.strategy_name
    if name in {"EMA_TrendFollowing", "TrendFollowing"}:
        return guards.validate_trend_following(candles, hourly, direction)
    if name in {"Breakout", "Breakout_V2"}:
        column = "DC_Upper" if direction == "BUY" else "DC_Lower"
        if column not in candles or pd.isna(candles[column].iloc[-1]):
            return False
        return guards.validate_breakout(
            candles, hourly, float(candles[column].iloc[-1]), direction,
            skip_adx=getattr(engine, "adx_mode", "threshold") == "rising",
        )
    if name == "Range_Reversion":
        return guards.validate_range(
            candles, hourly, direction, h1_max_dist_atr=getattr(engine, "h1_max_dist_atr", None),
        )
    raise ValueError(f"No trade guard configured for strategy {name}")


def run_pair(pair: str, candles: pd.DataFrame, hourly: pd.DataFrame, engines: list[Any],
             guards: TradeGuards, split: pd.Timestamp, spread_mult: float = 1.0,
             live_validation: bool = False, validation_kwargs: dict[str, Any] | None = None,
             trade_start: pd.Timestamp | None = None, trade_end: pd.Timestamp | None = None,
             funnel_counts: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """Simulate one position at a time, using only candles available at each decision."""
    frames = [engine.add_indicators(candles.copy()) for engine in engines]
    hourly_close_times = hourly["time"] + pd.Timedelta(hours=1)
    half_spread = SPREAD_PIPS.get(pair, 1.2) * spread_mult * pyTrade_instruments.pip_size(pair) / 2
    trades: list[dict[str, Any]] = []
    position = None
    validator = BacktestValidation(**(validation_kwargs or {})) if live_validation else None
    handlers: dict[str, _LastMessageHandler] = {}
    logger_levels: dict[logging.Logger, int] = {}
    if funnel_counts is not None:
        loggers = {engine.logger for engine in engines if isinstance(getattr(engine, "logger", None), logging.Logger)}
        if isinstance(getattr(guards, "logger", None), logging.Logger):
            loggers.add(guards.logger)
        for logger in loggers:
            handler = _LastMessageHandler()
            logger.addHandler(handler)
            logger_levels[logger] = logger.level
            logger.setLevel(logging.DEBUG)
            handlers[logger.name] = handler

    for index in range(len(candles)):
        candle = candles.iloc[index]
        if position is not None:
            direction = position["direction"]
            adjustment = -half_spread if direction == "BUY" else half_spread
            stop_hit = (candle["low"] + adjustment <= position["stop"] if direction == "BUY"
                        else candle["high"] + adjustment >= position["stop"])
            target_hit = (candle["high"] + adjustment >= position["target"] if direction == "BUY"
                          else candle["low"] + adjustment <= position["target"])
            position["bars_held"] += 1
            reason = "sl" if stop_hit else "tp" if target_hit else None
            exit_price = position["stop"] if stop_hit else position["target"] if target_hit else None
            engine = position["engine"]
            if reason is None and validator is not None:
                validator.candle_close = candle["time"] + pd.Timedelta(minutes=15)
                pos = {
                    "instrument": pair, "direction": "long" if direction == "BUY" else "short",
                    "units": 1 if direction == "BUY" else -1, "entry_price": position["entry_price"],
                    "tradeID": None, "strategy": engine.strategy_name,
                    "trade_time": position["entry_time"].isoformat(),
                }
                current_market = market.get_open_session(validator.candle_close)["market"]
                validity = validator.validate_position(
                    pos, frames[position["engine_index"]].iloc[:index + 1], current_market, engine.strategy_name,
                )
                if not validity["validity"]:
                    reason, exit_price = validity["reason"][:40], float(candle["close"]) + adjustment
            if reason is None and callable(getattr(engine, "manage", None)):
                if engine.manage(position, frames[position["engine_index"]].iloc[:index + 1]) == "close":
                    reason, exit_price = "manage", float(candle["close"]) + adjustment
            if reason is None and index == len(candles) - 1:
                reason, exit_price = "end_of_data", float(candle["close"]) + adjustment
            if reason is not None:
                sign = 1 if direction == "BUY" else -1
                trades.append({
                    "pair": pair, "strategy": engine.strategy_name, "direction": direction,
                    "entry_time": position["entry_time"], "exit_time": candle["time"] + pd.Timedelta(minutes=15),
                    "r": sign * (exit_price - position["entry_price"]) / position["risk"],
                    "bars_held": position["bars_held"], "exit_reason": reason,
                    "sample": "out" if position["entry_time"] >= split else "in",
                })
                position = None
            continue

        if index < 200 or (trade_start is not None and candle["time"] < trade_start):
            continue
        if trade_end is not None and candle["time"] >= trade_end:
            continue
        if index + 1 >= len(candles):
            break
        closed_at = candle["time"] + pd.Timedelta(minutes=15)
        h1_slice = hourly.iloc[:hourly_close_times.searchsorted(closed_at, side="right")]
        if len(h1_slice) < 60:
            continue
        for engine_index, engine in enumerate(engines):
            if funnel_counts is not None:
                for handler in handlers.values():
                    handler.message = ""
            frame = frames[engine_index].iloc[:index + 1]
            original_add_indicators = engine.add_indicators
            engine.add_indicators = lambda data: data
            try:
                direction, entry, stop, target = engine.get_signal(frame, instrument=pair)
            finally:
                engine.add_indicators = original_add_indicators
            if direction not in ("BUY", "SELL") or any(value is None for value in (entry, stop, target)):
                continue
            if _guard_passes(guards, engine, frame, h1_slice, direction):
                next_candle = candles.iloc[index + 1]
                entry_price = float(next_candle["open"]) + (half_spread if direction == "BUY" else -half_spread)
                stop, target = float(stop), float(target)
                sign = 1 if direction == "BUY" else -1
                if all(math.isfinite(value) for value in (entry_price, stop, target)) and sign * (entry_price - stop) > 0 and sign * (target - entry_price) > 0:
                    position = {
                        "engine": engine, "engine_index": engine_index, "direction": direction,
                        "entry_time": next_candle["time"], "entry_price": entry_price,
                        "stop": stop, "target": target, "risk": abs(entry_price - stop), "bars_held": 0,
                    }
                    break
            if position is None and funnel_counts is not None:
                engine_logger = getattr(engine, "logger", None)
                message = handlers.get(engine_logger.name).message if engine_logger and engine_logger.name in handlers else ""
                if not message and guards.logger.name in handlers:
                    message = handlers[guards.logger.name].message
                message = (message or "No signal").strip()[:50]
                key = f"{engine.strategy_name}: {message}"
                funnel_counts[key] = funnel_counts.get(key, 0) + 1
    for logger in logger_levels:
        logger.removeHandler(handlers[logger.name])
        logger.setLevel(logger_levels[logger])
    return trades


def _summary_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda trade: trade["exit_time"]) if trades and "exit_time" in trades[0] else trades
    values = [float(trade["r"]) for trade in ordered]
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    equity = peak = max_drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "trades": len(values),
        "win_pct": 100 * sum(value > 0 for value in values) / len(values) if values else 0.0,
        "avg_r": sum(values) / len(values) if values else 0.0,
        "total_r": sum(values),
        "profit_factor": gross_profit / gross_loss if gross_loss else "inf" if gross_profit else None,
        "max_dd_r": max_drawdown,
    }


def _run_pair_job(job: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    for name, value in job["config_kwargs"].items():
        setattr(config, name, value)
    engines = make_engines(job["secondary"], job["primary_kwargs"], job["secondary_kwargs"])
    guards = TradeGuards(**job["guard_kwargs"])
    funnel: dict[str, int] = {}
    trades = run_pair(
        job["pair"], job["candles"], job["hourly"], engines, guards, job["split"],
        job["spread_mult"], job["live_validation"], job["validation_kwargs"],
        job["trade_start"], job["trade_end"], funnel if job["funnel"] else None,
    )
    return trades, funnel


def _read_params(path: str | None) -> dict[str, Any]:
    if path is None:
        return {"primary": {}, "secondary": {}, "guards": {}, "validation": {}, "config": {}}
    with open(path, encoding="utf-8") as params_file:
        params = json.load(params_file)
    if not isinstance(params, dict):
        raise ValueError("--params must contain a JSON object")
    values = {key: params.get(key, {}) for key in ("primary", "secondary", "guards", "validation", "config")}
    for key in values:
        if not isinstance(values[key], dict):
            raise ValueError(f"--params key {key!r} must be a JSON object")
    return values


def _secondary_options(value: dict[str, Any], names: list[str]) -> dict[str, dict[str, Any]]:
    if value and all(key in SECONDARIES and isinstance(options, dict) for key, options in value.items()):
        return {name: value.get(name, {}) for name in names}
    return {name: value for name in names}


def _date_bound(value: str, end: bool = False) -> pd.Timestamp:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"Invalid date {value!r}; expected YYYY-MM-DD") from exc
    if end:
        parsed += timedelta(days=1)
    return pd.Timestamp(parsed)


def print_summary(trades: list[dict[str, Any]], engines: list[Any],
                  start: pd.Timestamp, split: pd.Timestamp, end: pd.Timestamp) -> None:
    """Print per-strategy, per-sample performance in risk units."""
    print("Strategy               Sample  Trades  Win %  Avg R  Total R  Profit factor  Max DD R  Trades/week")
    for engine in engines:
        for sample, period_start, period_end in (("in", start, split), ("out", split, end)):
            selected = sorted((trade for trade in trades if trade["strategy"] == engine.strategy_name
                               and trade["sample"] == sample), key=lambda trade: trade["exit_time"])
            values = [trade["r"] for trade in selected]
            count = len(values)
            wins = sum(value > 0 for value in values)
            gross_profit = sum(value for value in values if value > 0)
            gross_loss = -sum(value for value in values if value < 0)
            profit_factor = f"{gross_profit / gross_loss:.2f}" if gross_loss else "inf" if gross_profit else "-"
            equity = peak = drawdown = 0.0
            for value in values:
                equity += value
                peak = max(peak, equity)
                drawdown = max(drawdown, peak - equity)
            weeks = (period_end - period_start).total_seconds() / (7 * 86400)
            print(f"{engine.strategy_name:22} {sample:6} {count:6} "
                  f"{100 * wins / count if count else 0:6.1f} {sum(values) / count if count else 0:6.2f} "
                  f"{sum(values):8.2f} {profit_factor:>14} {drawdown:9.2f} {count / weeks if weeks else 0:12.2f}")


def main() -> int:
    """Download data, run the replay, and write its trade results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", default="EUR_USD,GBP_USD")
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--oos-months", type=int, default=4)
    parser.add_argument("--secondary", default="none")
    parser.add_argument("--params")
    parser.add_argument("--from", dest="from_date")
    parser.add_argument("--to", dest="to_date")
    parser.add_argument("--funnel", action="store_true")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--spread-mult", type=float, default=1.0)
    parser.add_argument("--live-validation", action="store_true")
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    pairs = [pair.strip().upper() for pair in args.pairs.split(",")]
    if not pairs or any(not re.fullmatch(r"[A-Z]{3}_[A-Z]{3}", pair) for pair in pairs):
        parser.error("--pairs must contain comma-separated currency pairs such as EUR_USD")
    if len(set(pairs)) != len(pairs):
        parser.error("--pairs must not contain duplicates")
    if args.months <= 1 or not 0 < args.oos_months < args.months:
        parser.error("--months must exceed --oos-months, and both must be positive")
    secondary = [name.strip().lower() for name in args.secondary.split(",") if name.strip()]
    if secondary == ["none"]:
        secondary = []
    if any(name not in SECONDARIES for name in secondary):
        parser.error("--secondary must be a comma-separated list of breakout, breakout_v2, and range")
    if len(set(secondary)) != len(secondary):
        parser.error("--secondary must not contain duplicates")
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if not math.isfinite(args.spread_mult) or args.spread_mult < 0:
        parser.error("--spread-mult must be a finite non-negative number")
    if "/" in args.tag or "\\" in args.tag:
        parser.error("--tag must not contain path separators")
    try:
        params = _read_params(args.params)
        for name, value in params["config"].items():
            setattr(config, name, value)
        secondary_kwargs = _secondary_options(params["secondary"], secondary)
        engines = make_engines(secondary, params["primary"], secondary_kwargs)
        now = pd.Timestamp.now(tz="UTC").floor("15min")
        period_end = _date_bound(args.to_date, end=True) if args.to_date else now
        period_start = _date_bound(args.from_date) if args.from_date else period_end - pd.DateOffset(months=args.months)
        if period_start >= period_end:
            raise ValueError("--from must be earlier than --to")
        start = period_start
        end = period_end
        split = min(max(end - pd.DateOffset(months=args.oos_months), start), end)
        warmup_start = start - pd.Timedelta(days=10)
        trades: list[dict[str, Any]] = []
        funnel_totals: dict[str, int] = {}
        jobs: list[dict[str, Any]] = []
        for pair in pairs:
            print(f"Loading {pair} candles...", flush=True)
            candles = load_candles(pair, "M15", warmup_start, end)
            hourly = load_candles(pair, "H1", warmup_start, end)
            if candles.empty or hourly.empty:
                raise ValueError(f"No complete candle history for {pair}")
            jobs.append({
                "pair": pair, "candles": candles, "hourly": hourly, "secondary": secondary,
                "primary_kwargs": params["primary"], "secondary_kwargs": secondary_kwargs,
                "guard_kwargs": params["guards"], "validation_kwargs": params["validation"],
                "config_kwargs": params["config"], "split": split, "spread_mult": args.spread_mult,
                "live_validation": args.live_validation, "trade_start": start, "trade_end": end,
                "funnel": args.funnel,
            })
        if args.jobs == 1:
            results = map(_run_pair_job, jobs)
            for pair_trades, pair_funnel in results:
                trades.extend(pair_trades)
                for message, count in pair_funnel.items():
                    funnel_totals[message] = funnel_totals.get(message, 0) + count
        else:
            with ProcessPoolExecutor(max_workers=args.jobs) as executor:
                for pair_trades, pair_funnel in executor.map(_run_pair_job, jobs):
                    trades.extend(pair_trades)
                    for message, count in pair_funnel.items():
                        funnel_totals[message] = funnel_totals.get(message, 0) + count
        suffix = f"_{args.tag}" if args.tag else ""
        name = "+".join(secondary) if secondary else "none"
        path = Path("results") / f"{name}{suffix}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(trades, columns=RESULT_COLUMNS).sort_values("exit_time").to_csv(path, index=False)
        print_summary(trades, engines, start, split, end)
        summary = {"all": _summary_metrics(trades), "strategies": {}}
        for engine in engines:
            summary["strategies"][engine.strategy_name] = _summary_metrics(
                [trade for trade in trades if trade["strategy"] == engine.strategy_name]
            )
        summary_path = path.with_name(f"{path.stem}_summary.json")
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if args.funnel:
            print("\nNo-trade funnel (strategy: last log message)")
            for message, count in sorted(funnel_totals.items(), key=lambda item: (-item[1], item[0])):
                print(f"{count:8} {message}")
        print(f"Results: {path}")
        print(f"Summary: {summary_path}")
        return 0
    except Exception as exc:
        print(f"Backtest failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())