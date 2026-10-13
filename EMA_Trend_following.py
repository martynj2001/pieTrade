"""
EMA Trend Following Strategy Module (Legacy Compatibility Wrapper)

This module provides backward compatibility for legacy imports by delegating to:
- pyTrade_TrendFollowing_Strategy.TrendFollowingEngine
- pyTrade_orders (order creation & position sizing)
- pyTrade_validation.Validation (position validation)
"""

from typing import Any, Dict, Optional
import pandas as pd
from pyTrade_TrendFollowing_Strategy import TrendFollowingEngine
import pyTrade_orders as orders
import pyTrade_validation as validation

# Default engine and validation instances
_engine = TrendFollowingEngine()
_validator = validation.Validation()

# Forwarded order and validation functions
order_units = orders.order_units
order_data = orders.order_data
positions_data = validation.positions_data
position_Validity_Check = validation.position_Validity_Check


def get_indicators(df: pd.DataFrame, high_ind: int = 50, low_ind: int = 20) -> pd.DataFrame:
    """Calculate EMA and ATR indicators on the DataFrame."""
    engine = TrendFollowingEngine(ema_high_len=high_ind, ema_low_len=low_ind)
    return engine.add_indicators(df)


def has_clear_trend(row: pd.Series, k: float = 0.5) -> bool:
    """Check that price distance from 50 EMA exceeds ATR threshold."""
    return _engine.has_clear_trend(row)


def is_downtrend(row: pd.Series) -> bool:
    """Check if price is in downtrend below 50 EMA."""
    return _engine.is_downtrend(row)


def is_uptrend(row: pd.Series) -> bool:
    """Check if price is in uptrend above 50 EMA."""
    return _engine.is_uptrend(row)


def pullback_to_ema20(row: pd.Series) -> bool:
    """Check if price touched or is near 20 EMA."""
    return _engine.pullback_to_ema20(row)


def rejection_candle_uptrend(row: pd.Series, wick_factor: float = 1.5) -> bool:
    """Check for bullish rejection candle."""
    return _engine.rejection_candle_uptrend(row)


def rejection_candle_downtrend(row: pd.Series, wick_factor: float = 1.5) -> bool:
    """Check for bearish rejection candle."""
    return _engine.rejection_candle_downtrend(row)


def atr_stop_loss(trade_type: bool, row: pd.Series, atr: float, k: float = 1.5) -> float:
    """Calculate ATR-based stop loss level."""
    entry = float(row["high"] if trade_type else row["low"])
    signal = "BUY" if trade_type else "SELL"
    return _engine.calculate_stop(entry=entry, atr=atr, signal=signal)


def take_profit(entry_price: float, stop_loss: float, trade_type: bool) -> float:
    """Calculate 2R take profit level."""
    signal = "BUY" if trade_type else "SELL"
    return _engine.calculate_takeprofit(entry=entry_price, atr=0.0, signal=signal, stop=stop_loss)


def strat_5020_Pullback(df: pd.DataFrame, instrument: str) -> Optional[Dict[str, Any]]:
    """
    Execute 50/20 EMA Pullback strategy evaluation and return order data if triggered.
    """
    signal, entry, stop, tp = _engine.get_signal(df)
    if signal in ("BUY", "SELL") and entry is not None and stop is not None and tp is not None:
        return orders.create_order_from_signal(
            instrument=instrument,
            signal=signal,
            entry=entry,
            stop=stop,
            tp=tp,
        )
    return None


class TrendFollowing(TrendFollowingEngine):
    """
    Legacy wrapper for TrendFollowingEngine.
    """
    def __init__(self, df: Optional[pd.DataFrame] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.df = df
