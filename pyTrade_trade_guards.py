"""Central qualification checks for pyTrade entry signals."""

import logging
from typing import Optional

import pandas as pd


class TradeGuards:
    """Validate strategy signals against M15 strength and H1 trend."""

    def __init__(self, adx_threshold: float = 24.0) -> None:
        """Initialize guards.

        Args:
            adx_threshold: Minimum M15 ADX required to allow an entry.
        """
        self.adx_threshold = adx_threshold
        self.logger = logging.getLogger("Trade-Guard")

    def calculate_adx(self, df: pd.DataFrame, length: int = 14) -> pd.Series:
        """Calculate Wilder-style ADX from OHLC candles.

        Args:
            df: Candle DataFrame containing high, low, and close columns.
            length: ADX smoothing length.

        Returns:
            A pandas Series containing ADX values, aligned to ``df``.

        Raises:
            ValueError: If the input columns, data, or length are invalid.
        """
        if not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError("ADX input must be a non-empty pandas DataFrame")
        if length < 1:
            raise ValueError("ADX length must be a positive integer")

        required = {"high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"ADX input is missing required columns: {sorted(missing)}"
            )

        try:
            high = pd.to_numeric(df["high"], errors="raise")
            low = pd.to_numeric(df["low"], errors="raise")
            close = pd.to_numeric(df["close"], errors="raise")

            upward_move = high.diff()
            downward_move = -low.diff()
            positive_dm = upward_move.where(
                (upward_move > downward_move) & (upward_move > 0),
                0.0,
            )
            negative_dm = downward_move.where(
                (downward_move > upward_move) & (downward_move > 0),
                0.0,
            )

            true_range = pd.concat(
                (
                    high - low,
                    (high - close.shift(1)).abs(),
                    (low - close.shift(1)).abs(),
                ),
                axis=1,
            ).max(axis=1)
            smoothing = {
                "alpha": 1.0 / length,
                "adjust": False,
                "min_periods": length,
            }
            average_true_range = true_range.ewm(**smoothing).mean()
            positive_di = (
                100.0 * positive_dm.ewm(**smoothing).mean()
                / average_true_range
            )
            negative_di = (
                100.0 * negative_dm.ewm(**smoothing).mean()
                / average_true_range
            )
            di_sum = positive_di + negative_di
            dx = (
                100.0
                * (positive_di - negative_di).abs()
                / di_sum.where(di_sum != 0)
            ).fillna(0.0)
            adx = dx.ewm(**smoothing).mean()
            adx.name = f"ADX_{length}"
            return adx
        except (TypeError, ValueError, KeyError) as exc:
            self.logger.error("Could not calculate ADX(%d): %s", length, exc)
            raise

    @staticmethod
    def _normalize_direction(direction: str) -> Optional[str]:
        """Normalize supported direction labels to BUY or SELL."""
        if not isinstance(direction, str):
            return None
        normalized = direction.strip().upper()
        if normalized in {"BUY", "LONG"}:
            return "BUY"
        if normalized in {"SELL", "SHORT"}:
            return "SELL"
        return None

    def _latest_h1_trend(self, h1_df: pd.DataFrame) -> Optional[bool]:
        """Return whether H1 is bullish; None indicates invalid candle data."""
        if (
            not isinstance(h1_df, pd.DataFrame)
            or h1_df.empty
            or "close" not in h1_df.columns
        ):
            self.logger.error("H1 candles must be non-empty and include close")
            return None

        close = pd.to_numeric(h1_df["close"], errors="coerce")
        if "EMA_50" in h1_df.columns:
            ema50 = pd.to_numeric(h1_df["EMA_50"], errors="coerce")
        else:
            ema50 = close.ewm(span=50, adjust=False, min_periods=50).mean()

        latest_close = close.iloc[-1]
        latest_ema50 = ema50.iloc[-1]
        if pd.isna(latest_close) or pd.isna(latest_ema50):
            self.logger.error(
                "Insufficient valid H1 candles to confirm EMA50 trend"
            )
            return None
        if latest_close == latest_ema50:
            self.logger.warning(
                "H1 close equals EMA50; trend direction is unclear"
            )
            return None
        return bool(latest_close > latest_ema50)

    def _adx_passes(self, m15_df: pd.DataFrame) -> bool:
        """Check that the latest M15 ADX is above the configured threshold."""
        try:
            adx = self.calculate_adx(m15_df)
        except (TypeError, ValueError, KeyError):
            return False

        latest_adx = adx.iloc[-1] if not adx.empty else float("nan")
        if pd.isna(latest_adx):
            self.logger.warning(
                "Insufficient M15 candles to calculate ADX(14)"
            )
            return False
        if latest_adx <= self.adx_threshold:
            self.logger.info(
                "Trade rejected: ADX(14)=%.2f is not above %.2f",
                latest_adx,
                self.adx_threshold,
            )
            return False
        self.logger.info(
            "ADX guard passed: ADX(14)=%.2f > %.2f",
            latest_adx,
            self.adx_threshold,
        )
        return True

    def validate_trend_following(
        self,
        m15_df: pd.DataFrame,
        h1_df: pd.DataFrame,
        direction: str,
    ) -> bool:
        """Validate an EMA trend-following signal on M15 and H1.

        The intended signal direction must agree with M15 EMA20/EMA50, have
        ADX(14) above the threshold, and agree with H1 close versus EMA50.
        """
        normalized = self._normalize_direction(direction)
        if normalized is None:
            self.logger.error(
                "Unsupported trend-following direction: %s",
                direction,
            )
            return False
        if (
            not isinstance(m15_df, pd.DataFrame)
            or m15_df.empty
            or not {"EMA_20", "EMA_50"}.issubset(m15_df.columns)
        ):
            self.logger.error(
                "M15 trend-following data must include EMA_20 and EMA_50"
            )
            return False

        ema20 = pd.to_numeric(m15_df["EMA_20"], errors="coerce").iloc[-1]
        ema50 = pd.to_numeric(m15_df["EMA_50"], errors="coerce").iloc[-1]
        if pd.isna(ema20) or pd.isna(ema50):
            self.logger.warning("Latest M15 EMA values are unavailable")
            return False
        m15_agrees = ema20 > ema50 if normalized == "BUY" else ema20 < ema50
        if not m15_agrees:
            self.logger.info(
                "Trade rejected: %s disagrees with M15 EMA20/EMA50",
                normalized,
            )
            return False
        if not self._adx_passes(m15_df):
            return False

        h1_bullish = self._latest_h1_trend(h1_df)
        if h1_bullish is None:
            return False
        h1_agrees = h1_bullish if normalized == "BUY" else not h1_bullish
        if not h1_agrees:
            self.logger.info(
                "Trade rejected: %s disagrees with H1 EMA50 trend",
                normalized,
            )
            return False

        self.logger.info(
            "%s trend-following signal passed all guards",
            normalized,
        )
        return True

    def validate_breakout(
        self,
        m15_df: pd.DataFrame,
        h1_df: pd.DataFrame,
        breakout_level: float,
        direction: str,
    ) -> bool:
        """Validate a breakout signal against its level, M15 ADX, and H1 trend.

        Long breakouts require the latest M15 close above ``breakout_level``;
        short breakouts require it below the level.
        """
        normalized = self._normalize_direction(direction)
        if normalized is None:
            self.logger.error("Unsupported breakout direction: %s", direction)
            return False
        if (
            not isinstance(m15_df, pd.DataFrame)
            or m15_df.empty
            or "close" not in m15_df.columns
        ):
            self.logger.error(
                "M15 breakout data must be non-empty and include close"
            )
            return False

        try:
            latest_close = float(
                pd.to_numeric(m15_df["close"], errors="raise").iloc[-1]
            )
            level = float(breakout_level)
        except (TypeError, ValueError, KeyError, IndexError) as exc:
            self.logger.error("Invalid breakout close or level: %s", exc)
            return False

        price_agrees = (
            latest_close > level
            if normalized == "BUY"
            else latest_close < level
        )
        if not price_agrees:
            self.logger.info(
                "Trade rejected: %s close %.5f has not crossed "
                "breakout level %.5f",
                normalized,
                latest_close,
                level,
            )
            return False
        if not self._adx_passes(m15_df):
            return False

        h1_bullish = self._latest_h1_trend(h1_df)
        if h1_bullish is None:
            return False
        h1_agrees = h1_bullish if normalized == "BUY" else not h1_bullish
        if not h1_agrees:
            self.logger.info(
                "Trade rejected: %s disagrees with H1 EMA50 trend",
                normalized,
            )
            return False

        self.logger.info("%s breakout signal passed all guards", normalized)
        return True
