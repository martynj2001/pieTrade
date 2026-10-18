"""Candlestick chart widget built on pyqtgraph.

Kept separate from ui_pyTrade_GUI_v2.py so Qt Designer regeneration never overwrites it.
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPicture
from PySide6.QtWidgets import QStyleOptionGraphicsItem, QVBoxLayout, QWidget

logger = logging.getLogger("pyTrade.CandleChart")

GREEN = "#2ECC71"
RED = "#E01B24"
BACKGROUND = "#1e1e1e"
TEXT = "#e6e6e6"
REQUIRED_COLUMNS = ("time", "open", "high", "low", "close")
VISIBLE_CANDLES = 100


class CandlestickItem(pg.GraphicsObject):
    """Renders OHLC candles, drawn into a QPicture once per data update."""

    def __init__(self):
        super().__init__()
        self._picture = QPicture()
        self._bounds = QRectF()

    def set_data(self, xs: np.ndarray, df: pd.DataFrame, width: float) -> None:
        """Draw every candle. xs are Unix timestamps (seconds) aligned with df's rows."""
        self.prepareGeometryChange()

        opens = df["open"].to_numpy(dtype=float)
        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)
        closes = df["close"].to_numpy(dtype=float)

        picture = QPicture()
        painter = QPainter(picture)
        wick_pen = QPen()
        wick_pen.setWidthF(1.0)
        wick_pen.setCosmetic(True)

        for x, open_, high, low, close in zip(xs, opens, highs, lows, closes):
            colour = QColor(GREEN if close >= open_ else RED)
            wick_pen.setColor(colour)
            painter.setPen(wick_pen)
            painter.drawLine(x, low, x, high)
            painter.setBrush(QBrush(colour))
            top = max(open_, close)
            height = abs(close - open_)
            if height == 0:  # doji: flat body line
                painter.drawLine(x - width / 2, top, x + width / 2, top)
            else:
                painter.drawRect(QRectF(x - width / 2, top - height, width, height))
        painter.end()

        self._picture = picture
        if len(xs):
            x0, x1 = float(min(xs)) - width, float(max(xs)) + width
            y0, y1 = float(lows.min()), float(highs.max())
            self._bounds = QRectF(x0, y0, x1 - x0, max(y1 - y0, 1e-9))
        else:
            self._bounds = QRectF()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: Optional[QWidget] = None) -> None:
        painter.drawPicture(0, 0, self._picture)

    def boundingRect(self) -> QRectF:
        return self._bounds


class CandleChartPanel:
    """Hosts a pyqtgraph candlestick chart inside a container widget. GUI thread only."""

    def __init__(self, container: QWidget):
        date_axis = pg.DateAxisItem(orientation="bottom", utcOffset=0)
        self._plot = pg.PlotWidget(axisItems={"bottom": date_axis}, background=BACKGROUND)
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        for axis_name in ("bottom", "left"):
            axis = self._plot.getAxis(axis_name)
            axis.setPen(pg.mkPen(TEXT))
            axis.setTextPen(pg.mkPen(TEXT))

        self._candles = CandlestickItem()
        self._plot.addItem(self._candles)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)

    def update_candles(self, instrument: str, df: Optional[pd.DataFrame]) -> None:
        """Redraw the chart with the given candles, zoomed to the most recent ones."""
        if df is None or df.empty or any(col not in df.columns for col in REQUIRED_COLUMNS):
            return

        try:
            times = pd.to_datetime(df["time"], utc=True)
            xs = times.astype("int64").to_numpy() / 1e9
        except (TypeError, ValueError) as exc:
            logger.warning("Could not convert candle times to timestamps: %s", exc)
            return

        spacing = xs[1] - xs[0] if len(xs) > 1 else 0
        width = 0.7 * spacing if spacing > 0 else 600.0

        self._candles.set_data(xs, df, width)
        self._plot.setTitle(instrument.replace("_", "/"), color=TEXT, size="12pt")

        # Zoom to the most recent candles; all data stays drawn for panning back.
        visible = min(VISIBLE_CANDLES, len(xs))
        self._plot.setXRange(xs[-visible] - width, xs[-1] + width, padding=0)
        tail = df.iloc[-visible:]
        y_lo, y_hi = float(tail["low"].min()), float(tail["high"].max())
        pad = max((y_hi - y_lo) * 0.05, 1e-9)
        self._plot.setYRange(y_lo - pad, y_hi + pad, padding=0)


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    rng = np.random.default_rng(7)
    times = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("15min"),
                          periods=200, freq="15min")
    rows = []
    price = 1.10
    for t in times:
        open_ = price
        close = open_ + rng.normal(0, 0.0008)
        rows.append({
            "time": t,
            "open": open_,
            "high": max(open_, close) + abs(rng.normal(0, 0.0004)),
            "low": min(open_, close) - abs(rng.normal(0, 0.0004)),
            "close": close,
        })
        price = close
    demo_df = pd.DataFrame(rows)

    container = QWidget()
    container.setWindowTitle("pyTrade Candle Chart Demo")
    container.resize(1000, 600)
    panel = CandleChartPanel(container)
    panel.update_candles("EUR_USD", demo_df)
    container.show()

    sys.exit(app.exec())
