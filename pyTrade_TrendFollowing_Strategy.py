"""
EMA Trend Following Pullback Strategy Engine (TrendFollowingEngine)

Strategy Logic:
1. Macro Trend: 50 EMA defines overall trend direction (Price > EMA_50 = Uptrend, Price < EMA_50 = Downtrend).
2. Trend Strength: Distance between Price and EMA_50 must exceed k * ATR_14 to filter out choppy, flat markets.
3. Pullback Entry: Price retraces back to touch or close near the 20 EMA.
4. Rejection Candle: A candlestick with a long wick in the direction of the pullback rejection and strong close.
5. Risk Management: ATR-based stop loss and fixed Risk-to-Reward (2R) take profit targets.
"""

import logging
from typing import Optional, Tuple
import pandas as pd
import pandas_ta_classic as ta


class TrendFollowingEngine:
    """
    EMA 20/50 Pullback Trend Following Strategy Engine.
    """

    def __init__(
        self,
        ema_high_len: int = 50,
        ema_low_len: int = 20,
        atr_len: int = 14,
        atr_multiplier: float = 1.5,
        rr_ratio: float = 1.0, # was 2.0, lower to 1.0
        min_sl_dist: float = 0.05,
        trend_filter_k: float = 0.5,
        pullback_tolerance_k: float = 0.25,
        wick_factor: float = 1.5,
    ) -> None:
        """
        Initialize the TrendFollowingEngine with strategy parameters.

        :param ema_high_len: Lookback period for macro trend EMA (default: 50)
        :param ema_low_len: Lookback period for pullback EMA (default: 20)
        :param atr_len: Lookback period for ATR (default: 14)
        :param atr_multiplier: Multiplier for ATR-based stop loss (default: 1.5)
        :param rr_ratio: Risk-to-reward ratio for take profit (default: 1.0)
        :param min_sl_dist: Minimum stop loss distance in price units (default: 0.05)
        :param trend_filter_k: Multiplier for minimum price-to-EMA50 distance in ATRs (default: 0.5)
        :param pullback_tolerance_k: Multiplier for EMA20 proximity in ATRs (default: 0.25)
        :param wick_factor: Minimum ratio of wick to body for rejection candle (default: 1.5)
        """
        self.ema_high_len = ema_high_len
        self.ema_low_len = ema_low_len
        self.atr_len = atr_len
        self.atr_multiplier = atr_multiplier
        self.rr_ratio = rr_ratio
        self.min_sl_dist = min_sl_dist
        self.trend_filter_k = trend_filter_k
        self.pullback_tolerance_k = pullback_tolerance_k
        self.wick_factor = wick_factor

        self.strategy_name = "EMA_TrendFollowing"

        self.logger = logging.getLogger("pyTrade.TrendFollowingEngine")
        self.logger.info(
            "TrendFollowingEngine initialized: EMA_High=%d, EMA_Low=%d, ATR=%d, ATR_Mult=%.2f, RR=%.2f",
            self.ema_high_len,
            self.ema_low_len,
            self.atr_len,
            self.atr_multiplier,
            self.rr_ratio,
        )

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate and append EMA_20, EMA_50, and ATR_14 to the DataFrame.

        :param df: DataFrame containing OHLC candle data ('open', 'high', 'low', 'close')
        :return: DataFrame enriched with technical indicator columns
        """
        if df is None or df.empty:
            self.logger.error("add_indicators: Received empty or None DataFrame")
            return df

        required_cols = {"open", "high", "low", "close"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            self.logger.error("add_indicators: Missing required columns in DataFrame: %s", missing)
            return df

        min_required_rows = max(self.ema_high_len, self.ema_low_len, self.atr_len) + 1
        if len(df) < min_required_rows:
            self.logger.warning(
                "add_indicators: DataFrame length (%d) is less than recommended minimum (%d)",
                len(df),
                min_required_rows,
            )

        try:
            ema_low_col = f"EMA_{self.ema_low_len}"
            ema_high_col = f"EMA_{self.ema_high_len}"
            atr_col = f"ATR_{self.atr_len}"

            df[ema_low_col] = ta.ema(df["close"], length=self.ema_low_len)
            df[ema_high_col] = ta.ema(df["close"], length=self.ema_high_len)
            df[atr_col] = ta.atr(df["high"], df["low"], df["close"], length=self.atr_len)

            self.logger.debug(
                "add_indicators completed: Added %s, %s, %s",
                ema_low_col,
                ema_high_col,
                atr_col,
            )
        except Exception as e:
            self.logger.error(
                "add_indicators: Exception while computing indicators: %s",
                str(e),
                exc_info=True,
            )

        return df

    def is_uptrend(self, row: pd.Series) -> bool:
        """Check if price is above the macro trend EMA."""
        ema_high_col = f"EMA_{self.ema_high_len}"
        return float(row["close"]) > float(row[ema_high_col])

    def is_downtrend(self, row: pd.Series) -> bool:
        """Check if price is below the macro trend EMA."""
        ema_high_col = f"EMA_{self.ema_high_len}"
        return float(row["close"]) < float(row[ema_high_col])

    def has_clear_trend(self, row: pd.Series) -> bool:
        """
        Verify that price distance from macro EMA exceeds ATR threshold to avoid flat markets.
        """
        ema_high_col = f"EMA_{self.ema_high_len}"
        atr_col = f"ATR_{self.atr_len}"
        distance = abs(float(row["close"]) - float(row[ema_high_col]))
        threshold = self.trend_filter_k * float(row[atr_col])
        return distance > threshold

    def pullback_to_ema20(self, row: pd.Series) -> bool:
        """
        Check if candle touched or closed near the 20 EMA pullback level.
        """
        ema_low_col = f"EMA_{self.ema_low_len}"
        atr_col = f"ATR_{self.atr_len}"

        ema_low = float(row[ema_low_col])
        atr_val = float(row[atr_col])
        tolerance = self.pullback_tolerance_k * atr_val

        # Candle touched the 20 EMA
        touched = float(row["low"]) <= ema_low <= float(row["high"])

        # Candle closed near the 20 EMA
        near = abs(float(row["close"]) - ema_low) <= tolerance

        return touched or near

    def rejection_candle_uptrend(self, row: pd.Series) -> bool:
        """
        Check for a bullish rejection candle (strong close, long lower wick).
        """
        close_p = float(row["close"])
        open_p = float(row["open"])
        low_p = float(row["low"])

        body = abs(close_p - open_p)
        lower_wick = close_p - low_p
        return close_p > open_p and lower_wick >= (self.wick_factor * body)

    def rejection_candle_downtrend(self, row: pd.Series) -> bool:
        """
        Check for a bearish rejection candle (weak close, long upper wick).
        """
        close_p = float(row["close"])
        open_p = float(row["open"])
        high_p = float(row["high"])

        body = abs(close_p - open_p)
        upper_wick = high_p - close_p
        return close_p < open_p and upper_wick >= (self.wick_factor * body)

    def evaluate_trend_pullback(self, df: pd.DataFrame) -> str:
        """
        Evaluate market conditions on the latest candle for trend-following pullback signals.

        :param df: DataFrame enriched with technical indicators
        :return: 'BUY', 'SELL', or 'NONE'
        """
        if df is None or df.empty:
            self.logger.warning("evaluate_trend_pullback: Empty DataFrame provided")
            return "NONE"

        last_row = df.iloc[-1]
        ema_low_col = f"EMA_{self.ema_low_len}"
        ema_high_col = f"EMA_{self.ema_high_len}"
        atr_col = f"ATR_{self.atr_len}"

        required_cols = ["open", "high", "low", "close", ema_low_col, ema_high_col, atr_col]
        for col in required_cols:
            if col not in last_row or pd.isna(last_row[col]):
                self.logger.warning("evaluate_trend_pullback: Column '%s' missing or NaN in latest candle", col)
                return "NONE"

        # Check Long / BUY setup
        if self.is_uptrend(last_row) and self.has_clear_trend(last_row) and self.pullback_to_ema20(last_row):
            if self.rejection_candle_uptrend(last_row):
                self.logger.info(
                    "BUY signal confirmed: Uptrend (Close > %s), Clear Trend, Pullback to %s, Bullish Rejection",
                    ema_high_col,
                    ema_low_col,
                )
                return "BUY"

        # Check Short / SELL setup
        if self.is_downtrend(last_row) and self.has_clear_trend(last_row) and self.pullback_to_ema20(last_row):
            if self.rejection_candle_downtrend(last_row):
                self.logger.info(
                    "SELL signal confirmed: Downtrend (Close < %s), Clear Trend, Pullback to %s, Bearish Rejection",
                    ema_high_col,
                    ema_low_col,
                )
                return "SELL"

        self.logger.debug("No pullback trend signal triggered on current candle")
        return "NONE"

    def calculate_stop(self, entry: float, atr: float, signal: str = "BUY") -> float:
        """
        Calculate ATR-based stop loss level.

        :param entry: Entry price
        :param atr: ATR value
        :param signal: 'BUY' or 'SELL'
        :return: Stop loss price
        """
        sl_distance = max(atr * self.atr_multiplier, self.min_sl_dist)

        if signal.upper() == "BUY":
            stop_price = entry - sl_distance
        else:
            stop_price = entry + sl_distance

        self.logger.debug(
            "calculate_stop: Signal=%s, Entry=%.5f, ATR=%.5f, SL_Dist=%.5f -> Stop=%.5f",
            signal,
            entry,
            atr,
            sl_distance,
            stop_price,
        )
        return stop_price

    def calculate_takeprofit(
        self,
        entry: float,
        atr: float,
        signal: str = "BUY",
        stop: Optional[float] = None,
    ) -> float:
        """
        Calculate take profit level based on risk-to-reward ratio.

        :param entry: Entry price
        :param atr: ATR value
        :param signal: 'BUY' or 'SELL'
        :param stop: Optional stop loss price to calculate exact risk
        :return: Take profit price level
        """
        if stop is not None:
            risk = abs(entry - stop)
        else:
            risk = max(atr * self.atr_multiplier, self.min_sl_dist)

        tp_distance = risk * self.rr_ratio

        if signal.upper() == "BUY":
            tp_price = entry + tp_distance
        else:
            tp_price = entry - tp_distance

        self.logger.debug(
            "calculate_takeprofit: Signal=%s, Entry=%.5f, Risk=%.5f, RR=%.2f -> TP=%.5f",
            signal,
            entry,
            risk,
            self.rr_ratio,
            tp_price,
        )
        return tp_price

    def get_signal(
        self, df: pd.DataFrame
    ) -> Tuple[str, Optional[float], Optional[float], Optional[float]]:
        """
        Main strategy entry point. Computes indicators, evaluates pullback conditions,
        and returns trading signal with entry, stop loss, and take profit levels.

        :param df: DataFrame containing OHLC candle data
        :return: Tuple of (signal, entry, stop, tp)
                 signal: 'BUY', 'SELL', or 'NONE'
        """
        if df is None or df.empty:
            self.logger.error("get_signal: Empty candle DataFrame provided")
            return "NONE", None, None, None

        # 1. Calculate and append technical indicators
        df = self.add_indicators(df)

        # 2. Evaluate pullback logic
        signal = self.evaluate_trend_pullback(df)

        if signal == "NONE":
            return "NONE", None, None, None

        # 3. Calculate entry, stop, and take profit levels
        last_row = df.iloc[-1]
        entry = float(last_row["close"])
        atr_col = f"ATR_{self.atr_len}"
        atr_val = float(last_row[atr_col]) if atr_col in last_row else 0.0

        stop = self.calculate_stop(entry=entry, atr=atr_val, signal=signal)
        tp = self.calculate_takeprofit(entry=entry, atr=atr_val, signal=signal, stop=stop)

        self.logger.info(
            "Trend Signal Generated: %s | Entry: %.5f | Stop Loss: %.5f | Take Profit: %.5f",
            signal,
            entry,
            stop,
            tp,
        )

        return signal, entry, stop, tp
