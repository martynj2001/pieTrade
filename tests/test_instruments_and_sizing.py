import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import config  # noqa: F401
except ImportError:
    sys.modules["config"] = SimpleNamespace(MONEY_RISK=6.0, RISK_PERCENT=0.02)

import pyTrade_instruments as instruments
from pyTrade_orders import OrderManager


@pytest.mark.parametrize(
    "instr, pip, min_sl, precision",
    [
        ("EUR_USD", 0.0001, 0.0005, 5),
        ("GBP_USD", 0.0001, 0.0005, 5),
        ("USD_JPY", 0.01, 0.05, 3),
        ("GBP_JPY", 0.01, 0.05, 3),
    ],
)
def test_instrument_settings(instr, pip, min_sl, precision):
    assert instruments.pip_size(instr) == pip
    assert instruments.min_sl_dist(instr) == min_sl
    assert instruments.price_precision(instr) == precision


@pytest.mark.parametrize(
    "instrument, entry, stop, rate, expected",
    [
        ("EUR_USD", 1.1000, 1.1000 - 0.0012, 0.79, 6329),
        ("USD_JPY", 150.00, 150.00 - 0.20, 0.0053, 5660),
    ],
)
def test_calculate_units(instrument, entry, stop, rate, expected):
    units = OrderManager().calculate_units(
        "BUY",
        entry,
        stop,
        money_risk=6.0,
        instrument=instrument,
        quote_to_gbp=rate,
    )
    assert units == expected


def test_calculate_units_clamps_to_pair_minimum_stop():
    units = OrderManager().calculate_units(
        "BUY", 1.1000, 1.0999, money_risk=6.0, instrument="EUR_USD", quote_to_gbp=0.79
    )
    assert units == int(6.0 / (0.0005 * 0.79))
