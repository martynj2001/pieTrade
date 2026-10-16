"""
Volatility Breakout Strategy Engine (BreakoutEngine)

Strategy Logic:
1. Donchian Channels: Define the upper and lower breakout price levels over N periods.
2. Trend Filter: 50 EMA ensures trading strictly in the direction of the macro trend (price > EMA for BUY, price < EMA for SELL).
3. Volatility Expansion Filter: ATR(14) > ATR_SMA(14) confirms volatility expansion before entering breakouts.
4. Risk Management: ATR-based stop loss and risk-reward-based take profit targets.
"""

import logging
from typing import Optional, Tuple
import pandas as pd
import pandas_ta_classic as ta
import pyTrade_instruments


class BreakoutEngine:
    """
    Volatility Breakout Strategy Engine utilizing Donchian Channels,
    EMA trend filtering, and ATR volatility expansion filters.
    """

    def __init__(
        self,
        donchian_len: int = 20,
        ema_len: int = 50,
        atr_len: int = 14,
        atr_multiplier: float = 2.0,
        rr_ratio: float = 2.0,
        min_sl_dist: float = 0.05,
    ) -> None:
        """
        Initialize the BreakoutEngine with strategy parameters.

        :param donchian_len: Lookback period for Donchian Channels (default: 20)
        :param ema_len: Lookback period for trend filter EMA (default: 50)
        :param atr_len: Lookback period for ATR and ATR SMA (default: 14)
        :param atr_multiplier: Multiplier for ATR-based stop loss (default: 2.0)
        :param rr_ratio: Risk-to-reward ratio for take profit calculation (default: 2.0)
        :param min_sl_dist: Minimum stop-loss distance to avoid oversized position sizing (default: 0.05)
        """
        self.donchian_len = donchian_len
        self.ema_len = ema_len
        self.atr_len = atr_len
        self.atr_multiplier = atr_multiplier
        self.rr_ratio = rr_ratio
        self.min_sl_dist = min_sl_dist

        self.strategy_name = "Breakout"
        # Logger configured to integrate with pyTrade's logging hierarchy
        self.logger = logging.getLogger("pyTrade.BreakoutEngine")
        self.logger.info(
            "BreakoutEngine initialized: Donchian=%d, EMA=%d, ATR=%d, ATR_Mult=%.2f, RR=%.2f",
            self.donchian_len,
            self.ema_len,
            self.atr_len,
            self.atr_multiplier,
            self.rr_ratio,
        )

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate and append Donchian Channels, EMA, ATR, and ATR_SMA to the DataFrame.

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

        min_required_rows = max(self.donchian_len, self.ema_len, self.atr_len * 2) + 1
        if len(df) < min_required_rows:
            self.logger.warning(
                "add_indicators: DataFrame length (%d) is less than recommended minimum (%d)",
                len(df),
                min_required_rows,
            )

        try:
            # 1. Donchian Channel
            # Compute using shift(1) to avoid current-bar lookahead bias
            df["DC_Upper"] = df["high"].shift(1).rolling(window=self.donchian_len).max()
            df["DC_Lower"] = df["low"].shift(1).rolling(window=self.donchian_len).min()
            df["DC_Mid"] = (df["DC_Upper"] + df["DC_Lower"]) / 2.0

            # 2. EMA Trend Filter
            ema_col = f"EMA_{self.ema_len}"
            df[ema_col] = ta.ema(df["close"], length=self.ema_len)

            # 3. ATR Volatility Indicator
            atr_col = f"ATR_{self.atr_len}"
            df[atr_col] = ta.atr(df["high"], df["low"], df["close"], length=self.atr_len)

            # 4. ATR Moving Average (Volatility Expansion Filter)
            atr_sma_col = f"ATR_SMA_{self.atr_len}"
            df[atr_sma_col] = ta.sma(df[atr_col], length=self.atr_len)

            self.logger.debug(
                "add_indicators completed: Added DC_Upper, DC_Lower, %s, %s, %s",
                ema_col,
                atr_col,
                atr_sma_col,
            )
        except Exception as e:
            self.logger.error("add_indicators: Exception while computing indicators: %s", str(e), exc_info=True)

        return df

    def evaluate_breakout(self, df: pd.DataFrame) -> str:
        """
        Evaluate market conditions on the latest candle for breakout buy/sell signals.

        Conditions for BUY:
        - Price > Donchian Upper
        - Price > EMA_50 (Uptrend)
        - ATR > ATR_SMA (Volatility expanding)

        Conditions for SELL:
        - Price < Donchian Lower
        - Price < EMA_50 (Downtrend)
        - ATR > ATR_SMA (Volatility expanding)

        :param df: DataFrame with calculated indicators
        :return: 'BUY', 'SELL', or 'NONE'
        """
        if df is None or df.empty:
            self.logger.warning("evaluate_breakout: Empty DataFrame provided")
            return "NONE"

        last_row = df.iloc[-1]
        ema_col = f"EMA_{self.ema_len}"
        atr_col = f"ATR_{self.atr_len}"
        atr_sma_col = f"ATR_SMA_{self.atr_len}"

        required_cols = ["close", "DC_Upper", "DC_Lower", ema_col, atr_col, atr_sma_col]
        for col in required_cols:
            if col not in last_row or pd.isna(last_row[col]):
                self.logger.warning("evaluate_breakout: Column '%s' is missing or NaN in latest candle", col)
                return "NONE"

        close = float(last_row["close"])
        dc_upper = float(last_row["DC_Upper"])
        dc_lower = float(last_row["DC_Lower"])
        ema_val = float(last_row[ema_col])
        atr_val = float(last_row[atr_col])
        atr_sma_val = float(last_row[atr_sma_col])

        self.logger.debug(
            "Evaluating breakout: Close=%.5f, DC_Upper=%.5f, DC_Lower=%.5f, EMA=%.5f, ATR=%.5f, ATR_SMA=%.5f",
            close,
            dc_upper,
            dc_lower,
            ema_val,
            atr_val,
            atr_sma_val,
        )

        volatility_expanding = atr_val > atr_sma_val

        # Check BUY Breakout
        if close > dc_upper and close > ema_val and volatility_expanding:
            self.logger.info(
                "BUY signal confirmed: Close (%.5f) > DC_Upper (%.5f), Close > EMA (%.5f), ATR (%.5f) > ATR_SMA (%.5f)",
                close,
                dc_upper,
                ema_val,
                atr_val,
                atr_sma_val,
            )
            return "BUY"

        # Check SELL Breakout
        if close < dc_lower and close < ema_val and volatility_expanding:
            self.logger.info(
                "SELL signal confirmed: Close (%.5f) < DC_Lower (%.5f), Close < EMA (%.5f), ATR (%.5f) > ATR_SMA (%.5f)",
                close,
                dc_lower,
                ema_val,
                atr_val,
                atr_sma_val,
            )
            return "SELL"

        if not volatility_expanding:
            self.logger.debug("No trade: Volatility is compressing (ATR %.5f <= ATR_SMA %.5f)", atr_val, atr_sma_val)
        else:
            self.logger.debug("No breakout triggered on current candle")

        return "NONE"

    def calculate_stop(
        self,
        entry: float,
        atr: float,
        signal: str = "BUY",
        instrument: Optional[str] = None,
    ) -> float:
        """
        Calculate an ATR-based stop loss level.

        :param entry: Entry price
        :param atr: Current ATR value
        :param signal: 'BUY' or 'SELL'
        :param instrument: Optional instrument symbol for pair-specific minimum stop distance
        :return: Stop loss price level
        """
        minimum_sl_dist = (
            pyTrade_instruments.min_sl_dist(instrument)
            if instrument is not None
            else self.min_sl_dist
        )
        sl_distance = max(atr * self.atr_multiplier, minimum_sl_dist)

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
        instrument: Optional[str] = None,
    ) -> float:
        """
        Calculate take profit level based on risk-to-reward ratio or ATR multiple.

        :param entry: Entry price
        :param atr: Current ATR value
        :param signal: 'BUY' or 'SELL'
        :param stop: Optional stop loss price to calculate exact risk (R)
        :param instrument: Optional instrument symbol for pair-specific minimum stop distance
        :return: Take profit price level
        """
        if stop is not None:
            risk = abs(entry - stop)
        else:
            minimum_sl_dist = (
                pyTrade_instruments.min_sl_dist(instrument)
                if instrument is not None
                else self.min_sl_dist
            )
            risk = max(atr * self.atr_multiplier, minimum_sl_dist)

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
        self, df: pd.DataFrame, instrument: Optional[str] = None
    ) -> Tuple[str, Optional[float], Optional[float], Optional[float]]:
        """
        Main strategy entry point. Computes indicators, evaluates market conditions,
        and returns trading signal with entry, stop loss, and take profit levels.

        :param df: DataFrame containing OHLC candle data
        :param instrument: Optional instrument symbol for pair-specific risk levels
        :return: Tuple of (signal, entry, stop, tp)
                 signal: 'BUY', 'SELL', or 'NONE'
        """
        if df is None or df.empty:
            self.logger.error("get_signal: Empty candle DataFrame provided")
            return "NONE", None, None, None

        # 1. Calculate and append technical indicators
        df = self.add_indicators(df)

        # 2. Evaluate breakout logic
        signal = self.evaluate_breakout(df)

        if signal == "NONE":
            return "NONE", None, None, None

        # 3. Calculate entry, stop, and take profit levels
        last_row = df.iloc[-1]
        entry = float(last_row["close"])
        atr_col = f"ATR_{self.atr_len}"
        atr_val = float(last_row[atr_col]) if atr_col in last_row else 0.0

        stop = self.calculate_stop(
            entry=entry,
            atr=atr_val,
            signal=signal,
            instrument=instrument,
        )
        tp = self.calculate_takeprofit(
            entry=entry,
            atr=atr_val,
            signal=signal,
            stop=stop,
            instrument=instrument,
        )

        self.logger.info(
            "Trade Signal Generated: %s | Entry: %.5f | Stop Loss: %.5f | Take Profit: %.5f",
            signal,
            entry,
            stop,
            tp,
        )

        return signal, entry, stop, tp
