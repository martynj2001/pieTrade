"""Settings editor panel for the pyTrade desktop application."""
import logging
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
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

import pyTrade_settings as settings

logger = logging.getLogger("pyTrade.Settings")


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
            if setting.kind == "bool":
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
        if setting.kind == "bool":
            return QCheckBox()
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

    def _fill(self, values: dict[str, Any]) -> None:
        """Set controls from stored values, converting to display units."""
        for key, control in self._controls.items():
            setting = self._definitions[key]
            value = values.get(key, setting.default)
            if setting.kind == "bool":
                control.setChecked(value)  # type: ignore[attr-defined]
            else:
                control.setValue(value * setting.scale)  # type: ignore[attr-defined]

    def _values(self) -> dict[str, Any]:
        """Read and convert all controls to stored values."""
        values = {}
        for key, control in self._controls.items():
            setting = self._definitions[key]
            if setting.kind == "bool":
                value = control.isChecked()  # type: ignore[attr-defined]
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
