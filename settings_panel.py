"""Settings editor panel for the pyTrade desktop application."""
import logging
from typing import Any

from PySide6.QtCore import (
    Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import config
import pyTrade_settings as settings

logger = logging.getLogger("pyTrade.Settings")


class ToggleSwitch(QAbstractButton):
    """iOS-style on/off switch, drawn in paintEvent so inherited stylesheets cannot affect it."""

    OFF_COLOUR = QColor("#636366")
    ON_COLOUR = QColor("#34C759")

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(51, 31)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("AI Agent")
        self._position = 0.0
        self._instant = False
        self._animation = QPropertyAnimation(self, b"position", self)
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self._on_toggled)

    def _get_position(self) -> float:
        return self._position

    def _set_position(self, value: float) -> None:
        self._position = value
        self.update()

    position = Property(float, _get_position, _set_position)

    def sizeHint(self) -> QSize:
        return QSize(51, 31)

    def setCheckedInstant(self, checked: bool) -> None:
        """Set the state without animating (initial load from saved settings)."""
        self._instant = True
        self.blockSignals(True)  # a programmatic load must not trigger a save
        self.setChecked(checked)
        self.blockSignals(False)
        self._instant = False
        self._animation.stop()
        self._set_position(1.0 if checked else 0.0)

    def _on_toggled(self, checked: bool) -> None:
        if self._instant:
            return
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)
        t = self._position
        track = QColor(
            round(self.OFF_COLOUR.red() + (self.ON_COLOUR.red() - self.OFF_COLOUR.red()) * t),
            round(self.OFF_COLOUR.green() + (self.ON_COLOUR.green() - self.OFF_COLOUR.green()) * t),
            round(self.OFF_COLOUR.blue() + (self.ON_COLOUR.blue() - self.OFF_COLOUR.blue()) * t),
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(0, 0, 51, 31), 15.5, 15.5)
        x = 2 + t * (51 - 27 - 4)
        painter.setBrush(QColor(0, 0, 0, 45))  # soft shadow
        painter.drawEllipse(QRectF(x - 0.5, 3, 28, 28))
        painter.setBrush(QColor("white"))
        painter.drawEllipse(QRectF(x, 2, 27, 27))


class SettingsPanel(QWidget):
    """Build and apply controls from the central settings definitions."""

    settings_applied = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("settingsPanel")
        self.setStyleSheet("QWidget#settingsPanel { background-image: none; }")
        self._controls: dict[str, QWidget] = {}
        self._definitions = {setting.key: setting for setting in settings.SETTINGS}

        layout = QVBoxLayout(self)
        groups: dict[str, tuple[QGroupBox, QFormLayout]] = {}
        for setting in settings.SETTINGS:
            if setting.section not in groups:
                group = QGroupBox(setting.section)
                form = QFormLayout(group)
                groups[setting.section] = (group, form)
                layout.addWidget(group)
            group, form = groups[setting.section]

            control = self._make_control(setting)
            self._controls[setting.key] = control
            if setting.switch:
                form.addRow(self._switch_row(setting, control))
            elif setting.kind == "bool":
                control.setText(setting.label)  # type: ignore[attr-defined]
                form.addRow("", control)
            else:
                form.addRow(setting.label, control)

        note = QLabel(
            "Changes will apply to new trades only. Open trades will keep their current stop loss and take profit."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QHBoxLayout()
        self.pb_apply = QPushButton("Apply")
        self.pb_reset = QPushButton("Reset to Defaults")
        self.pb_apply.clicked.connect(self._apply)
        self.pb_reset.clicked.connect(self._reset)
        buttons.addWidget(self.pb_apply)
        buttons.addWidget(self.pb_reset)
        layout.addLayout(buttons)
        layout.addStretch(1)

        self._fill(settings.load())

    @staticmethod
    def _make_control(setting: settings.Setting) -> QWidget:
        """Create the numeric or boolean control for a setting definition."""
        if setting.switch:
            return ToggleSwitch()
        if setting.kind == "bool":
            return QCheckBox()
        if setting.kind == "choice":
            control = QComboBox()
            for value, label in setting.choices:
                control.addItem(label, value)
            return control
        if setting.kind == "int":
            control = QSpinBox()
            control.setRange(
                int(setting.min) if setting.min is not None else -2147483647,
                int(setting.max) if setting.max is not None else 2147483647,
            )
            control.setSingleStep(int(setting.step or 1) * int(setting.scale))
            return control

        control = QDoubleSpinBox()
        control.setDecimals(4)
        control.setRange(
            setting.min * setting.scale if setting.min is not None else -1e12,
            setting.max * setting.scale if setting.max is not None else 1e12,
        )
        control.setSingleStep((setting.step or 0.1) * setting.scale)
        return control

    def _switch_row(self, setting: settings.Setting, switch: QWidget) -> QWidget:
        """Row with a bold title and grey caption on the left and the switch on the right."""
        row = QWidget()
        row.setObjectName("switchRow")
        row.setStyleSheet("QWidget#switchRow { background: transparent; background-image: none; }")
        outer = QVBoxLayout(row)
        outer.setContentsMargins(0, 0, 0, 0)
        line = QHBoxLayout()
        text = QVBoxLayout()
        title = QLabel(setting.label)
        title.setObjectName("switchTitle")
        title.setStyleSheet("QLabel#switchTitle { font-weight: bold; background: transparent; }")
        caption = QLabel("Lets the AI choose the pair and market each hour. Off = fixed market sessions.")
        caption.setObjectName("switchCaption")
        caption.setWordWrap(True)
        caption.setStyleSheet("QLabel#switchCaption { color: #888888; font-size: 11px; background: transparent; }")
        text.addWidget(title)
        text.addWidget(caption)
        line.addLayout(text, 1)
        line.addWidget(switch, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addLayout(line)
        if getattr(config, "AGENT_SHADOW", True):
            shadow = QLabel("Shadow mode is on (config.py): the AI's picks are logged but not used for trading.")
            shadow.setObjectName("switchShadow")
            shadow.setWordWrap(True)
            shadow.setStyleSheet("QLabel#switchShadow { color: #F19E39; font-size: 11px; background: transparent; }")
            outer.addWidget(shadow)
        switch.toggled.connect(lambda checked, key=setting.key: self._switch_toggled(key, checked))  # type: ignore[attr-defined]
        return row

    def _switch_toggled(self, key: str, checked: bool) -> None:
        """Save only this switch (other unsaved edits stay unsaved) and notify listeners."""
        values = settings.load()
        values[key] = checked
        settings.save(values)
        self.settings_applied.emit(values)
        logger.info("%s set to %s", key, checked)

    def _fill(self, values: dict[str, Any]) -> None:
        """Set controls from stored values, converting to display units."""
        for key, control in self._controls.items():
            setting = self._definitions[key]
            value = values.get(key, setting.default)
            if setting.switch:
                control.setCheckedInstant(value)  # type: ignore[attr-defined]
            elif setting.kind == "bool":
                control.setChecked(value)  # type: ignore[attr-defined]
            elif setting.kind == "choice":
                control.setCurrentIndex(max(0, control.findData(value)))  # type: ignore[attr-defined]
            else:
                control.setValue(value * setting.scale)  # type: ignore[attr-defined]

    def _values(self) -> dict[str, Any]:
        """Read and convert all controls to stored values."""
        values = {}
        for key, control in self._controls.items():
            setting = self._definitions[key]
            if setting.kind == "bool":
                value = control.isChecked()  # type: ignore[attr-defined]
            elif setting.kind == "choice":
                value = control.currentData()  # type: ignore[attr-defined]
            else:
                value = control.value() / setting.scale  # type: ignore[attr-defined]
            values[key] = value
        return values

    def _apply(self) -> None:
        """Persist current control values and notify the worker."""
        values = self._values()
        settings.save(values)
        self.settings_applied.emit(values)
        logger.info("Settings applied")

    def _reset(self) -> None:
        """Fill controls with defaults without saving or applying them."""
        self._fill({setting.key: setting.default for setting in settings.SETTINGS})

    def set_running(self, running: bool) -> None:
        """Disable settings that are not live-editable while the bot runs."""
        for key, control in self._controls.items():
            control.setEnabled(not running or self._definitions[key].live)
