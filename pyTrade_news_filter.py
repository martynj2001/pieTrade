"""High-impact news blackout windows for pyTrade."""
import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

import config

logger = logging.getLogger("pyTrade.NewsFilter")

NEWS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_PATH = Path(__file__).with_name("news_cache.json")
REFETCH_SECONDS = 4 * 3600


class NewsFilter:
    """Blocks currencies around high-impact news events. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._raw: list = []
        self._loaded_at = 0.0  # monotonic time of last fetch attempt
        self._warned = False

    def _read_cache(self) -> list:
        """Return cached raw items, or [] if missing or unreadable."""
        try:
            with CACHE_PATH.open("r", encoding="utf-8") as cache_file:
                data = json.load(cache_file)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _refresh(self) -> None:
        """Refetch at most every 4 hours; fall back to the cache on any failure."""
        now = time.monotonic()
        if self._raw and now - self._loaded_at < REFETCH_SECONDS:
            return
        if not self._raw:
            self._raw = self._read_cache()
            if self._raw and CACHE_PATH.exists():
                age = time.time() - CACHE_PATH.stat().st_mtime
                if age < REFETCH_SECONDS:
                    self._loaded_at = now
                    return
        self._loaded_at = now
        try:
            response = requests.get(NEWS_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise ValueError("unexpected news feed format")
            self._raw = data
            with CACHE_PATH.open("w", encoding="utf-8") as cache_file:
                json.dump(data, cache_file)
        except (requests.RequestException, ValueError, OSError) as exc:
            logger.warning("News fetch failed (%s); using cached data", exc.__class__.__name__)
        if not self._raw and not self._warned:
            logger.warning("No news data available - news filter is not blocking anything")
            self._warned = True

    def _events(self) -> list[tuple[str, datetime]]:
        """Return (currency, utc time) for high-impact events."""
        self._refresh()
        events = []
        for item in self._raw:
            try:
                if item["impact"] != "High":
                    continue
                when = datetime.fromisoformat(item["date"])
                if when.tzinfo is None:
                    continue
                events.append((str(item["country"]).upper(), when.astimezone(timezone.utc)))
            except (KeyError, TypeError, ValueError):
                continue
        return events

    @staticmethod
    def _windows() -> tuple[timedelta, timedelta]:
        return (
            timedelta(minutes=getattr(config, "NEWS_BEFORE_MIN", 30)),
            timedelta(minutes=getattr(config, "NEWS_AFTER_MIN", 15)),
        )

    def blocked_during(self, start: datetime, end: datetime) -> set[str]:
        """Currencies whose blackout window overlaps [start, end]."""
        before, after = self._windows()
        with self._lock:
            events = self._events()
        return {
            currency for currency, when in events
            if when - before <= end and when + after >= start
        }

    def blocked_currencies(self, now: datetime) -> set[str]:
        """Currencies in a blackout window at `now`."""
        return self.blocked_during(now, now)

    def is_pair_blocked(self, instrument: str, now: datetime) -> bool:
        """True if either currency of a pair like 'EUR_USD' is blocked at `now`."""
        return bool(set(instrument.split("_")) & self.blocked_currencies(now))
