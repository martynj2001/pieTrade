"""Pure analytics functions over closed-trade rows (dicts)."""
from collections import defaultdict
from statistics import median
from typing import Iterable, Optional

TOLERANCE = 0.02  # fraction of the entry->level distance


def is_win(t: dict) -> bool:
    return (t.get("pnl_currency") or 0) > 0


def _summarise(trades: list[dict]) -> dict:
    n = len(trades)
    wins = sum(1 for t in trades if is_win(t))
    pnls = [t.get("pnl_currency") or 0 for t in trades]
    return {
        "trades": n,
        "wins": wins,
        "losses": n - wins,
        "win_rate": round(wins / n * 100, 2) if n else None,
        "total_pnl": round(sum(pnls), 4),
        "avg_pnl": round(sum(pnls) / n, 4) if n else None,
        "profit_factor": profit_factor(trades),
    }


def profit_factor(trades: Iterable[dict]) -> Optional[float]:
    gp = gl = 0.0
    for t in trades:
        p = t.get("pnl_currency") or 0
        if p > 0:
            gp += p
        else:
            gl += -p
    return round(gp / gl, 4) if gl > 0 else None


def group_by(trades: list[dict], key: str) -> list[dict]:
    groups: dict = defaultdict(list)
    for t in trades:
        groups[t.get(key) or "unknown"].append(t)
    return sorted(
        ({key: k, **_summarise(v)} for k, v in groups.items()),
        key=lambda r: r["trades"],
        reverse=True,
    )


def overall(trades: list[dict]) -> dict:
    gp = sum(t["pnl_currency"] for t in trades if (t.get("pnl_currency") or 0) > 0)
    gl = -sum(t["pnl_currency"] for t in trades if (t.get("pnl_currency") or 0) < 0)
    return {**_summarise(trades), "gross_profit": round(gp, 4), "gross_loss": round(gl, 4)}


def holding_time(trades: list[dict], key: Optional[str] = None) -> dict:
    def stats(ts):
        d = [t["duration_minutes"] for t in ts if t.get("duration_minutes") is not None]
        return {
            "trades": len(d),
            "avg_minutes": round(sum(d) / len(d), 2) if d else None,
            "median_minutes": median(d) if d else None,
        }

    res = {"overall": stats(trades)}
    if key:
        groups: dict = defaultdict(list)
        for t in trades:
            groups[t.get(key) or "unknown"].append(t)
        res["groups"] = [{key: k, **stats(v)} for k, v in sorted(groups.items())]
    return res


def classify_exit(t: dict) -> str:
    """Return 'take_profit', 'stop_loss' or 'other'."""
    exit_p, entry = t.get("exit_price"), t.get("entry_price")
    if exit_p is not None and entry is not None:
        for level_key, label in (("take_profit", "take_profit"), ("stop_loss", "stop_loss")):
            level = t.get(level_key)
            if level is None:
                continue
            tol = abs(entry - level) * TOLERANCE
            if abs(exit_p - level) <= max(tol, 1e-9):
                return label
    reason = (t.get("close_reason") or "").lower()
    if "take profit" in reason or "take_profit" in reason or reason.strip() in ("tp", "tp hit"):
        return "take_profit"
    if "stop loss" in reason or "stop_loss" in reason or reason.strip() in ("sl", "sl hit"):
        return "stop_loss"
    return "other"


def exit_reasons(trades: list[dict]) -> dict:
    n = len(trades)
    counts = {"take_profit": 0, "stop_loss": 0, "other": 0}
    for t in trades:
        counts[classify_exit(t)] += 1
    pct = lambda c: round(c / n * 100, 2) if n else None
    return {
        "trades": n,
        "take_profit": {"count": counts["take_profit"], "pct": pct(counts["take_profit"])},
        "stop_loss": {"count": counts["stop_loss"], "pct": pct(counts["stop_loss"])},
        "other": {"count": counts["other"], "pct": pct(counts["other"])},
    }


def atr_ranges(trades: list[dict], buckets: int = 4) -> list[dict]:
    """Equal-count ATR buckets (by trade_signals.atr14), ranked by win rate."""
    with_atr = sorted((t for t in trades if t.get("atr14") is not None), key=lambda t: t["atr14"])
    n = len(with_atr)
    if not n:
        return []
    buckets = max(1, min(buckets, n))
    out = []
    for i in range(buckets):
        chunk = with_atr[i * n // buckets:(i + 1) * n // buckets]
        if chunk:
            out.append({"atr_min": chunk[0]["atr14"], "atr_max": chunk[-1]["atr14"], **_summarise(chunk)})
    return out


def drawdown(trades: list[dict], starting_balance: Optional[float] = None) -> dict:
    ordered = sorted(
        (t for t in trades if t.get("exit_time")), key=lambda t: t["exit_time"]
    )
    equity = peak = 0.0
    peak_time = None
    curve, max_dd, max_dd_pct = [], 0.0, None
    dd_peak_time = dd_trough_time = None
    for t in ordered:
        equity += t.get("pnl_currency") or 0
        if equity > peak:
            peak, peak_time = equity, t["exit_time"]
        dd = peak - equity
        curve.append({"time": t["exit_time"], "trade_id": t["trade_id"],
                      "equity": round(equity, 4), "drawdown": round(dd, 4)})
        if dd > max_dd:
            max_dd, dd_peak_time, dd_trough_time = dd, peak_time, t["exit_time"]
            base = (starting_balance or 0) + peak
            max_dd_pct = round(dd / base * 100, 2) if base > 0 and starting_balance else None
    return {
        "max_drawdown": round(max_dd, 4),
        "max_drawdown_pct": max_dd_pct,
        "peak_time": dd_peak_time,
        "trough_time": dd_trough_time,
        "curve": curve,
    }
