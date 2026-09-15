"""
pyTrade Position Validation Module

Provides position data parsing and multi-rule position validity checking to
automatically manage and close open positions when trend structures break,
volatility contracts, breakout integrity fails, time thresholds expire,
or market sessions approach close.

Supports strategy-specific validation pipelines for:
- EMA Trend Following Strategy
- Volatility Breakout Strategy
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import pyTrade_market_session as market


class Validation:
    """
    Position Validation Engine that checks open trade validity across
    technical indicators, breakout structure, trade duration, and session boundaries.
    """

    def __init__(
        self,
        strategy_type: str = "auto",
        max_trade_hours: float = 4.0,
        ema_low_len: int = 20,
        ema_high_len: int = 50,
        atr_len: int = 14,
        atr_multiplier: float = 2.0,
        stop_proximity_ratio: float = 0.3,
        momentum_loss_threshold: float = 0.20,
        enable_trend_check: bool = True,
        enable_time_check: bool = True,
        enable_session_check: bool = True,
        enable_breakout_checks: bool = True,
    ) -> None:
        """
        Initialize the Validation engine.

        :param strategy_type: Active strategy profile ('auto', 'trend_following', 'breakout', 'all')
        :param max_trade_hours: Maximum allowed open trade duration in hours before invalidation
        :param ema_low_len: Lookback period for fast EMA (default: 20)
        :param ema_high_len: Lookback period for slow / macro trend EMA (default: 50)
        :param atr_len: Lookback period for ATR (default: 14)
        :param atr_multiplier: Multiplier used for ATR stop calculations (default: 2.0)
        :param stop_proximity_ratio: Fraction of ATR for stop proximity warning/invalidation (default: 0.3)
        :param momentum_loss_threshold: Fraction drop in ATR from entry to invalidate (default: 0.20 / 20%)
        :param enable_trend_check: Enable trend structure checks
        :param enable_time_check: Enable trade age duration check (4 hours)
        :param enable_session_check: Enable session boundary / closing check
        :param enable_breakout_checks: Enable breakout-specific validation rules
        """
        self.strategy_type = strategy_type.lower()
        self.max_trade_hours = max_trade_hours
        self.ema_low_len = ema_low_len
        self.ema_high_len = ema_high_len
        self.atr_len = atr_len
        self.atr_multiplier = atr_multiplier
        self.stop_proximity_ratio = stop_proximity_ratio
        self.momentum_loss_threshold = momentum_loss_threshold

        self.enable_trend_check = enable_trend_check
        self.enable_time_check = enable_time_check
        self.enable_session_check = enable_session_check
        self.enable_breakout_checks = enable_breakout_checks

        self.logger = logging.getLogger("pyTrade.Validation")
        self.logger.info(
            "Validation initialized: strategy_type=%s, max_trade_hours=%.1f, EMA_Low=%d, EMA_High=%d, ATR=%d",
            self.strategy_type,
            self.max_trade_hours,
            self.ema_low_len,
            self.ema_high_len,
            self.atr_len,
        )

    def extract_position_data(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract normalized position details from an OANDA open position dictionary.

        :param position: OANDA open position dictionary
        :return: Normalized dictionary with instrument, direction, units, entry_price, tradeID
        """
        long_units = int(position.get("long", {}).get("units", 0))
        short_units = int(position.get("short", {}).get("units", 0))

        if long_units != 0:
            units = long_units
            trade_ids = position.get("long", {}).get("tradeIDs", [])
            trade_id = trade_ids[0] if trade_ids else None
            direction = "long"
            entry_price = float(position.get("long", {}).get("averagePrice", 0.0))
        else:
            units = short_units
            trade_ids = position.get("short", {}).get("tradeIDs", [])
            trade_id = trade_ids[0] if trade_ids else None
            direction = "short"
            entry_price = float(position.get("short", {}).get("averagePrice", 0.0))

        parsed = {
            "instrument": position.get("instrument", ""),
            "direction": direction,
            "units": units,
            "entry_price": entry_price,
            "tradeID": trade_id,
            "strategy": position.get("strategy", None),
        }

        self.logger.debug("extract_position_data: %s", parsed)
        return parsed

    def positions_data(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Alias for extract_position_data for backward compatibility.
        """
        return self.extract_position_data(position)

    # -------------------------------------------------------------------------
    # Universal Validation Rules (Time & Session)
    # -------------------------------------------------------------------------

    def check_time_invalidation(
        self,
        pos: Dict[str, Any],
        candle_time: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """
        Check if the open position has exceeded the maximum duration limit (e.g. 4 hours).

        :param pos: Position data containing 'trade_time'
        :param candle_time: Timestamp of the current candle (or None for UTC now)
        :return: Tuple of (is_valid, reason)
        """
        trade_time_str = pos.get("trade_time")
        if not trade_time_str:
            self.logger.warning("check_time_invalidation: Missing trade_time in pos dictionary")
            return True, "Trade time not available"

        try:
            entry_dt = datetime.fromisoformat(str(trade_time_str).replace("Z", "+00:00"))
            ref_time = candle_time if candle_time is not None else datetime.now(timezone.utc)

            # Ensure ref_time has timezone info
            if ref_time.tzinfo is None:
                ref_time = ref_time.replace(tzinfo=timezone.utc)

            trade_age = ref_time - entry_dt

            if trade_age > timedelta(hours=self.max_trade_hours):
                reason = f"Time-based invalidation (Trade age {trade_age} > {self.max_trade_hours} hours)"
                self.logger.debug("[INVALIDATION] %s", reason)
                return False, reason

        except Exception as e:
            self.logger.error("check_time_invalidation: Error parsing time: %s", str(e), exc_info=True)
            return True, "Time parsing error"

        return True, "Trade age valid"

    def check_session_invalidation(
        self,
        current_market: str,
        utc_now: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """
        Check if the current market session is closing soon.

        :param current_market: Market session identifier (e.g., 'london', 'new_york')
        :param utc_now: Current UTC datetime
        :return: Tuple of (is_valid, reason)
        """
        if not current_market:
            return True, "No active market specified"

        now = utc_now if utc_now is not None else datetime.now(timezone.utc)
        if market.is_market_closing(now, current_market):
            reason = f"Session boundary invalidation (Market '{current_market}' closing soon)"
            self.logger.debug("[INVALIDATION] %s", reason)
            return False, reason

        return True, "Session boundary valid"

    # -------------------------------------------------------------------------
    # EMA Trend Following Validation Rules
    # -------------------------------------------------------------------------

    def check_trend_invalidation(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
    ) -> Tuple[bool, str]:
        """
        Check if the EMA20/50 trend structure has flipped (EMA flip).

        - Long invalid if fast EMA < slow EMA
        - Short invalid if fast EMA > slow EMA

        :param pos: Normalized position data dictionary
        :param candle: Latest candle data Series containing EMA columns
        :return: Tuple of (is_valid, reason)
        """
        ema_low_col = f"EMA_{self.ema_low_len}"
        ema_high_col = f"EMA_{self.ema_high_len}"

        if ema_low_col not in candle or ema_high_col not in candle:
            self.logger.warning(
                "check_trend_invalidation: Missing indicator columns (%s, %s)",
                ema_low_col,
                ema_high_col,
            )
            return True, "Indicators unavailable for trend check"

        ema_low = float(candle[ema_low_col])
        ema_high = float(candle[ema_high_col])
        direction = pos.get("direction", "").lower()

        # Long position invalidation: trend flipped bearish
        if direction == "long" and ema_low < ema_high:
            reason = f"Trend invalidation (EMA Flip) - Long ({ema_low_col} < {ema_high_col})"
            self.logger.debug("[INVALIDATION] %s", reason)
            return False, reason

        # Short position invalidation: trend flipped bullish
        if direction == "short" and ema_low > ema_high:
            reason = f"Trend invalidation (EMA Flip) - Short ({ema_low_col} > {ema_high_col})"
            self.logger.debug("[INVALIDATION] %s", reason)
            return False, reason

        return True, "Trend valid"

    # -------------------------------------------------------------------------
    # Breakout Strategy Validation Rules
    # -------------------------------------------------------------------------

    def check_trend_continuation(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
    ) -> Tuple[bool, str]:
        """
        Trend-continuation check:
        - Invalidate long if price closes below EMA50
        - Invalidate short if price closes above EMA50

        :param pos: Normalized position data dictionary
        :param candle: Latest candle data Series
        :return: Tuple of (is_valid, reason)
        """
        ema_col = f"EMA_{self.ema_high_len}"
        if ema_col not in candle or pd.isna(candle[ema_col]) or "close" not in candle:
            return True, "Indicators unavailable for trend continuation check"

        close_price = float(candle["close"])
        ema_val = float(candle[ema_col])
        direction = pos.get("direction", "").lower()

        if direction == "long" and close_price < ema_val:
            reason = f"Trend-continuation invalidation: Long closed below {ema_col} (Close {close_price:.5f} < EMA {ema_val:.5f})"
            self.logger.debug("[INVALIDATION] %s", reason)
            return False, reason

        if direction == "short" and close_price > ema_val:
            reason = f"Trend-continuation invalidation: Short closed above {ema_col} (Close {close_price:.5f} > EMA {ema_val:.5f})"
            self.logger.debug("[INVALIDATION] %s", reason)
            return False, reason

        return True, "Trend continuation intact"

    def check_donchian_reentry(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
    ) -> Tuple[bool, str]:
        """
        Donchian re-entry check:
        - Invalidate long if price closes back below Donchian Upper
        - Invalidate short if price closes back above Donchian Lower

        :param pos: Normalized position data dictionary
        :param candle: Latest candle data Series
        :return: Tuple of (is_valid, reason)
        """
        direction = pos.get("direction", "").lower()
        close_price = float(candle.get("close", 0.0))

        if direction == "long":
            if "DC_Upper" in candle and not pd.isna(candle["DC_Upper"]):
                dc_upper = float(candle["DC_Upper"])
                if close_price < dc_upper:
                    reason = f"Donchian re-entry invalidation: Long closed back below DC_Upper ({close_price:.5f} < {dc_upper:.5f})"
                    self.logger.debug("[INVALIDATION] %s", reason)
                    return False, reason

        elif direction == "short":
            if "DC_Lower" in candle and not pd.isna(candle["DC_Lower"]):
                dc_lower = float(candle["DC_Lower"])
                if close_price > dc_lower:
                    reason = f"Donchian re-entry invalidation: Short closed back above DC_Lower ({close_price:.5f} > {dc_lower:.5f})"
                    self.logger.debug("[INVALIDATION] %s", reason)
                    return False, reason

        return True, "Donchian breakout boundary intact"

    def check_volatility_contraction(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
    ) -> Tuple[bool, str]:
        """
        Volatility contraction check:
        - Invalidate if ATR falls below ATR_SMA after entry (volatility collapsing)

        :param pos: Normalized position data dictionary
        :param candle: Latest candle data Series
        :return: Tuple of (is_valid, reason)
        """
        atr_col = f"ATR_{self.atr_len}"
        atr_sma_col = f"ATR_SMA_{self.atr_len}"

        if atr_col in candle and atr_sma_col in candle:
            if not pd.isna(candle[atr_col]) and not pd.isna(candle[atr_sma_col]):
                atr_val = float(candle[atr_col])
                atr_sma_val = float(candle[atr_sma_col])
                if atr_val < atr_sma_val:
                    reason = f"Volatility contraction invalidation: {atr_col} ({atr_val:.5f}) fell below {atr_sma_col} ({atr_sma_val:.5f})"
                    self.logger.debug("[INVALIDATION] %s", reason)
                    return False, reason

        return True, "Volatility expansion intact"

    def check_breakout_candle_integrity(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
        df: Optional[pd.DataFrame] = None,
    ) -> Tuple[bool, str]:
        """
        Breakout candle integrity check:
        - Invalidate if the candle immediately after entry engulfs the breakout candle.

        :param pos: Normalized position data dictionary
        :param candle: Current candle Series
        :param df: Candles DataFrame history
        :return: Tuple of (is_valid, reason)
        """
        if df is None or len(df) < 2:
            return True, "Insufficient candle history for breakout candle integrity check"

        direction = pos.get("direction", "").lower()
        curr_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]

        curr_open = float(curr_candle["open"])
        curr_close = float(curr_candle["close"])
        curr_high = float(curr_candle["high"])
        curr_low = float(curr_candle["low"])

        prev_open = float(prev_candle["open"])
        prev_close = float(prev_candle["close"])
        prev_high = float(prev_candle["high"])
        prev_low = float(prev_candle["low"])

        # Long trade: Check for bearish engulfing on post-breakout bar
        if direction == "long":
            prev_is_bullish = prev_close >= prev_open
            curr_is_bearish = curr_close < curr_open
            # Bearish engulfing: current opens at/above previous close and closes at/below previous open
            # or completely engulfs the previous high/low range
            is_engulfing = (
                curr_is_bearish
                and prev_is_bullish
                and curr_open >= prev_close
                and curr_close <= prev_open
            ) or (curr_is_bearish and curr_high >= prev_high and curr_close < prev_low)

            if is_engulfing:
                reason = "Breakout candle integrity invalidation: Bearish engulfing candle formed immediately after entry"
                self.logger.debug("[INVALIDATION] %s", reason)
                return False, reason

        # Short trade: Check for bullish engulfing on post-breakout bar
        elif direction == "short":
            prev_is_bearish = prev_close <= prev_open
            curr_is_bullish = curr_close > curr_open
            # Bullish engulfing: current opens at/below previous close and closes at/above previous open
            # or completely engulfs previous high/low range
            is_engulfing = (
                curr_is_bullish
                and prev_is_bearish
                and curr_open <= prev_close
                and curr_close >= prev_open
            ) or (curr_is_bullish and curr_low <= prev_low and curr_close > prev_high)

            if is_engulfing:
                reason = "Breakout candle integrity invalidation: Bullish engulfing candle formed immediately after entry"
                self.logger.debug("[INVALIDATION] %s", reason)
                return False, reason

        return True, "Breakout candle integrity confirmed"

    def check_stop_proximity(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
        df: Optional[pd.DataFrame] = None,
    ) -> Tuple[bool, str]:
        """
        Stop-loss proximity check:
        - Invalidate if price moves within 0.3 * ATR of the ATR stop loss level.

        :param pos: Normalized position data dictionary (with 'entry_price' or 'stop_loss')
        :param candle: Latest candle data Series
        :param df: Optional DataFrame for ATR lookup
        :return: Tuple of (is_valid, reason)
        """
        atr_col = f"ATR_{self.atr_len}"
        if atr_col not in candle or pd.isna(candle[atr_col]):
            return True, "ATR indicator unavailable for stop proximity check"

        atr_val = float(candle[atr_col])
        proximity_buffer = self.stop_proximity_ratio * atr_val
        direction = pos.get("direction", "").lower()
        entry_price = float(pos.get("entry_price", 0.0))

        if entry_price <= 0.0 and "close" in candle:
            entry_price = float(candle["close"])

        close_price = float(candle.get("close", entry_price))
        low_price = float(candle.get("low", close_price))
        high_price = float(candle.get("high", close_price))

        # Determine stop loss price level
        if "stop_loss" in pos and pos["stop_loss"] is not None:
            stop_price = float(pos["stop_loss"])
        else:
            sl_dist = max(atr_val * self.atr_multiplier, 0.05)
            stop_price = (entry_price - sl_dist) if direction == "long" else (entry_price + sl_dist)

        # Long: Invalidate if low or close is within 0.3 * ATR of stop price
        if direction == "long":
            dist_to_stop = low_price - stop_price
            if dist_to_stop <= proximity_buffer:
                reason = f"Stop-loss proximity invalidation: Long price ({low_price:.5f}) within {proximity_buffer:.5f} (0.3x ATR) of Stop ({stop_price:.5f})"
                self.logger.debug("[INVALIDATION] %s", reason)
                return False, reason

        # Short: Invalidate if high or close is within 0.3 * ATR of stop price
        elif direction == "short":
            dist_to_stop = stop_price - high_price
            if dist_to_stop <= proximity_buffer:
                reason = f"Stop-loss proximity invalidation: Short price ({high_price:.5f}) within {proximity_buffer:.5f} (0.3x ATR) of Stop ({stop_price:.5f})"
                self.logger.debug("[INVALIDATION] %s", reason)
                return False, reason

        return True, "Stop loss buffer safe"

    def check_failed_retest(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
        df: Optional[pd.DataFrame] = None,
    ) -> Tuple[bool, str]:
        """
        Failed retest check:
        - Invalidate if retest of breakout level fails (long closes below breakout level, short closes above).

        :param pos: Normalized position data dictionary
        :param candle: Latest candle data Series
        :param df: Optional DataFrame for candle history
        :return: Tuple of (is_valid, reason)
        """
        direction = pos.get("direction", "").lower()
        close_price = float(candle.get("close", 0.0))
        entry_price = float(pos.get("entry_price", 0.0))

        # Breakout level: user-tagged breakout_level or entry_price
        breakout_level = float(pos.get("breakout_level", entry_price))
        if breakout_level <= 0.0:
            return True, "Breakout level unknown"

        if direction == "long":
            # If price tested down near/below breakout level and closed below it
            if close_price < breakout_level:
                reason = f"Failed retest invalidation: Long closed below breakout level ({close_price:.5f} < {breakout_level:.5f})"
                self.logger.debug("[INVALIDATION] %s", reason)
                return False, reason

        elif direction == "short":
            # If price tested up near/above breakout level and closed above it
            if close_price > breakout_level:
                reason = f"Failed retest invalidation: Short closed above breakout level ({close_price:.5f} > {breakout_level:.5f})"
                self.logger.debug("[INVALIDATION] %s", reason)
                return False, reason

        return True, "Retest validation passed"

    def check_momentum_loss(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
        df: Optional[pd.DataFrame] = None,
    ) -> Tuple[bool, str]:
        """
        Momentum loss check:
        - Invalidate if ATR drops more than 20% from entry ATR.

        :param pos: Normalized position data dictionary (may contain 'entry_atr')
        :param candle: Latest candle data Series
        :param df: Candles DataFrame history to locate ATR at trade_time if entry_atr not in pos
        :return: Tuple of (is_valid, reason)
        """
        atr_col = f"ATR_{self.atr_len}"
        if atr_col not in candle or pd.isna(candle[atr_col]):
            return True, "ATR indicator unavailable for momentum loss check"

        curr_atr = float(candle[atr_col])

        # Resolve entry ATR: 1) from pos dict, 2) from historical candle at trade_time, 3) max ATR in df
        entry_atr = None
        if "entry_atr" in pos and pos["entry_atr"] is not None:
            entry_atr = float(pos["entry_atr"])
        elif df is not None and not df.empty and "trade_time" in pos and pos["trade_time"]:
            try:
                trade_dt = datetime.fromisoformat(str(pos["trade_time"]).replace("Z", "+00:00"))
                if "time" in df.columns:
                    # Find candle nearest or equal to trade_time
                    time_diffs = (pd.to_datetime(df["time"], utc=True) - trade_dt).abs()
                    nearest_idx = time_diffs.idxmin()
                    if atr_col in df.columns and not pd.isna(df.loc[nearest_idx, atr_col]):
                        entry_atr = float(df.loc[nearest_idx, atr_col])
            except Exception:
                pass

        if entry_atr is None and df is not None and atr_col in df.columns:
            # Fallback: compare against recent peak ATR in the series
            entry_atr = float(df[atr_col].tail(10).max())

        if entry_atr is not None and entry_atr > 0.0:
            atr_drop_pct = (entry_atr - curr_atr) / entry_atr
            if atr_drop_pct > self.momentum_loss_threshold:
                reason = (
                    f"Momentum loss invalidation: ATR dropped {atr_drop_pct*100:.1f}% from entry "
                    f"(Entry ATR: {entry_atr:.5f} -> Current ATR: {curr_atr:.5f}, threshold: {self.momentum_loss_threshold*100:.0f}%)"
                )
                self.logger.debug("[INVALIDATION] %s", reason)
                return False, reason

        return True, "Momentum intact"

    # -------------------------------------------------------------------------
    # Extensible Validation Hooks
    # -------------------------------------------------------------------------

    def check_pullback_failure(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
        df: Optional[pd.DataFrame] = None,
    ) -> Tuple[bool, str]:
        """Hook for future custom pullback failure invalidation logic."""
        return True, "Pullback check passed"

    def check_volatility_collapse(
        self,
        pos: Dict[str, Any],
        candle: pd.Series,
        df: Optional[pd.DataFrame] = None,
    ) -> Tuple[bool, str]:
        """Hook for future custom volatility collapse logic."""
        return True, "Volatility check passed"

    def check_custom_rules(
        self,
        pos: Dict[str, Any],
        df: pd.DataFrame,
        current_market: str,
    ) -> Tuple[bool, str]:
        """Hook for user-added validation rules."""
        return True, "Custom checks passed"

    # -------------------------------------------------------------------------
    # Strategy Determination Mechanism
    # -------------------------------------------------------------------------

    def resolve_strategy_type(
        self,
        pos: Dict[str, Any],
        df: pd.DataFrame,
        explicit_strategy: Optional[str] = None,
    ) -> str:
        """
        Determine which strategy validation pipeline to apply for the given position.

        Resolution hierarchy:
        1. Explicitly passed `strategy_type` argument to `validate_position`
        2. Position metadata tag `pos['strategy']` or `pos['strategy_type']`
        3. Configured `self.strategy_type` on this Validation instance
        4. Auto-detection from indicator columns present in DataFrame:
           - If 'DC_Upper' in df.columns -> 'breakout'
           - If 'EMA_20' in df.columns -> 'trend_following'
           - Else -> 'all'

        :param pos: Position data dictionary
        :param df: Candles DataFrame
        :param explicit_strategy: Strategy name passed to validate_position
        :return: Resolved strategy string ('breakout', 'trend_following', or 'all')
        """
        if explicit_strategy and explicit_strategy.lower() != "auto":
            return explicit_strategy.lower()

        pos_strat = pos.get("strategy") or pos.get("strategy_type")
        if pos_strat and str(pos_strat).lower() != "auto":
            return str(pos_strat).lower()

        if self.strategy_type != "auto":
            return self.strategy_type

        # Auto-detect based on available indicator columns in DataFrame
        cols = set(df.columns) if df is not None else set()
        if "DC_Upper" in cols or "DC_Lower" in cols:
            return "breakout"
        elif "EMA_20" in cols and "EMA_50" in cols:
            return "trend_following"

        return "all"

    # -------------------------------------------------------------------------
    # Main Validation Pipeline
    # -------------------------------------------------------------------------

    def validate_position(
        self,
        pos: Dict[str, Any],
        df: pd.DataFrame,
        current_market: str,
        strategy_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute all active validation rules for an open position based on its strategy type.

        :param pos: Normalized position dictionary (instrument, direction, trade_time, etc.)
        :param df: DataFrame with candle history and technical indicators
        :param current_market: Market session identifier
        :param strategy_type: Optional strategy override ('breakout', 'trend_following', 'all', 'auto')
        :return: Dictionary containing 'instrument', 'reason', 'validity'
        """
        instrument = pos.get("instrument", "UNKNOWN")

        if df is None or df.empty:
            self.logger.warning("validate_position: Empty DataFrame passed for %s", instrument)
            return {
                "instrument": instrument,
                "reason": "DataFrame empty",
                "validity": True,
            }

        candle = df.iloc[-1]
        candle_time = candle["time"] if "time" in candle else None
        active_strategy = self.resolve_strategy_type(pos, df, strategy_type)

        # ---------------------------------------------------------------------
        # 1. Universal Checks: Time Duration & Session Boundary
        # ---------------------------------------------------------------------
        if self.enable_time_check:
            is_valid, reason = self.check_time_invalidation(pos, candle_time)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

        if self.enable_session_check:
            is_valid, reason = self.check_session_invalidation(current_market)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

        # ---------------------------------------------------------------------
        # 2. Strategy-Specific Checks: Breakout vs Trend Following
        # ---------------------------------------------------------------------
        if active_strategy in ("breakout", "all") and self.enable_breakout_checks:
            # 2a. Trend-continuation check (Price vs EMA50)
            is_valid, reason = self.check_trend_continuation(pos, candle)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

            # 2b. Donchian re-entry check (Price vs DC_Upper / DC_Lower)
            is_valid, reason = self.check_donchian_reentry(pos, candle)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

            # 2c. Volatility contraction check (ATR < ATR_SMA)
            is_valid, reason = self.check_volatility_contraction(pos, candle)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

            # 2d. Breakout candle integrity check (Engulfing post-entry)
            is_valid, reason = self.check_breakout_candle_integrity(pos, candle, df)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

            # 2e. Stop-loss proximity check (Within 0.3 * ATR)
            is_valid, reason = self.check_stop_proximity(pos, candle, df)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

            # 2f. Failed retest check (Closes beyond breakout level)
            is_valid, reason = self.check_failed_retest(pos, candle, df)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

            # 2g. Momentum loss check (ATR drop > 20% from entry)
            is_valid, reason = self.check_momentum_loss(pos, candle, df)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

        if active_strategy in ("trend_following", "ema_trend", "all") and self.enable_trend_check:
            # EMA Trend Invalidation (EMA20 vs EMA50 flip)
            is_valid, reason = self.check_trend_invalidation(pos, candle)
            if not is_valid:
                return {"instrument": instrument, "reason": reason, "validity": False}

        # ---------------------------------------------------------------------
        # 3. Custom Extensible Hooks
        # ---------------------------------------------------------------------
        is_valid, reason = self.check_pullback_failure(pos, candle, df)
        if not is_valid:
            return {"instrument": instrument, "reason": reason, "validity": False}

        is_valid, reason = self.check_volatility_collapse(pos, candle, df)
        if not is_valid:
            return {"instrument": instrument, "reason": reason, "validity": False}

        is_valid, reason = self.check_custom_rules(pos, df, current_market)
        if not is_valid:
            return {"instrument": instrument, "reason": reason, "validity": False}

        # Position still valid
        self.logger.debug("[VALID] Position %s still valid under %s validation", instrument, active_strategy)
        return {
            "instrument": instrument,
            "reason": f"Position still valid ({active_strategy})",
            "validity": True,
        }


# Module-level instance and convenience functions

_default_validator = Validation()


def position_Validity_Check(
    pos: Dict[str, Any],
    df: pd.DataFrame,
    current_market: str,
    strategy_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Module-level function for validating position status against active rules.

    :param pos: Position data dictionary
    :param df: Candles DataFrame
    :param current_market: Active market session name
    :param strategy_type: Optional strategy override ('breakout', 'trend_following', 'all', 'auto')
    :return: Dict with instrument, reason, validity
    """
    return _default_validator.validate_position(pos, df, current_market, strategy_type=strategy_type)


def positions_data(position: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level function to extract normalized position data.

    :param position: OANDA open position dictionary
    :return: Normalized position dictionary
    """
    return _default_validator.extract_position_data(position)

