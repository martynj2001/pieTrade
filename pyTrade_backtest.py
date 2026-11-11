"""Replay the bot's strategies against historical OANDA candles."""

import math
import argparse
import importlib
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from oandapyV20 import API
from oandapyV20.contrib.factories import InstrumentsCandlesFactory

import config
import pyTrade_instruments
from pyTrade_TrendFollowing_Strategy import TrendFollowingEngine
from pyTrade_trade_guards import TradeGuards


SPREAD_PIPS: dict[str, float] = {}

SECONDARIES = {
    "breakout": ("pyTrade_Breakout_Strategy", "BreakoutEngine"),
    "breakout_v2": ("pyTrade_BreakoutV2_Strategy", "BreakoutV2Engine"),
    "range": ("pyTrade_RangeReversion_Strategy", "RangeReversionEngine"),
}
RESULT_COLUMNS = ["pair", "strategy", "direction", "entry_time", "exit_time", "r", "bars_held", "exit_reason", "sample"]


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


def make_engines(secondary: str) -> list[Any]:
    """Create the primary and the requested optional secondary engine."""
    engines: list[Any] = [TrendFollowingEngine()]
    if secondary != "none":
        module_name, class_name = SECONDARIES[secondary]
        try:
            module = importlib.import_module(module_name)
            engine_class = getattr(module, class_name)
        except (ModuleNotFoundError, AttributeError) as exc:
            raise ValueError(f"Secondary engine {secondary!r} is unavailable: expected {module_name}.{class_name}") from exc
        engines.append(engine_class())
    return engines

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
        return guards.validate_breakout(candles, hourly, float(candles[column].iloc[-1]), direction)
    if name == "Range_Reversion":
        return guards.validate_range(candles, hourly, direction)
    raise ValueError(f"No trade guard configured for strategy {name}")


def run_pair(pair: str, candles: pd.DataFrame, hourly: pd.DataFrame, engines: list[Any],
             guards: TradeGuards, split: pd.Timestamp) -> list[dict[str, Any]]:
    """Simulate one position at a time, using only candles available at each decision."""
    frames = [engine.add_indicators(candles.copy()) for engine in engines]
    hourly_close_times = hourly["time"] + pd.Timedelta(hours=1)
    half_spread = SPREAD_PIPS.get(pair, 1.2) * pyTrade_instruments.pip_size(pair) / 2
    trades: list[dict[str, Any]] = []
    position = None

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

        if index + 1 >= len(candles):
            break
        closed_at = candle["time"] + pd.Timedelta(minutes=15)
        h1_slice = hourly.iloc[:hourly_close_times.searchsorted(closed_at, side="right")]
        for engine_index, engine in enumerate(engines):
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
    return trades


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
    parser.add_argument("--secondary", choices=("none", "breakout", "breakout_v2", "range"), default="none")
    args = parser.parse_args()
    pairs = [pair.strip().upper() for pair in args.pairs.split(",")]
    if not pairs or any(not re.fullmatch(r"[A-Z]{3}_[A-Z]{3}", pair) for pair in pairs):
        parser.error("--pairs must contain comma-separated currency pairs such as EUR_USD")
    if len(set(pairs)) != len(pairs):
        parser.error("--pairs must not contain duplicates")
    if args.months <= 1 or not 0 < args.oos_months < args.months:
        parser.error("--months must exceed --oos-months, and both must be positive")
    try:
        engines = make_engines(args.secondary)
        end = pd.Timestamp.now(tz="UTC").floor("15min")
        start = end - pd.DateOffset(months=args.months)
        split = end - pd.DateOffset(months=args.oos_months)
        trades: list[dict[str, Any]] = []
        for pair in pairs:
            print(f"Loading {pair} candles...", flush=True)
            candles = load_candles(pair, "M15", start, end)
            hourly = load_candles(pair, "H1", start, end)
            if candles.empty or hourly.empty:
                raise ValueError(f"No complete candle history for {pair}")
            trades.extend(run_pair(pair, candles, hourly, engines, TradeGuards(), split))
        path = Path("results") / f"{args.secondary}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(trades, columns=RESULT_COLUMNS).sort_values("exit_time").to_csv(path, index=False)
        print_summary(trades, engines, start, split, end)
        print(f"Results: {path}")
        return 0
    except Exception as exc:
        print(f"Backtest failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())