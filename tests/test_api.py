import sqlite3

import pytest
from fastapi.testclient import TestClient

from api import analytics as an

SCHEMA = """
CREATE TABLE trades (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_id TEXT UNIQUE, instrument TEXT,
 direction TEXT, strategy TEXT, entry_time DATETIME, exit_time DATETIME, entry_price REAL,
 exit_price REAL, stop_loss REAL, take_profit REAL, units INTEGER, risk_amount REAL, status TEXT,
 close_reason TEXT, pnl_currency REAL, pnl_pips REAL, duration_minutes INTEGER, session TEXT,
 created_at DATETIME);
CREATE TABLE trade_signals (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_id TEXT, ema20 REAL,
 ema50 REAL, atr14 REAL, adx REAL, trend_strength REAL, rejection_candle BOOLEAN,
 pullback_detected BOOLEAN, close_price REAL, high_price REAL, low_price REAL,
 signal_timestamp DATETIME);
CREATE TABLE trade_events (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_id TEXT, event_time DATETIME,
 event_type TEXT, message TEXT);
"""

ROWS = [  # trade_id, instr, dir, entry, exit, entry_p, exit_p, sl, tp, status, pnl, dur, session
    ("1", "EUR_USD", "BUY", "2026-01-01T08:00", "2026-01-01T10:00", 1.10, 1.12, 1.09, 1.12, "CLOSED", 10, 120, "london"),
    ("2", "EUR_USD", "SELL", "2026-01-02T08:00", "2026-01-02T09:00", 1.10, 1.11, 1.11, 1.08, "CLOSED", -5, 60, "london"),
    ("3", "USD_JPY", "BUY", "2026-01-03T00:00", "2026-01-03T04:00", 150, 150.5, 149, 152, "CLOSED", -15, 240, "tokyo"),
    ("4", "USD_JPY", "BUY", "2026-01-04T00:00", None, 150, None, 149, 152, "OPEN", None, None, "tokyo"),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    for r in ROWS:
        c.execute("INSERT INTO trades (trade_id,instrument,direction,entry_time,exit_time,entry_price,"
                  "exit_price,stop_loss,take_profit,status,pnl_currency,duration_minutes,session)"
                  " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", r)
    c.execute("INSERT INTO trade_signals (trade_id, atr14) VALUES ('1', 0.001), ('2', 0.005), ('3', 0.5)")
    c.execute("INSERT INTO trade_events (trade_id,event_time,event_type,message) VALUES ('1','2026-01-01','OPEN','x')")
    c.commit()
    c.close()
    monkeypatch.setenv("PYTRADE_DB", str(path))
    from api.main import app
    return TestClient(app)


def test_health_and_meta(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/meta").json()["instrument"] == ["EUR_USD", "USD_JPY"]


def test_list_filter_sort_page(client):
    r = client.get("/api/trades", params={"instrument": "eur_usd", "sort": "pnl_currency", "order": "asc"}).json()
    assert r["total"] == 2 and [t["trade_id"] for t in r["items"]] == ["2", "1"]
    assert len(client.get("/api/trades", params={"limit": 1}).json()["items"]) == 1
    assert client.get("/api/trades", params={"sort": "x; DROP"}).status_code == 400


def test_detail(client):
    d = client.get("/api/trades/1").json()
    assert d["trade"]["instrument"] == "EUR_USD" and len(d["signals"]) == 1 and len(d["events"]) == 1
    assert client.get("/api/trades/nope").status_code == 404


def test_db_is_read_only(client):
    import api.db as db
    gen = db.get_conn()
    conn = next(gen)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM trades")


def test_analytics_endpoints(client):
    s = client.get("/api/analytics/summary").json()
    assert s["trades"] == 3 and s["win_rate"] == 33.33 and s["profit_factor"] == 0.5
    inst = {r["instrument"]: r for r in client.get("/api/analytics/by-instrument").json()}
    assert inst["EUR_USD"]["win_rate"] == 50.0
    assert client.get("/api/analytics/holding-time").json()["overall"]["avg_minutes"] == 140
    ex = client.get("/api/analytics/exit-reasons").json()
    assert ex["take_profit"]["count"] == 1 and ex["stop_loss"]["count"] == 1
    assert len(client.get("/api/analytics/atr-ranges", params={"buckets": 3}).json()) == 3
    dd = client.get("/api/analytics/drawdown").json()
    assert dd["max_drawdown"] == 20 and dd["curve"][-1]["equity"] == -10
    assert client.get("/api/analytics/by-session", params={"direction": "BUY"}).json()[0]["trades"] >= 1


def test_profit_factor_no_losses():
    assert an.profit_factor([{"pnl_currency": 5}]) is None
