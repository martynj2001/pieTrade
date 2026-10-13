"""Busy-spinner overlay shown over a window while a long operation finishes.

Kept separate from ui_pyTrade_GUI_v2.py so Qt Designer regeneration never overwrites it.
"""
from PySide6.QtCore import QEvent, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class SpinnerOverlay(QWidget):
    """Dims its parent and draws a rotating arc; call start()/stop()."""

    def __init__(self, parent: QWidget, diameter: int = 40, colour: str = "#F5A623"):
        super().__init__(parent)
        self._diameter = diameter
        self._colour = QColor(colour)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._advance)
        parent.installEventFilter(self)
        self.hide()

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() == QEvent.Type.Resize and self.isVisible():
            self.setGeometry(self.parentWidget().rect())
        return super().eventFilter(obj, event)

    def start(self):
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _advance(self):
        self._angle = (self._angle - 12) % 360
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255, 170))

        d = self._diameter
        rect = QRectF((self.width() - d) / 2, (self.height() - d) / 2, d, d)
        pen = QPen(QColor(0, 0, 0, 30), 6)
        painter.setPen(pen)
        painter.drawEllipse(rect)

        pen = QPen(self._colour, 6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, self._angle * 16, 100 * 16)
