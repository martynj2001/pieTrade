"""UTC opening-range breakout strategy."""

import logging
from typing import Optional, Tuple

import pandas as pd
import pandas_ta_classic as ta

import pyTrade_instruments


class OpeningRangeEngine:
    """Trade breaks of the current UTC day's opening range."""

    def __init__(
        self,
        range_start: int = 0,
        range_end: int = 7,
        entry_end: int = 10,
        exit_hour: int = 16,
        buffer_atr: float = 0.1,
        min_range_atr: float = 2.0,
        max_range_atr: float = 8.0,
        sl_mode: str = "mid",
        rr_ratio: float = 1.5,
        atr_len: int = 14,
        min_sl_dist: float = 0.05,
    ) -> None:
        if not 0 <= range_start < range_end <= 24:
            raise ValueError("range_start and range_end must satisfy 0 <= start < end <= 24")
        if not range_end <= entry_end <= 24 or not 0 <= exit_hour <= 23:
            raise ValueError("entry_end and exit_hour must be valid UTC hours")
        if sl_mode not in {"mid", "opposite"}:
            raise ValueError("sl_mode must be 'mid' or 'opposite'")
        self.range_start = range_start
        self.range_end = range_end
        self.entry_end = entry_end
        self.exit_hour = exit_hour
        self.buffer_atr = buffer_atr
        self.min_range_atr = min_range_atr
        self.max_range_atr = max_range_atr
        self.sl_mode = sl_mode
        self.rr_ratio = rr_ratio
        self.atr_len = atr_len
        self.min_sl_dist = min_sl_dist
        self.strategy_name = "Opening_Range"
        self.logger = logging.getLogger("pyTrade.OpeningRangeEngine")

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ATR and the completed UTC-day opening range."""
        if df is None or df.empty or not {"time", "high", "low", "close"}.issubset(df.columns):
            return df
        times = pd.to_datetime(df["time"], utc=True, errors="coerce")
        df["ATR_14"] = ta.atr(df["high"], df["low"], df["close"], length=self.atr_len)
        df["OR_High"] = float("nan")
        df["OR_Low"] = float("nan")
        hours = times.dt.hour
        days = times.dt.date
        for day in days.dropna().unique():
            day_mask = days == day
            range_mask = day_mask & (hours >= self.range_start) & (hours < self.range_end)
            if not range_mask.any():
                continue
            range_high = float(df.loc[range_mask, "high"].max())
            range_low = float(df.loc[range_mask, "low"].min())
            available = day_mask & (hours >= self.range_end)
            df.loc[available, "OR_High"] = range_high
            df.loc[available, "OR_Low"] = range_low
        return df

    def _signal(self, df: pd.DataFrame) -> str:
        if df is None or df.empty or not {"time", "open", "close", "ATR_14", "OR_High", "OR_Low"}.issubset(df.columns):
            return "NONE"
        times = pd.to_datetime(df["time"], utc=True, errors="coerce")
        current_time = times.iloc[-1]
        if pd.isna(current_time) or not self.range_end <= current_time.hour < self.entry_end:
            return "NONE"
        current = df.iloc[-1]
        if any(pd.isna(current[key]) for key in ("close", "ATR_14", "OR_High", "OR_Low")):
            return "NONE"
        atr = float(current["ATR_14"])
        if atr <= 0:
            return "NONE"
        range_high = float(current["OR_High"])
        range_low = float(current["OR_Low"])
        range_width = range_high - range_low
        if not self.min_range_atr * atr <= range_width <= self.max_range_atr * atr:
            return "NONE"

        prior_today = (times.dt.date == current_time.date()) & (times.dt.hour >= self.range_end) & (times < current_time)
        prior_closes = pd.to_numeric(df.loc[prior_today, "close"], errors="coerce")
        if ((prior_closes > range_high) | (prior_closes < range_low)).any():
            return "NONE"
        close = float(current["close"])
        buffer = self.buffer_atr * atr
        if close > range_high + buffer:
            return "BUY"
        if close < range_low - buffer:
            return "SELL"
        return "NONE"

    def get_signal(
        self, df: pd.DataFrame, instrument: Optional[str] = None
    ) -> Tuple[str, Optional[float], Optional[float], Optional[float]]:
        """Return a breakout signal with range-based risk levels."""
        if df is None or df.empty:
            return "NONE", None, None, None
        df = self.add_indicators(df)
        direction = self._signal(df)
        if direction == "NONE":
            return "NONE", None, None, None
        current = df.iloc[-1]
        entry = float(current["close"])
        range_high = float(current["OR_High"])
        range_low = float(current["OR_Low"])
        stop = (range_high + range_low) / 2 if self.sl_mode == "mid" else range_low if direction == "BUY" else range_high
        minimum = pyTrade_instruments.min_sl_dist(instrument) if instrument else self.min_sl_dist
        if direction == "BUY":
            stop = min(stop, entry - minimum)
            target = entry + self.rr_ratio * (entry - stop)
        else:
            stop = max(stop, entry + minimum)
            target = entry - self.rr_ratio * (stop - entry)
        return direction, entry, stop, target

    def manage(self, trade: dict, df: pd.DataFrame) -> Optional[str]:
        """Close at the UTC exit hour or after the entry day."""
        if df is None or df.empty or "time" not in df:
            return None
        latest = pd.to_datetime(df["time"].iloc[-1], utc=True, errors="coerce")
        entry = pd.to_datetime(trade.get("entry_time"), utc=True, errors="coerce")
        if pd.isna(latest) or pd.isna(entry):
            return None
        if latest.date() > entry.date() or latest.hour >= self.exit_hour:
            return "close"
        return None
