"""Measure recent average bid/ask spreads from completed OANDA M15 candles."""

import argparse
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

from oandapyV20 import API
from oandapyV20.contrib.factories import InstrumentsCandlesFactory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
import pyTrade_instruments


BLOCKS = ((0, 7, "00-06"), (7, 16, "07-15"), (16, 22, "16-21"), (22, 24, "22-23"))


def _percentile(values: list[float], percentile: float) -> float:
    """Return a linearly interpolated percentile."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot calculate a percentile without spread samples")
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _fetch_spreads(client: Any, pair: str, start: datetime, end: datetime) -> list[tuple[int, float]]:
    params = {
        "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "granularity": "M15",
        "price": "BA",
        "count": 5000,
    }
    pip_size = pyTrade_instruments.pip_size(pair)
    samples = []
    for request in InstrumentsCandlesFactory(instrument=pair, params=params):
        response = client.request(request)
        for candle in response.get("candles", []):
            if not candle.get("complete"):
                continue
            try:
                timestamp = datetime.fromisoformat(candle["time"].replace("Z", "+00:00"))
                bid_close = float(candle["bid"]["c"])
                ask_close = float(candle["ask"]["c"])
            except (KeyError, TypeError, ValueError):
                continue
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            timestamp = timestamp.astimezone(timezone.utc)
            samples.append((timestamp.hour, (ask_close - bid_close) / pip_size))
    return samples


def _format(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", default="EUR_USD,GBP_USD")
    args = parser.parse_args()
    pairs = [pair.strip().upper() for pair in args.pairs.split(",") if pair.strip()]
    if not pairs or any(not re.fullmatch(r"[A-Z]{3}_[A-Z]{3}", pair) for pair in pairs):
        parser.error("--pairs must contain comma-separated currency pairs such as EUR_USD")
    if len(set(pairs)) != len(pairs):
        parser.error("--pairs must not contain duplicates")

    token = getattr(config, "OANDA_API_KEY", "").strip()
    if not token:
        print("OANDA_API_KEY is required to download candles", file=sys.stderr)
        return 1
    client = API(access_token=token, environment=getattr(config, "OANDA_ENVIRON", "practice"))
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    spread_map = {}

    try:
        for pair in pairs:
            samples = _fetch_spreads(client, pair, start, end)
            if not samples:
                raise ValueError(f"No completed BA M15 candles returned for {pair}")
            values = [spread for _, spread in samples]
            pair_mean = mean(values)
            spread_map[pair] = round(pair_mean, 1)
            print(f"{pair} ({len(values)} candles)")
            print(f"  Mean: {_format(pair_mean)} pips")
            print(f"  Median: {_format(median(values))} pips")
            print(f"  90th percentile: {_format(_percentile(values, 0.9))} pips")
            print("  Mean by UTC block:")
            for first_hour, end_hour, label in BLOCKS:
                block = [spread for hour, spread in samples if first_hour <= hour < end_hour]
                print(f"    {label}: {_format(mean(block) if block else None)} pips")
        print("\nReady-to-paste spread setting:")
        print(f"SPREAD_PIPS = {spread_map!r}")
        return 0
    except Exception as exc:
        print(f"Spread check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
