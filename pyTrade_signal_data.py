# Extraction of indicator values from the signal candle (no database access).

import logging
from typing import Any, Dict, Optional


def num(value: Any) -> Optional[float]:
    # Return a finite float, or None for missing/NaN values.
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def build_signal_data(
    strategy: Any,
    signal: str,
    price: Any,
    trade_guards: Any,
    logger: logging.Logger,
) -> Dict[str, Any]:
    # Collect the indicator values on the signal candle for the trade_signals table.
    row = price.iloc[-1]

    def col(name):
        return num(row[name]) if name in row.index else None

    atr_len = getattr(strategy, "atr_len", 14)
    ema_low_len = getattr(strategy, "ema_low_len", None)
    ema_high_len = getattr(strategy, "ema_high_len", None) or getattr(strategy, "ema_len", None)
    atr = col(f"ATR_{atr_len}")
    ema20 = col(f"EMA_{ema_low_len}") if ema_low_len else None
    ema50 = col(f"EMA_{ema_high_len}") if ema_high_len else None
    close = col("close")

    adx = None
    try:
        adx_series = trade_guards.calculate_adx(price)
        adx = num(adx_series.iloc[-1]) if adx_series is not None and len(adx_series) else None
    except Exception:
        logger.exception("Could not calculate ADX for signal data")

    # Distance of price from the macro EMA in ATRs (the measure the trend filter uses)
    trend_strength = None
    if None not in (close, ema50, atr) and atr:
        trend_strength = abs(close - ema50) / atr

    rejection = pullback = None
    if hasattr(strategy, "pullback_to_ema20") and ema20 is not None:
        try:
            pullback = bool(strategy.pullback_to_ema20(row))
            rejection = bool(
                strategy.rejection_candle_uptrend(row)
                if signal == "BUY"
                else strategy.rejection_candle_downtrend(row)
            )
        except Exception:
            logger.exception("Could not evaluate pullback/rejection for signal data")

    return {
        "ema20": ema20,
        "ema50": ema50,
        "atr14": atr,
        "adx": adx,
        "trend_strength": trend_strength,
        "rejection_candle": rejection,
        "pullback_detected": pullback,
        "close_price": close,
        "high_price": col("high"),
        "low_price": col("low"),
        "signal_timestamp": str(row["time"]) if "time" in row.index else None,
    }
