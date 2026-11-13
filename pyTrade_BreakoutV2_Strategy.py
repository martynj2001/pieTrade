"""Squeeze-filtered breakout strategy with early-exit management."""

from typing import Any, Optional, Tuple

import pandas as pd

import config
import pyTrade_instruments
from pyTrade_Breakout_Strategy import BreakoutEngine
from pyTrade_trade_guards import TradeGuards


class BreakoutV2Engine(BreakoutEngine):
    """Trade strong breakouts from a narrow prior Donchian channel."""

    def __init__(self, squeeze_pct: float | None = None, hours: list[int] | tuple[int, ...] | None = None,
                 max_ema_dist_atr: float | None = None, rr_ratio: float | None = None,
                 adx_mode: str = "threshold", manage_exits: bool = True,
                 require_h1_trend: bool = True) -> None:
        effective_rr = getattr(config, "BO_RR", 1.5) if rr_ratio is None else rr_ratio
        super().__init__(rr_ratio=effective_rr)
        self.strategy_name = "Breakout_V2"
        self.squeeze_pct = getattr(config, "BO_SQUEEZE_PCT", 0.3) if squeeze_pct is None else squeeze_pct
        self.hours = tuple(getattr(config, "BO_HOURS", (7, 8, 9, 12, 13, 14))) if hours is None else tuple(hours)
        self.max_ema_dist_atr = (
            getattr(config, "BO_MAX_EMA_DISTANCE_ATR", 3.0)
            if max_ema_dist_atr is None else max_ema_dist_atr
        )
        self.adx_mode = adx_mode.lower()
        if self.adx_mode not in {"threshold", "rising"}:
            raise ValueError("adx_mode must be 'threshold' or 'rising'")
        self.adx_calculator = TradeGuards()
        self.manage_exits = manage_exits
        self.require_h1_trend = require_h1_trend

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add the prior-channel width and its rolling squeeze threshold."""
        df = super().add_indicators(df)
        if df is not None and {"DC_Upper", "DC_Lower"}.issubset(df.columns):
            df["DC_Width"] = df["DC_Upper"] - df["DC_Lower"]
            window = getattr(config, "BO_SQUEEZE_WINDOW", 100)
            df["DC_Squeeze"] = df["DC_Width"].rolling(window, min_periods=window).quantile(
                self.squeeze_pct
            )
        return df

    def evaluate_breakout(self, df: pd.DataFrame) -> str:
        """Return a direction only when every V2 entry filter passes."""
        if df is None or df.empty:
            return "NONE"
        row = df.iloc[-1]
        required = ["time", "open", "high", "low", "close", "DC_Upper", "DC_Lower",
                    "DC_Width", "DC_Squeeze", f"EMA_{self.ema_len}", f"ATR_{self.atr_len}"]
        if any(column not in row or pd.isna(row[column]) for column in required):
            return "NONE"
        timestamp = pd.to_datetime(row["time"], utc=True, errors="coerce")
        if pd.isna(timestamp) or (timestamp + pd.Timedelta(minutes=15)).hour not in self.hours:
            return "NONE"

        open_price, high, low, close = (float(row[column]) for column in ("open", "high", "low", "close"))
        atr, ema = float(row[f"ATR_{self.atr_len}"]), float(row[f"EMA_{self.ema_len}"])
        candle_range = high - low
        if (atr <= 0 or candle_range <= 0 or float(row["DC_Width"]) > float(row["DC_Squeeze"])
                or abs(close - open_price) < getattr(config, "BO_MIN_BODY_RATIO", 0.5) * candle_range
                or candle_range > getattr(config, "BO_MAX_RANGE_ATR", 2.0) * atr
                or abs(close - ema) > self.max_ema_dist_atr * atr):
            return "NONE"
        if self.adx_mode == "rising":
            adx = self.adx_calculator.calculate_adx(df)
            if len(adx) < 4 or pd.isna(adx.iloc[-1]) or pd.isna(adx.iloc[-4]) or adx.iloc[-1] <= adx.iloc[-4]:
                return "NONE"

        margin = getattr(config, "BO_MIN_BREAKOUT_ATR", 0.1) * atr
        if close >= float(row["DC_Upper"]) + margin:
            return "BUY"
        if close <= float(row["DC_Lower"]) - margin:
            return "SELL"
        return "NONE"

    def get_signal(
        self, df: pd.DataFrame, instrument: Optional[str] = None
    ) -> Tuple[str, Optional[float], Optional[float], Optional[float]]:
        """Return the breakout signal with its level-based stop and target."""
        if df is None or df.empty:
            return "NONE", None, None, None
        df = self.add_indicators(df)
        direction = self.evaluate_breakout(df)
        if direction == "NONE":
            return "NONE", None, None, None
        row = df.iloc[-1]
        entry = float(row["close"])
        atr = float(row[f"ATR_{self.atr_len}"])
        sign = 1 if direction == "BUY" else -1
        level = float(row["DC_Upper"] if direction == "BUY" else row["DC_Lower"])
        minimum = pyTrade_instruments.min_sl_dist(instrument) if instrument else self.min_sl_dist
        stop = level - sign * getattr(config, "BO_STOP_ATR", 0.5) * atr
        stop = min(stop, entry - minimum) if direction == "BUY" else max(stop, entry + minimum)
        target = entry + sign * self.rr_ratio * abs(entry - stop)
        return direction, entry, stop, target

    def manage(self, trade: dict[str, Any], df: pd.DataFrame) -> Optional[str]:
        """Close failed breakouts or trades that have not moved sufficiently."""
        bars = int(trade["bars_held"])
        if bars <= 0 or df is None or len(df) < bars + 1:
            return None
        direction = trade["direction"]
        signal_row = df.iloc[-bars - 1]
        level = float(signal_row["DC_Upper"] if direction == "BUY" else signal_row["DC_Lower"])
        close = float(df.iloc[-1]["close"])
        if bars <= getattr(config, "BO_FAILED_BREAKOUT_BARS", 4) and (
            close < level if direction == "BUY" else close > level
        ):
            return "close"
        if bars >= getattr(config, "BO_TIME_STOP_BARS", 6):
            held = df.iloc[-bars:]
            entry = float(trade["entry_price"])
            best_move = float(held["high"].max()) - entry if direction == "BUY" else entry - float(held["low"].min())
            if best_move < getattr(config, "BO_MIN_MOVE_R", 0.5) * float(trade["risk"]):
                return "close"
        return None