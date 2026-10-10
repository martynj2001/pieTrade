"""Qt-free conversion of OANDA open positions/trades into display data for the position cards."""
from typing import Any, Dict, Iterable, List, Optional


def _price(order: Optional[Dict[str, Any]]) -> Optional[str]:
    return order.get("price") if order else None


def build_position_cards(
    positions: Iterable[Dict[str, Any]],
    open_trades: Optional[Iterable[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Build one card dict per open position.

    open_trades may be None (trade lookup failed); cards are then built without trade rows.
    """
    trades_by_id = {str(t.get("id")): t for t in (open_trades or [])}
    cards = []
    for position in positions:
        long_units = int(float(position.get("long", {}).get("units", 0)))
        short_units = int(float(position.get("short", {}).get("units", 0)))
        if long_units == 0 and short_units == 0:
            continue
        side = "long" if long_units != 0 else "short"
        units = long_units if side == "long" else short_units

        trade_rows = []
        for trade_id in position.get(side, {}).get("tradeIDs", []):
            trade = trades_by_id.get(str(trade_id))
            if trade is None:
                continue
            trade_rows.append({
                "id": str(trade_id),
                "units": int(float(trade.get("currentUnits", 0))),
                "pl": float(trade.get("unrealizedPL", 0.0)),
                "tp": _price(trade.get("takeProfitOrder")),
                "sl": _price(trade.get("stopLossOrder")),
            })

        cards.append({
            "instrument": position.get("instrument", ""),
            "direction": side.upper(),
            "units": abs(units),
            "trade_count": len(position.get(side, {}).get("tradeIDs", [])),
            "pl": float(position.get("unrealizedPL", 0.0)),
            "margin": float(position.get("marginUsed", 0.0)),
            "trades": trade_rows,
        })
    return cards
