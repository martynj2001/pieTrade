"""Range-reversion strategy for quiet forex markets."""

from typing import Any, Optional, Tuple

import pandas as pd
import pandas_ta_classic as ta

import config
import pyTrade_instruments
from pyTrade_trade_guards import TradeGuards


class RangeReversionEngine:
    """Trade a return inside Bollinger Bands when trend strength is weak."""

    def __init__(self, adx_max: float | None = None,
                 rsi_level: float | None = getattr(config, "RANGE_RSI_OVERSOLD", 35.0),
                 bb_std: float | None = None, need_confirm_candle: bool = True,
                 h1_max_dist_atr: float | None = None) -> None:
        self.strategy_name = "Range_Reversion"
        self.guards = TradeGuards()
        self.adx_max = getattr(config, "RANGE_ADX_MAX", 20.0) if adx_max is None else adx_max
        self.rsi_level = rsi_level
        self.bb_std = getattr(config, "RANGE_BB_STD", 2.0) if bb_std is None else bb_std
        self.need_confirm_candle = need_confirm_candle
        self.h1_max_dist_atr = (
            getattr(config, "RANGE_H1_ATR_MULTIPLIER", 1.5)
            if h1_max_dist_atr is None else h1_max_dist_atr
        )

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Bands, RSI, ATR, EMA and ADX to candle data."""
        if df is None or df.empty or not {"open", "high", "low", "close"}.issubset(df.columns):
            return df
        bb_length = getattr(config, "RANGE_BB_LENGTH", 20)
        df["BB_Mid"] = df["close"].rolling(bb_length).mean()
        deviation = df["close"].rolling(bb_length).std(ddof=0) * self.bb_std
        df["BB_Lower"] = df["BB_Mid"] - deviation
        df["BB_Upper"] = df["BB_Mid"] + deviation
        df["RSI_14"] = ta.rsi(df["close"], length=getattr(config, "RANGE_RSI_LENGTH", 14))
        df["ATR_14"] = ta.atr(df["high"], df["low"], df["close"], length=getattr(config, "RANGE_ATR_LENGTH", 14))
        df["EMA_50"] = ta.ema(df["close"], length=getattr(config, "RANGE_EMA_LENGTH", 50))
        df["ADX_14"] = self.guards.calculate_adx(df, length=getattr(config, "RANGE_ADX_LENGTH", 14))
        return df

    def get_signal(
        self, df: pd.DataFrame, instrument: Optional[str] = None
    ) -> Tuple[str, Optional[float], Optional[float], Optional[float]]:
        """Return a qualified signal, signal-candle stop, and mid-band target."""
        if df is None or len(df) < 4:
            return "NONE", None, None, None
        df = self.add_indicators(df)
        required = {"time", "open", "high", "low", "close", "BB_Lower", "BB_Mid", "BB_Upper", "RSI_14", "ATR_14", "ADX_14"}
        if not required.issubset(df.columns):
            return "NONE", None, None, None
        previous, current, earlier = df.iloc[-2], df.iloc[-1], df.iloc[-4]
        timestamp = pd.to_datetime(current["time"], utc=True, errors="coerce")
        if pd.isna(timestamp) or (timestamp + pd.Timedelta(minutes=15)).hour in getattr(
            config, "RANGE_SKIP_HOURS", (7, 12, 13)
        ):
            return "NONE", None, None, None
        values = [current[name] for name in ("open", "high", "low", "close", "BB_Lower", "BB_Mid", "BB_Upper", "ATR_14", "ADX_14")]
        values += [previous["low"], previous["high"], previous["BB_Lower"], previous["BB_Upper"], earlier["ADX_14"]]
        if any(pd.isna(value) for value in values):
            return "NONE", None, None, None
        adx, atr = float(current["ADX_14"]), float(current["ATR_14"])
        if adx >= self.adx_max or adx > float(earlier["ADX_14"]) or atr <= 0:
            return "NONE", None, None, None

        entry = float(current["close"])
        rsi_values = [float(value) for value in (previous["RSI_14"], current["RSI_14"]) if not pd.isna(value)]
        buy_rsi_ok = self.rsi_level is None or any(value < self.rsi_level for value in rsi_values)
        sell_rsi_ok = self.rsi_level is None or any(value > 100 - self.rsi_level for value in rsi_values)
        if (previous["low"] <= previous["BB_Lower"] and entry > current["BB_Lower"]
                and (not self.need_confirm_candle or entry > current["open"]) and buy_rsi_ok):
            direction, sign, extreme = "BUY", 1, float(current["low"])
        elif (previous["high"] >= previous["BB_Upper"] and entry < current["BB_Upper"]
              and (not self.need_confirm_candle or entry < current["open"]) and sell_rsi_ok):
            direction, sign, extreme = "SELL", -1, float(current["high"])
        else:
            return "NONE", None, None, None

        minimum = pyTrade_instruments.min_sl_dist(instrument) if instrument else getattr(config, "RANGE_MIN_SL_DIST", 0.05)
        stop = extreme - sign * getattr(config, "RANGE_STOP_ATR", 0.5) * atr
        stop = min(stop, entry - minimum) if sign == 1 else max(stop, entry + minimum)
        target = float(current["BB_Mid"])
        if sign * (target - entry) < getattr(config, "RANGE_MIN_REWARD_R", 0.8) * abs(entry - stop):
            return "NONE", None, None, None
        return direction, entry, stop, target

    def manage(self, trade: dict[str, Any], df: pd.DataFrame) -> Optional[str]:
        """Close if the range becomes a trend or the trade times out."""
        if int(trade["bars_held"]) >= getattr(config, "RANGE_MAX_BARS", 8):
            return "close"
        if df is not None and not df.empty and "ADX_14" in df.columns:
            adx = df["ADX_14"].iloc[-1]
            if pd.notna(adx) and float(adx) > getattr(config, "RANGE_EXIT_ADX", 25.0):
                return "close"
        return None