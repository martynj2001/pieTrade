"""AI agent status card (display only).

Kept separate from ui_pyTrade_GUI_v2.py so Qt Designer regeneration never overwrites it.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

import config

GREEN = "#2ECC71"
AMBER = "#F19E39"
GREY = "#8C8C8C"
RED = "#E01B24"
TEXT = "#e6e6e6"
CAPTION = "#9a9a9a"

ROWS = (
    "Status", "Using", "Market", "Pair", "Hour", "Reason", "Chosen at",
    "Next hour", "Fixed-session pair", "Last request", "Updated",
)


def _market(name: Optional[str]) -> str:
    return name.replace("_", " ").title() if name else "-"


def _pair(instrument: Optional[str]) -> str:
    return instrument.replace("_", "/") if instrument else "-"


def _time(iso: Optional[str], fmt: str = "%H:%M") -> str:
    try:
        return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime(fmt)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "-"


class AgentCard(QFrame):
    """Shows what the AI agent is doing: status, current pick, next pick and request health."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("agentCard")
        self.setStyleSheet(
            "#agentCard { background: transparent; background-image: none; }"
            f"#agentCard QLabel {{ background: transparent; color: {TEXT}; }}"
        )
        self._enabled = False
        self._snapshot: Optional[Dict[str, Any]] = None
        self._running = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        header = QHBoxLayout()
        title = QLabel("AI Agent")
        title.setStyleSheet(f"color: {TEXT}; font-weight: bold; background: transparent;")
        self.badge = QLabel()
        self.badge.setObjectName("agentBadge")
        header.addWidget(title)
        header.addWidget(self.badge)
        header.addStretch(1)
        layout.addLayout(header)

        body = QWidget()
        body.setObjectName("agentBody")
        body.setStyleSheet("QWidget#agentBody { background: transparent; background-image: none; }")
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(1)
        grid.setColumnStretch(1, 1)
        self._labels: Dict[str, QLabel] = {}
        self._values: Dict[str, QLabel] = {}
        for index, name in enumerate(ROWS):
            label = QLabel(f"{name}:")
            label.setStyleSheet(f"color: {CAPTION}; background: transparent;")
            value = QLabel("-")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            grid.addWidget(label, index, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(value, index, 1)
            self._labels[name] = label
            self._values[name] = value
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; background-image: none; }")
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        self.show_idle(False)

    @staticmethod
    def _shadow(snapshot: Optional[dict]) -> bool:
        if snapshot is not None:
            return bool(snapshot.get("shadow", True))
        return bool(getattr(config, "AGENT_SHADOW", True))

    @Slot(dict)
    def update_plan(self, snapshot: dict) -> None:
        """Show the latest snapshot sent by the bot thread."""
        self._snapshot = snapshot
        self._running = True
        self._enabled = bool(snapshot.get("enabled"))
        self._render()

    @Slot(bool)
    def show_idle(self, enabled: bool) -> None:
        """Bot stopped: show only the saved on/off status."""
        self._snapshot = None
        self._running = False
        self._enabled = bool(enabled)
        self._render()

    @Slot(bool)
    def set_enabled(self, enabled: bool) -> None:
        """Update the status immediately when the Settings switch changes."""
        self._enabled = bool(enabled)
        self._render()

    def _render(self) -> None:
        snapshot = self._snapshot if self._enabled else None
        shadow = self._shadow(self._snapshot)
        if not self._enabled:
            status, colour = "OFF", GREY
        elif shadow:
            status, colour = "ON - shadow (not used for trading)", AMBER
        else:
            status, colour = "ON - live", GREEN
        badge_text = status.split(" (")[0]
        self.badge.setText(badge_text)
        self.badge.setStyleSheet(
            f"QLabel#agentBadge {{ background: {colour}; color: #000000; border-radius: 8px; "
            "padding: 1px 8px; font-size: 11px; font-weight: bold; }"
        )

        current = snapshot.get("current") if snapshot else None
        nxt = snapshot.get("next") if snapshot else None
        fixed = self._snapshot.get("fixed") if self._snapshot else None
        last = snapshot.get("last") if snapshot else None

        self._labels["Market"].setText("Would trade market:" if shadow else "Market:")
        self._labels["Pair"].setText("Would trade pair:" if shadow else "Pair:")

        values = {name: "-" for name in ROWS}
        colours = {name: TEXT for name in ROWS}
        values["Status"], colours["Status"] = status, colour
        if not self._running:
            values["Using"] = "Bot stopped"
        else:
            values["Using"] = (self._snapshot or {}).get("using", "-") if self._enabled else "fixed sessions"
            values["Fixed-session pair"] = f"{_market(fixed['market'])} {_pair(fixed['instrument'])}" if fixed else "-"
            values["Updated"] = _time((self._snapshot or {}).get("updated"), "%H:%M:%S UTC")
        if current:
            values["Market"] = _market(current["market"])
            values["Pair"] = _pair(current["instrument"])
            hour = _time(current.get("target_hour"))
            values["Hour"] = f"{hour}-{(int(hour[:2]) + 1) % 24:02d}:00 UTC" if hour != "-" else "-"
            values["Reason"] = current.get("reason") or "-"
            latency = current.get("latency_s")
            values["Chosen at"] = _time(current.get("decided_at")) + " UTC" + (f" ({latency:.1f}s)" if latency else "")
        if nxt:
            values["Next hour"] = f"{_market(nxt['market'])} {_pair(nxt['instrument'])} from {_time(nxt.get('target_hour'))} UTC"
        if last:
            if last.get("status") == "failed":
                values["Last request"] = f"failed - retry {_time(last.get('retry_at'))} UTC"
                colours["Last request"] = RED
            else:
                values["Last request"] = str(last.get("status", "-"))
                if last.get("status") == "ok":
                    colours["Last request"] = GREEN
        for name in ROWS:
            self._values[name].setText(values[name])
            self._values[name].setStyleSheet(f"color: {colours[name]}; background: transparent;")
