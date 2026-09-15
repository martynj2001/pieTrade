# Implementation Plan: Volatility Breakout Strategy (`BreakoutEngine`)

## Overview
Replace the existing placeholder in `pyTrade_Breakout_Strategy.py` with a complete `BreakoutEngine` class implementing a volatility breakout trading strategy with Donchian channels, EMA trend filtering, ATR volatility expansion filters, and ATR-based risk management. Provide an integration design and code snippet for the `pyTradeWorker` thread in `pyTrade_bot.py`.

---

## 1. Class Architecture: `BreakoutEngine`

### **File to Modify**
- `pyTrade_Breakout_Strategy.py`

### **Dependencies & Logging**
- `import pandas_ta_classic as ta`
- `import pandas as pd`
- `import numpy as np`
- `import logging`
- Logger configured using `logging.getLogger("pyTrade.BreakoutEngine")` to seamlessly inherit the root logger handlers configured in `pyTradeWorker.run_bot()`.

### **Class Interface & Methods**

1. **`__init__(self, donchian_len=20, ema_len=50, atr_len=14, atr_multiplier=2.0, rr_ratio=2.0, min_sl_dist=0.05)`**
   - Store strategy hyperparameters.
   - Initialize instance logger.

2. **`add_indicators(self, df: pd.DataFrame) -> pd.DataFrame`**
   - Validate DataFrame input (check for required columns: `open`, `high`, `low`, `close` and row count).
   - Compute Donchian Channel (`DCU`, `DCL`, `DCM`) using `ta.donchian` / rolling extrema with prior-bar shifting to prevent lookahead bias.
   - Compute `EMA_50` via `ta.ema(df["close"], length=self.ema_len)`.
   - Compute `ATR_14` via `ta.atr(df["high"], df["low"], df["close"], length=self.atr_len)`.
   - Compute `ATR_SMA_14` via `ta.sma(df["ATR_14"], length=self.atr_len)`.
   - Log `DEBUG` for computed indicator tails; log `WARNING` for insufficient candle history; log `ERROR` for missing price columns.

3. **`evaluate_breakout(self, df: pd.DataFrame) -> str`**
   - Inspect the latest bar/row (`current_row`).
   - **BUY conditions**:
     - Breakout: `close > DCU` (or `high > DCU`)
     - Trend Filter: `close > EMA_50`
     - Volatility Filter: `ATR_14 > ATR_SMA_14`
   - **SELL conditions**:
     - Breakout: `close < DCL` (or `low < DCL`)
     - Trend Filter: `close < EMA_50`
     - Volatility Filter: `ATR_14 > ATR_SMA_14`
   - Log filter evaluation details at `DEBUG` level.
   - Return `"BUY"`, `"SELL"`, or `"NONE"`.

4. **`calculate_stop(self, signal: str, entry: float, atr: float) -> float`**
   - BUY Stop Loss: `entry - max(atr * self.atr_multiplier, self.min_sl_dist)`
   - SELL Stop Loss: `entry + max(atr * self.atr_multiplier, self.min_sl_dist)`

5. **`calculate_takeprofit(self, signal: str, entry: float, atr: float, stop: float = None) -> float`**
   - ATR / Risk-Reward based target:
     - BUY TP: `entry + (risk * self.rr_ratio)` (or `entry + atr * self.atr_multiplier * self.rr_ratio`)
     - SELL TP: `entry - (risk * self.rr_ratio)` (or `entry - atr * self.atr_multiplier * self.rr_ratio`)

6. **`get_signal(self, df: pd.DataFrame) -> tuple[str, float | None, float | None, float | None]`**
   - Call `add_indicators(df)`.
   - Evaluate signal via `evaluate_breakout(df)`.
   - If `"BUY"` or `"SELL"`, compute `entry` (latest close/ask/bid), `stop`, and `tp`.
   - Log `INFO` on signal generation; log `DEBUG` when no signal is triggered.
   - Return `(signal, entry, stop, tp)`.

---

## 2. Worker Thread Integration (`pyTrade_bot.py`)

### **Object-Oriented Strategy Architecture Pattern**
- Prepare `pyTrade_bot.py` to support pluggable strategy engines (e.g. `BreakoutEngine` and a future `EMATrendEngine` class).
- Instantiate `self.strategy = BreakoutEngine(...)` once during bot initialization.
- In `run_bot()` on every 15-minute candle trigger:
  ```python
  signal, entry, stop, tp = self.strategy.get_signal(price)
  if signal in ("BUY", "SELL"):
      order = self.build_order(signal, open_market["instrument"], entry, stop, tp)
      order_res = oanda.place_order(client, order)
  ```

---

## 3. Todos

- [ ] Create `BreakoutEngine` class in `pyTrade_Breakout_Strategy.py`
- [ ] Provide worker thread integration code snippet and structural change recommendations for `pyTrade_bot.py`
