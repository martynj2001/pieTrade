"""Standalone: record how each AI-agent decision hour actually moved (run manually or by cron)."""
import json
from datetime import datetime, timedelta, timezone

import oandapyV20.endpoints.instruments as instruments_ep
from oandapyV20 import API

import config
import pyTrade_instruments as instruments
import pyTrade_trades_db as trades_db


def fetch_candles(client: API, instrument: str, start: datetime) -> list[dict]:
    """M15 mid candles from `start` to start + 1 hour."""
    params = {
        "granularity": "M15",
        "price": "M",
        "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": (start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    request = instruments_ep.InstrumentsCandles(instrument=instrument, params=params)
    return [c for c in client.request(request)["candles"] if "mid" in c]


def main() -> None:
    client = API(access_token=config.OANDA_API_KEY.strip(), environment=config.OANDA_ENVIRON)
    now = datetime.now(timezone.utc)
    with trades_db._connection() as connection:
        decisions = connection.execute(
            """
            SELECT id, target_hour, candidates FROM agent_decisions d
            WHERE status = 'ok'
              AND NOT EXISTS (SELECT 1 FROM agent_outcomes o WHERE o.decision_id = d.id)
            """
        ).fetchall()

    processed = 0
    for decision in decisions:
        target = datetime.fromisoformat(decision["target_hour"])
        if target + timedelta(hours=1, minutes=5) > now:
            continue
        atr_by_instrument = {c["instrument"]: c["atr_pips"] for c in json.loads(decision["candidates"] or "[]")}
        for instrument, atr_pips in atr_by_instrument.items():
            candles = fetch_candles(client, instrument, target)
            if not candles:
                continue
            pip = instruments.pip_size(instrument)
            high = max(float(c["mid"]["h"]) for c in candles)
            low = min(float(c["mid"]["l"]) for c in candles)
            range_pips = (high - low) / pip
            net_pips = (float(candles[-1]["mid"]["c"]) - float(candles[0]["mid"]["o"])) / pip
            trades_db.insert_row("agent_outcomes", {
                "decision_id": decision["id"],
                "instrument": instrument,
                "range_pips": range_pips,
                "net_move_pips": net_pips,
                "efficiency": abs(net_pips) / range_pips if range_pips else 0.0,
                "range_atr": range_pips / atr_pips if atr_pips else None,
                "candles": len(candles),
            })
        processed += 1
    print(f"Processed {processed} decision(s)")


if __name__ == "__main__":
    main()
