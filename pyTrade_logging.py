"""Shared logging setup for pyTrade.

Called once from pyTrade_main at startup so the GUI and the bot worker
write to the same log file.
"""
import logging
from datetime import datetime, timezone

import config

_configured = False


def setup_logging() -> None:
    """Configure root logging to a timestamped pyTrade log file. Runs once."""
    global _configured
    if _configured:
        return
    _configured = True

    logging.basicConfig(
        filename=f"{datetime.now(timezone.utc).strftime('%d%m%y-%H%M')}-pyTrade.log",
        level=logging.DEBUG if config.DEBUG_LOGGING else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
    )
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("oandapyV20.oandapyV20").setLevel(logging.INFO)
