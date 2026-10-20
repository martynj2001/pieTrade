def pip_size(instr: str) -> float:
    return 0.01 if instr.endswith("_JPY") else 0.0001


def min_sl_dist(instr: str) -> float:
    return 0.10 if instr.endswith("_JPY") else 0.0010


def price_precision(instr: str) -> int:
    return 3 if instr.endswith("_JPY") else 5
