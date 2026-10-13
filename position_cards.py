"""Reusable open-position card widgets.

Kept separate from ui_pyTrade_GUI_v2.py so Qt Designer regeneration never overwrites it.
"""
from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QLabel, QPushButton, QScrollArea,
                               QStackedLayout, QVBoxLayout, QWidget)

GREEN = "#1E9E52"
RED = "rgb(224, 27, 36)"
CURRENCY = "£"


def _money(value: float, signed: bool = False) -> str:
    sign = "+" if signed and value > 0 else "-" if value < 0 else ""
    return f"{sign}{CURRENCY}{abs(value):,.2f}"


def _pl_colour(value: float) -> str:
    return RED if value < 0 else GREEN


class PositionCard(QFrame):
    """Summary of one open position with an expandable list of its trades."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("positionCard")
        self.setStyleSheet(
            "#positionCard { background: #FFFFFF; border: 1px solid #C8C8C8; border-radius: 8px; }"
            "#positionCard QLabel { background: transparent; color: #222222; }"
        )
        layout = QVBoxLayout(self)

        self.lb_title = QLabel()
        self.lb_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.lb_units = QLabel()
        self.lb_trades = QLabel()
        self.lb_pl = QLabel()
        self.lb_margin = QLabel()
        for label in (self.lb_title, self.lb_units, self.lb_trades, self.lb_pl, self.lb_margin):
            layout.addWidget(label)

        self.pb_view_trades = QPushButton("View Trades")
        self.pb_view_trades.setCheckable(True)
        self.pb_view_trades.toggled.connect(self._on_toggled)
        layout.addWidget(self.pb_view_trades)

        self.trades_frame = QWidget()
        self.trades_layout = QVBoxLayout(self.trades_frame)
        self.trades_layout.setContentsMargins(0, 4, 0, 0)
        self.trades_frame.setVisible(False)
        layout.addWidget(self.trades_frame)

    @property
    def expanded(self) -> bool:
        return self.pb_view_trades.isChecked()

    def _on_toggled(self, checked: bool):
        self.pb_view_trades.setText("Hide Trades" if checked else "View Trades")
        self.trades_frame.setVisible(checked)

    def set_data(self, data: Dict[str, Any]):
        self.lb_title.setText(f"{data['instrument'].replace('_', '/')} {data['direction']}")
        self.lb_units.setText(f"Units: {data['units']:,}")
        self.lb_trades.setText(f"Trades: {data['trade_count']}")
        self.lb_pl.setText(f"P/L: {_money(data['pl'], signed=True)}")
        self.lb_pl.setStyleSheet(f"color: {_pl_colour(data['pl'])};")
        self.lb_margin.setText(f"Margin: {_money(data['margin'])}")

        while self.trades_layout.count():
            item = self.trades_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for trade in data["trades"]:
            self.trades_layout.addWidget(self._trade_row(trade))
        if not data["trades"]:
            self.trades_layout.addWidget(QLabel("Trade details unavailable"))

    @staticmethod
    def _trade_row(trade: Dict[str, Any]) -> QFrame:
        row = QFrame()
        row.setStyleSheet("QFrame { background: #F0F0F0; border-radius: 4px; }"
                          "QLabel { background: transparent; color: #222222; }")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)
        layout.addWidget(QLabel(f"Trade {trade['id']} — Units: {trade['units']:,}"))
        pl = QLabel(f"P/L: {_money(trade['pl'], signed=True)}")
        pl.setStyleSheet(f"color: {_pl_colour(trade['pl'])};")
        layout.addWidget(pl)
        layout.addWidget(QLabel(f"TP: {trade['tp'] or '—'}   SL: {trade['sl'] or '—'}"))
        return row


class PositionCardsPanel:
    """Populates a Designer-made QScrollArea with one PositionCard per open position."""

    def __init__(self, scroll_area: QScrollArea):
        self._cards: Dict[str, PositionCard] = {}

        container = QWidget()
        self._stack = QStackedLayout(container)

        self._empty = QLabel("No Open Positions")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: rgb(224, 27, 36); font-weight: bold; font-size: 12px;")
        self._stack.addWidget(self._empty)

        cards_page = QWidget()
        self._cards_layout = QVBoxLayout(cards_page)
        self._cards_layout.addStretch(1)
        self._stack.addWidget(cards_page)

        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container)
        self._stack.setCurrentWidget(self._empty)

    def update_positions(self, positions: List[Dict[str, Any]]):
        """Refresh cards in place so expanded state survives each update."""
        seen = set()
        for data in positions:
            key = f"{data['instrument']}:{data['direction']}"
            seen.add(key)
            card = self._cards.get(key)
            if card is None:
                card = PositionCard()
                self._cards[key] = card
                self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
            card.set_data(data)

        for key in list(self._cards):
            if key not in seen:
                card = self._cards.pop(key)
                self._cards_layout.removeWidget(card)
                card.deleteLater()

        self._stack.setCurrentIndex(1 if self._cards else 0)
