"""Persistent settings and worker application for pyTrade."""
import json
import logging
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Optional

import config

logger = logging.getLogger("pyTrade.Settings")
SETTINGS_PATH = Path(__file__).with_name("settings.json")


@dataclass(frozen=True)
class Setting:
    """Definition of one persisted and editable application setting."""

    key: str
    label: str
    kind: Literal["bool", "float", "int", "choice"]
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    scale: float = 1.0
    choices: tuple[tuple[str, str], ...] = ()  # (value, label) pairs for kind "choice"
    section: str = "General"
    live: bool = True
    targets: tuple[str, ...] = ()
    on_apply: Optional[Callable[[Any, Any], None]] = None


def _set_debug_logging(value: bool, worker: Any) -> None:
    logging.getLogger().setLevel(logging.DEBUG if value else logging.INFO)


SETTINGS: list[Setting] = [
    Setting("debug_logging", "Debug Logging", "bool", config.DEBUG_LOGGING, on_apply=_set_debug_logging),
    Setting(
        "strategy_mode", "Strategy mode", "choice", "dual", section="Strategies",
        targets=("strategy_mode",),
        choices=(
            ("dual", "Primary + secondary (secondary tried if primary has no signal)"),
            ("single", "Selected strategy only (the one chosen in the menu)"),
        ),
    ),
    Setting("risk_percent", "Risk per Trade (%)", "float", config.RISK_PERCENT, min=0.001, max=0.05, step=0.001, scale=100, section="Trading", targets=("order_manager.risk_percent",)),
    Setting("adx_threshold", "ADX Threshold", "float", 24.0, min=10, max=50, step=1, section="Trade guards", targets=("trade_guards.adx_threshold",)),
    Setting("atr_multiplier", "ATR Stop Multiplier", "float", 1.5, min=0.5, max=5, step=0.1, section="Strategies", targets=("strategies.atr_multiplier",)),
    Setting("rr_ratio", "Risk/Reward ratio", "float", 1.0, min=0.5, max=5, step=0.1, section="Strategies", targets=("strategies.rr_ratio",)),
    Setting("max_trade_hours", "Maximum Trade Duration (hours)", "float", 4.0, min=0.25, max=24, step=0.25, section="Validation", targets=("validator.max_trade_hours",)),
    Setting("enable_session_check", "Enable Session Check", "bool", True, section="Validation", targets=("validator.enable_session_check",)),
]


def _normalize(setting: Setting, value: Any) -> Any:
    """Validate one value, clamp numbers, and use the default when invalid."""
    if setting.kind == "bool":
        return value if isinstance(value, bool) else setting.default
    if setting.kind == "choice":
        return value if value in dict(setting.choices) else setting.default
    if setting.kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            return setting.default
        number: int | float = value
    else:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return setting.default
        number = float(value)
        if not math.isfinite(number):
            return setting.default
    if setting.min is not None:
        number = max(number, setting.min)
    if setting.max is not None:
        number = min(number, setting.max)
    return int(number) if setting.kind == "int" else float(number)


def load() -> dict[str, Any]:
    """Load settings, falling back to defaults for invalid or missing values."""
    defaults = {setting.key: setting.default for setting in SETTINGS}
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
            stored = json.load(settings_file)
        if not isinstance(stored, dict):
            return defaults
        return {
            setting.key: _normalize(setting, stored.get(setting.key, setting.default))
            for setting in SETTINGS
        }
    except Exception:
        return defaults


def save(values: dict) -> None:
    """Atomically save known settings beside this module."""
    normalized = {
        setting.key: _normalize(setting, values.get(setting.key, setting.default))
        for setting in SETTINGS
    }
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=SETTINGS_PATH.parent,
            prefix=".settings-", suffix=".tmp", delete=False,
        ) as settings_file:
            temporary_path = Path(settings_file.name)
            json.dump(normalized, settings_file, indent=2)
            settings_file.write("\n")
        os.replace(temporary_path, SETTINGS_PATH)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _resolve_target(worker: Any, path: str) -> tuple[Any, str]:
    """Return the parent object and final attribute for a dotted target path."""
    parts = path.split(".")
    target = worker
    for part in parts[:-1]:
        target = getattr(target, part)
    return target, parts[-1]


def apply_to_worker(values: dict[str, Any], worker: Any) -> None:
    """Apply settings to the worker and log only values that actually changed."""
    for setting in SETTINGS:
        value = _normalize(setting, values.get(setting.key, setting.default))
        if setting.on_apply is not None:
            old_level = logging.getLevelName(logging.getLogger().level)
            setting.on_apply(value, worker)
            new_level = logging.getLevelName(logging.getLogger().level)
            if old_level != new_level:
                logger.info("%s: %s -> %s", setting.key, old_level, new_level)

        for path in setting.targets:
            if path.startswith("strategies."):
                target_path = path.removeprefix("strategies.")
                targets = (worker.strategy_primary, worker.strategy_secondary)
            else:
                target_path = path
                targets = (worker,)
            for target in targets:
                parent, attribute = _resolve_target(target, target_path)
                old_value = getattr(parent, attribute, None)
                if old_value != value:
                    setattr(parent, attribute, value)
                    logger.info("%s: %s -> %s", setting.key, old_value, value)
