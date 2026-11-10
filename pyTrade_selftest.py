#!/usr/bin/env python3
"""pyTrade offline self-test - safe to run with the markets CLOSED (e.g. weekends).

Run from the bot folder (same Python environment as the bot):

    python3 pyTrade_selftest.py              # full test, includes ONE real Anthropic call
    python3 pyTrade_selftest.py --no-api     # no real Anthropic call (fake model only)
    python3 pyTrade_selftest.py --outcomes   # also test pyTrade_agent_outcomes.py + report
    python3 pyTrade_selftest.py --keep-db    # keep the temporary test database

What it does
  * Uses made-up "pretend" clock times (mid-week 13:00 UTC), so the agent runs even
    though the real markets are shut. OANDA still returns the last 200 candles
    (Friday's) so the indicator maths is real.
  * Never places orders. Only reads OANDA candles/prices.
  * Writes to a TEMPORARY database, not pytrade.db (it also checks that your real
    database was not changed).
  * The real Anthropic call costs a fraction of a cent. Everything else uses a fake model.

A FAIL means either a bug or that this test assumed a name/behaviour that differs from
your code - read the detail next to it.
"""
import argparse
import importlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import traceback
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

parser = argparse.ArgumentParser(description="pyTrade offline self-test")
parser.add_argument("--no-api", action="store_true", help="skip the one real Anthropic call")
parser.add_argument("--outcomes", action="store_true",
                    help="also run pyTrade_agent_outcomes.py and the analysis report on the test DB")
parser.add_argument("--keep-db", action="store_true", help="keep the temporary test database")
ARGS = parser.parse_args()

COUNTS = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}


def _out(status, name, detail=""):
    COUNTS[status] += 1
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ""))


def check(name, ok, detail=""):
    _out("PASS" if ok else "FAIL", name, detail)


def warn(name, detail=""):
    _out("WARN", name, detail)


def skip(name, why=""):
    _out("SKIP", name, why)


def info(msg):
    print(f"  [INFO] {msg}")


def heading(title):
    print(f"\n=== {title} ===")


def utc(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


def last_midweek(hour=13):
    """Most recent Tue/Wed/Thu at `hour`:00 UTC that is already in the past."""
    now = datetime.now(timezone.utc)
    d = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    while d > now or d.weekday() not in (1, 2, 3):
        d -= timedelta(days=1)
    return d


# Fixed pretend times (UTC) for the session-table tests
SAT_NOON = utc(2026, 10, 31, 12)
SUN_2159 = utc(2026, 11, 1, 21, 59)
SUN_2200 = utc(2026, 11, 1, 22, 0)
WED_0300 = utc(2026, 11, 4, 3)
WED_1400 = utc(2026, 11, 4, 14)
FRI_2230 = utc(2026, 10, 30, 22, 30)

MODS = {}


def load(name):
    try:
        MODS[name] = importlib.import_module(name)
        return MODS[name], None
    except Exception as exc:  # noqa: BLE001
        MODS[name] = None
        return None, exc


def mod(name):
    return MODS.get(name)


# ----------------------------------------------------------------------------
# 1. Environment
# ----------------------------------------------------------------------------
def t_environment():
    heading("1. Environment and imports")
    info(f"Python {sys.version.split()[0]}")
    for name in ("config", "oanda_api_handler", "pyTrade_market_session", "pyTrade_instruments",
                 "pyTrade_trades_db", "pyTrade_trade_guards", "pyTrade_settings",
                 "pyTrade_news_filter", "pyTrade_agent"):
        m, exc = load(name)
        check(f"import {name}", m is not None, "" if m else repr(exc))
    try:
        import anthropic
        info(f"anthropic SDK {anthropic.__version__}")
    except Exception as exc:  # noqa: BLE001
        check("import anthropic", False, repr(exc))
    cfg = mod("config")
    if cfg:
        for attr in ("OANDA_API_KEY", "OANDA_ENVIRON", "ANTHROPIC_API_KEY"):
            check(f"config.{attr} is set", bool(str(getattr(cfg, attr, "")).strip()))
        info(f"AGENT_MODEL={getattr(cfg, 'AGENT_MODEL', 'claude-haiku-5-5 (default)')}  "
             f"AGENT_SHADOW={getattr(cfg, 'AGENT_SHADOW', True)}")
    agent_path = os.path.join(HERE, "pyTrade_agent.py")
    if os.path.exists(agent_path):
        src = open(agent_path, encoding="utf-8").read()
        if "identity" in src:
            check("agent asks for uncompressed replies (Accept-Encoding: identity)", True)
        else:
            warn("agent does not set Accept-Encoding: identity",
                 "the earlier 'Connection error' (decompression crash) will return")


# ----------------------------------------------------------------------------
# 2. Market sessions with pretend clock times
# ----------------------------------------------------------------------------
def t_sessions():
    heading("2. Market sessions (pretend clock times)")
    mk = mod("pyTrade_market_session")
    if mk is None:
        return skip("market sessions", "module did not import")
    if not hasattr(mk, "get_open_sessions"):
        return check("get_open_sessions() exists", False, "Prompt 2 section 1 not applied?")
    check("Saturday: nothing open",
          mk.get_open_session(SAT_NOON)["market"] is None and mk.get_open_sessions(SAT_NOON) == [])
    check("Sunday 21:59 UTC: nothing open", mk.get_open_sessions(SUN_2159) == [])
    check("Sunday 22:00 UTC: sydney opens", mk.get_open_sessions(SUN_2200) == ["sydney"])
    check("Wednesday 14:00: london + new_york", sorted(mk.get_open_sessions(WED_1400)) == ["london", "new_york"])
    check("Wednesday 03:00: sydney + tokyo", sorted(mk.get_open_sessions(WED_0300)) == ["sydney", "tokyo"])
    check("london closing flag at 16:50", mk.is_market_closing(utc(2026, 11, 4, 16, 50), "london"))
    check("london not closing at 16:30", not mk.is_market_closing(utc(2026, 11, 4, 16, 30), "london"))
    fri = mk.get_open_sessions(FRI_2230)
    if fri:
        warn("Friday 22:30 UTC is treated as OPEN", f"sessions={fri}. FX normally shuts on Friday evening "
             "(about 21:00 UTC in summer, 22:00 in winter), so the bot could run on stale prices late Friday")


# ----------------------------------------------------------------------------
# 3. Pair table vs pyTrade_instruments
# ----------------------------------------------------------------------------
def t_pairs():
    heading("3. Pair table vs pyTrade_instruments")
    mk, inst = mod("pyTrade_market_session"), mod("pyTrade_instruments")
    if mk is None or not hasattr(mk, "session_pairs") or not hasattr(mk, "valid_session_pairs"):
        return skip("pair table", "session_pairs / valid_session_pairs not found")
    raw, valid = mk.session_pairs, mk.valid_session_pairs()
    for session, pairs in raw.items():
        check(f"{session}: every pair passes validation", valid.get(session) == pairs,
              "" if valid.get(session) == pairs else f"kept {valid.get(session)}")
        check(f"{session}: first pair is the fixed fallback ({mk.market_instruments[session]})",
              bool(pairs) and pairs[0] == mk.market_instruments[session])
    if inst is None:
        return
    for pair in sorted({p for v in raw.values() for p in v}):
        jpy = pair.endswith("_JPY")
        want = (0.01, 0.1, 3) if jpy else (0.0001, 0.001, 5)
        try:
            got = (inst.pip_size(pair), inst.min_sl_dist(pair), inst.price_precision(pair))
            ok = all(abs(float(a) - float(b)) < 1e-12 for a, b in zip(got, want))
            check(f"{pair}: pip / min stop / precision", ok, f"got {got}, expected {want}")
        except Exception as exc:  # noqa: BLE001
            check(f"{pair}: instrument lookups", False, repr(exc))


# ----------------------------------------------------------------------------
# 4. OANDA data (works at weekends: returns Friday's last candles)
# ----------------------------------------------------------------------------
OANDA_CLIENT = None


def t_oanda():
    global OANDA_CLIENT
    heading("4. OANDA practice data (read-only)")
    cfg, oanda = mod("config"), mod("oanda_api_handler")
    if cfg is None or oanda is None:
        return skip("OANDA", "config / oanda_api_handler missing")
    from oandapyV20 import API
    OANDA_CLIENT = API(access_token=cfg.OANDA_API_KEY.strip(), environment=cfg.OANDA_ENVIRON)
    for gran in (None, "H1"):
        label = gran or "M15"
        df = oanda.get_Candles(OANDA_CLIENT, "EUR_USD", granularity=gran)
        if df is None or df.empty:
            check(f"EUR_USD {label} candles", False, "no data returned")
            continue
        check(f"EUR_USD {label} candles", len(df) >= 60, f"{len(df)} rows, last candle {df['time'].iloc[-1]}")
    mk = mod("pyTrade_market_session")
    quotes = sorted({p.split('_')[1] for v in getattr(mk, "session_pairs", {}).values() for p in v})
    for quote in quotes:
        rate = oanda.get_quote_to_gbp(OANDA_CLIENT, f"XXX_{quote}")
        check(f"GBP conversion for quote currency {quote}", rate is not None and rate > 0, f"rate={rate}")

    # Cache candle downloads so the many agent scenarios below stay fast
    original = oanda.get_Candles
    cache = {}

    def cached(client, inst, retries=5, granularity=None):
        key = (inst, granularity)
        if key not in cache:
            df = original(client, inst, retries=retries, granularity=granularity)
            if df is None:
                return None
            cache[key] = df
        return cache[key].copy()

    oanda.get_Candles = cached
    MODS["_oanda_original"] = original


# ----------------------------------------------------------------------------
# 5. News filter (uses the cached calendar, so it works at weekends)
# ----------------------------------------------------------------------------
def t_news():
    heading("5. News filter")
    nfm, cfg = mod("pyTrade_news_filter"), mod("config")
    if nfm is None:
        return skip("news filter", "module did not import")
    nf = nfm.NewsFilter()
    before = int(getattr(cfg, "NEWS_BEFORE_MIN", 30))
    after = int(getattr(cfg, "NEWS_AFTER_MIN", 15))
    info(f"window: {before} min before, {after} min after")
    now = datetime.now(timezone.utc)
    blocked_now = nf.blocked_currencies(now)
    check("blocked_currencies(now) runs", isinstance(blocked_now, set), f"{sorted(blocked_now)}")

    path = os.path.join(os.path.dirname(nfm.__file__), "news_cache.json")
    if not os.path.exists(path):
        return skip("calendar checks", f"{path} not found - the feed may not have been fetched")
    raw = json.load(open(path, encoding="utf-8"))
    items = raw if isinstance(raw, list) else next((v for v in raw.values() if isinstance(v, list)), [])
    events = []
    for e in items:
        if e.get("impact") == "High":
            try:
                events.append((datetime.fromisoformat(e["date"]).astimezone(timezone.utc),
                               e["country"], e.get("title", "")))
            except Exception:  # noqa: BLE001
                pass
    events.sort()
    check("calendar cache has high-impact events", len(events) > 0, f"{len(events)} events")
    for t, cur, title in events[:3]:
        info(f"{t:%a %d %b %H:%M} UTC  {cur}  {title}")
    isolated = [x for x in events
                if all(abs((x[0] - y[0]).total_seconds()) > 3 * 3600 for y in events if y is not x)]
    if not isolated:
        return skip("window edge tests", "no high-impact event is isolated by 3 hours")
    t0, cur, title = isolated[0]
    info(f"testing around {t0:%a %d %b %H:%M} UTC {cur} {title}")
    m = timedelta(minutes=1)
    check("blocked at event time", cur in nf.blocked_currencies(t0))
    check("blocked just inside the 'before' window", cur in nf.blocked_currencies(t0 - (before - 1) * m))
    check("free just before the window", cur not in nf.blocked_currencies(t0 - (before + 1) * m))
    check("blocked just inside the 'after' window", cur in nf.blocked_currencies(t0 + (after - 1) * m))
    check("free just after the window", cur not in nf.blocked_currencies(t0 + (after + 1) * m))
    check("blocked_during: hour ending inside the window",
          cur in nf.blocked_during(t0 - timedelta(hours=1), t0 - (before - 5) * m))
    check("blocked_during: hour far away is clear",
          cur not in nf.blocked_during(t0 - timedelta(hours=3), t0 - timedelta(hours=2)))
    other = "EUR_GBP" if cur in ("AUD", "NZD") else "AUD_NZD"
    check(f"is_pair_blocked({cur}_USD) is True", nf.is_pair_blocked(f"{cur}_USD", t0))
    check(f"is_pair_blocked({other}) is False", not nf.is_pair_blocked(other, t0))


# ----------------------------------------------------------------------------
# 6. Settings store
# ----------------------------------------------------------------------------
def t_settings():
    heading("6. Settings store (read-only)")
    st = mod("pyTrade_settings")
    if st is None:
        return skip("settings", "module did not import")
    for key, ok_values in (("strategy_mode", ("dual", "single")), ("ai_agent_enabled", (True, False))):
        try:
            value = st.get(key)
            check(f"setting {key}", value in ok_values, f"value={value!r}")
        except Exception as exc:  # noqa: BLE001
            check(f"setting {key}", False, repr(exc))


# ----------------------------------------------------------------------------
# Test database + fake model
# ----------------------------------------------------------------------------
TMP_DIR = tempfile.mkdtemp(prefix="pytrade_selftest_")
TEST_DB = os.path.join(TMP_DIR, "selftest.db")
REAL_DB = None
FAKE = {"mode": "best"}


def count_rows(path, table="agent_decisions"):
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        con.close()
        return n
    except Exception:  # noqa: BLE001
        return None


def last_row():
    con = sqlite3.connect(TEST_DB)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM agent_decisions ORDER BY id DESC LIMIT 1").fetchone()
    con.close()
    return dict(row) if row else None


class _Usage:
    input_tokens = 111
    output_tokens = 22


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Msg:
    stop_reason = "end_turn"
    model = "fake"

    def __init__(self, text):
        self.content = [_Block(text)]
        self.usage = _Usage()


class _Messages:
    def create(self, **kw):
        mode = FAKE["mode"]
        if mode == "raise":
            raise RuntimeError("fake API failure")
        content = kw["messages"][0]["content"]
        if not isinstance(content, str):
            content = content[0]["text"] if isinstance(content[0], dict) else content[0].text
        candidates = json.loads(content)["candidates"]
        best = max(candidates, key=lambda c: c.get("adx", 0))
        pick = {"market": best["market"], "instrument": best["instrument"], "reason": "fake: highest ADX"}
        if mode == "invalid":
            pick = {"market": "london", "instrument": "XAU_USD", "reason": "not a candidate"}
        if mode == "garbage":
            return _Msg("I think EUR_USD looks good today!")
        text = json.dumps(pick)
        if mode == "fenced":
            text = "```json\n" + text + "\n```"
        return _Msg(text)


class FakeAnthropic:
    def __init__(self, *args, **kwargs):
        self.messages = _Messages()


class StubNews:
    """Stands in for NewsFilter so the scenarios do not depend on today's calendar."""

    def __init__(self, blocked=()):
        self.blocked = set(blocked)

    def blocked_during(self, start, end):
        return set(self.blocked)

    def blocked_currencies(self, now):
        return set(self.blocked)

    def is_pair_blocked(self, instrument, now):
        return bool(set(instrument.split("_")) & self.blocked)


def new_planner(blocked=()):
    guards = mod("pyTrade_trade_guards").TradeGuards()
    return mod("pyTrade_agent").AgentPlanner(guards, StubNews(blocked))


def run_make_plan(planner, target):
    n0 = count_rows(TEST_DB) or 0
    started = time.time()
    try:
        plan, err = planner._make_plan(target), None
    except Exception as exc:  # noqa: BLE001
        plan, err = None, exc
    rows = (count_rows(TEST_DB) or 0) - n0
    return plan, err, rows, last_row(), time.time() - started


def candidate_pairs(row):
    try:
        return [(c["market"], c["instrument"]) for c in json.loads(row["candidates"])]
    except Exception:  # noqa: BLE001
        return []


# ----------------------------------------------------------------------------
# 7. Agent: real call + fake scenarios
# ----------------------------------------------------------------------------
def t_agent():
    global REAL_DB
    heading("7. Agent pipeline (pretend time: last Tue/Wed/Thu 13:00 UTC)")
    db, agent = mod("pyTrade_trades_db"), mod("pyTrade_agent")
    if db is None or agent is None or mod("pyTrade_trade_guards") is None:
        return skip("agent", "pyTrade_agent / trades_db / trade_guards missing")
    if not hasattr(db, "_DEFAULT_DB_PATH"):
        return skip("agent", "trades_db has no _DEFAULT_DB_PATH, so the test DB redirect cannot work")
    REAL_DB = os.path.abspath(db._DEFAULT_DB_PATH)
    real_before = count_rows(REAL_DB)
    db._DEFAULT_DB_PATH = TEST_DB
    MODS["_db_path_restore"] = REAL_DB
    db.create_database()
    con = sqlite3.connect(TEST_DB)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    con.close()
    for name in ("agent_decisions", "agent_outcomes", "v_agent_eval"):
        check(f"test DB has {name}", name in names)
    if "agent_decisions" not in names:
        return
    target = last_midweek(13)
    info(f"pretend hour: {target:%a %d %b %Y %H:%M} UTC (real markets are not involved)")

    # A. one REAL Anthropic call through your real code path
    if ARGS.no_api:
        skip("real Anthropic call", "--no-api")
    else:
        plan, err, rows, row, secs = run_make_plan(new_planner(), target)
        if err is not None:
            info(f"exception: {err!r}  cause: {err.__cause__!r}")
        check("A real call: no exception, plan returned", err is None and plan is not None)
        check("A real call: exactly one agent_decisions row", rows == 1, f"{rows} rows")
        if row:
            check("A real call: row status is 'ok'", row["status"] == "ok",
                  f"status={row['status']} error={row['error']}")
            if row["status"] == "ok":
                check("A real call: pick is one of the candidates",
                      (row["market"], row["instrument"]) in candidate_pairs(row))
                check("A real call: tokens recorded", (row["input_tokens"] or 0) > 0,
                      f"in={row['input_tokens']} out={row['output_tokens']}")
                cost = (row["input_tokens"] or 0) * 0.10e-6 + (row["output_tokens"] or 0) * 0.50e-6
                info(f"AI picked {row['market']} {row['instrument']} in {secs:.1f}s "
                     f"(est. cost ${cost:.5f}). Reason: {row['reason']}")
                info(f"fixed pair would be {row['fixed_market']} {row['fixed_instrument']}; "
                     f"highest-ADX baseline is {row['baseline_instrument']}")
                for c in json.loads(row["candidates"]):
                    info(f"  {c['market']:<9}{c['instrument']:<8} adx={c.get('adx')} atr_pips={c.get('atr_pips')} "
                         f"vol_exp={c.get('volatility_expanding')} h1={c.get('h1_trend')} "
                         f"dist_atr={c.get('h1_distance_atr')}")

    # B-H. fake model scenarios (free, deterministic)
    import anthropic
    saved = {"anthropic": anthropic.Anthropic}
    anthropic.Anthropic = FakeAnthropic
    if hasattr(agent, "Anthropic"):
        saved["agent"] = agent.Anthropic
        agent.Anthropic = FakeAnthropic
    MODS["_fake_saved"] = saved
    try:
        FAKE["mode"] = "best"
        plan, err, rows, row, _ = run_make_plan(new_planner(), target)
        check("B fake model picks highest ADX: ok", err is None and plan is not None and row["status"] == "ok",
              f"err={err!r}")
        if plan and row:
            check("B pick equals the baseline pair", plan["instrument"] == row["baseline_instrument"])
            check("B row records mode/fixed pair", bool(row["mode"]) and bool(row["fixed_instrument"]),
                  f"mode={row['mode']} fixed={row['fixed_market']}/{row['fixed_instrument']}")

        FAKE["mode"] = "fenced"
        plan, err, rows, row, _ = run_make_plan(new_planner(), target)
        check("C reply wrapped in ```json fences is parsed", plan is not None and row["status"] == "ok",
              f"err={err!r}")

        FAKE["mode"] = "invalid"
        plan, err, rows, row, _ = run_make_plan(new_planner(), target)
        check("D invalid pair is rejected (status 'invalid', no plan)",
              plan is None and row is not None and row["status"] == "invalid",
              f"err={err!r} status={row and row['status']}")

        FAKE["mode"] = "garbage"
        plan, err, rows, row, _ = run_make_plan(new_planner(), target)
        check("E non-JSON reply is rejected safely",
              plan is None and row is not None and row["status"] in ("invalid", "error"),
              f"err={err!r} status={row and row['status']}")

        FAKE["mode"] = "raise"
        plan, err, rows, row, _ = run_make_plan(new_planner(), target)
        check("F API failure: no plan", plan is None)
        check("F API failure: an 'error' row is logged", rows == 1 and row and row["status"] == "error",
              f"exception_escaped={err!r} rows={rows}")

        FAKE["mode"] = "best"
        plan, err, rows, row, _ = run_make_plan(new_planner({"CHF"}), target)
        check("G CHF news block: no CHF pair chosen",
              plan is not None and "CHF" not in plan["instrument"], f"plan={plan} err={err!r}")
        check("G CHF news block: exclusions logged",
              bool(row and row["excluded_news"] and row["excluded_news"] not in ("[]", "")),
              f"excluded_news={row and row['excluded_news']}")

        plan, err, rows, row, _ = run_make_plan(
            new_planner({"USD", "EUR", "GBP", "JPY", "CAD", "CHF", "AUD", "NZD"}), target)
        check("H everything blocked: no plan, status 'no_candidates'",
              plan is None and row is not None and row["status"] == "no_candidates",
              f"err={err!r} status={row and row['status']}")

        t_schedule(target)
        t_bot(target)
        if ARGS.outcomes:
            t_outcomes()
    finally:
        anthropic.Anthropic = saved["anthropic"]
        if "agent" in saved:
            agent.Anthropic = saved["agent"]
        db._DEFAULT_DB_PATH = REAL_DB
    real_after = count_rows(REAL_DB)
    if real_before == real_after:
        check("your real pytrade.db was not changed by this test", True, f"agent_decisions rows: {real_after}")
    else:
        warn("real pytrade.db agent_decisions changed during the test",
             f"{real_before} -> {real_after}: something wrote to the real database (maybe a live bot)")


# ----------------------------------------------------------------------------
# 8. tick() / current_plan() scheduling with a pretend clock
# ----------------------------------------------------------------------------
def wait(future, timeout=240):
    try:
        future.result(timeout=timeout)
    except Exception:  # noqa: BLE001
        pass


def t_schedule(target):
    heading("8. Hourly scheduling with a pretend clock (tick / current_plan)")
    try:
        FAKE["mode"] = "best"
        p = new_planner()
        now = target - timedelta(minutes=4)  # 12:56 - the plan for 13:00 is requested early
        p.tick(now)
        check("12:56 tick submits a request for the next hour", p.pending is not None)
        if p.pending is None:
            return
        check("request is for the 13:00 hour", p.pending[0] == target, f"{p.pending[0]}")
        wait(p.pending[1])
        p.tick(now + timedelta(seconds=10))
        check("finished plan stored for 13:00", target in p.plans)
        plan = p.current_plan(target + timedelta(seconds=5))
        check("current_plan() at 13:00:05 returns the plan", plan is not None, f"{plan}")
        check("no plan for the 14:00 hour yet", p.current_plan(target + timedelta(hours=1, minutes=5)) is None)
        p.tick(now + timedelta(seconds=20))
        check("no duplicate request once the plan exists", p.pending is None)

        FAKE["mode"] = "raise"
        q = new_planner()
        q.tick(now)
        if q.pending is not None:
            wait(q.pending[1])
        q.tick(now + timedelta(seconds=10))
        check("failed request sets a retry time about 5 minutes ahead",
              q.retry_after is not None and q.retry_after > now + timedelta(minutes=4), f"{q.retry_after}")
        q.tick(now + timedelta(minutes=1))
        check("no new request during the retry wait", q.pending is None)
        q.tick(now + timedelta(minutes=6))
        check("request is retried after the wait", q.pending is not None)
        if q.pending is not None:
            wait(q.pending[1])
    except AttributeError as exc:
        skip("scheduling", f"planner is missing an attribute the test expects: {exc}")
    finally:
        FAKE["mode"] = "best"


# ----------------------------------------------------------------------------
# 9. Bot select_market() (the toggle / shadow / fallback logic)
# ----------------------------------------------------------------------------
def t_bot(target):
    heading("9. Bot select_market() fallback logic")
    cfg, st, mk = mod("config"), mod("pyTrade_settings"), mod("pyTrade_market_session")
    bot, exc = load("pyTrade_bot")
    if bot is None:
        return skip("bot", f"pyTrade_bot did not import: {exc!r}")
    if st is None:
        return skip("bot", "pyTrade_settings missing")
    real_get = st.get
    enabled = {"v": False}
    had_shadow = hasattr(cfg, "AGENT_SHADOW")
    old_shadow = getattr(cfg, "AGENT_SHADOW", None)

    def fake_get(key, *a, **k):
        return enabled["v"] if key == "ai_agent_enabled" else real_get(key, *a, **k)

    st.get = fake_get
    try:
        w = bot.pyTradeWorker()
        if not hasattr(w, "select_market"):
            return check("worker has select_market()", False, "Prompt 2 section 5 not applied?")
        now = target + timedelta(minutes=30)
        w.planner.plans[target] = {"market": "london", "instrument": "GBP_USD", "reason": "selftest"}

        enabled["v"] = False
        r = w.select_market(now)
        check("toggle OFF -> fixed sessions", r.get("source") == "fixed sessions", f"{r}")

        enabled["v"] = True
        r = w.select_market(SAT_NOON)
        check("weekend + toggle ON -> market None and no AI request fired",
              r["market"] is None and w.planner.pending is None, f"{r}")

        cfg.AGENT_SHADOW = True
        r = w.select_market(now)
        check("shadow mode -> still fixed sessions",
              r.get("source") == "fixed sessions" and r["market"] == mk.get_open_session(now)["market"], f"{r}")

        cfg.AGENT_SHADOW = False
        r = w.select_market(now)
        check("live mode -> AI plan used",
              r.get("source") == "AI agent" and r["instrument"] == "GBP_USD" and r["market"] == "london", f"{r}")

        w.planner.plans[target] = {"market": "tokyo", "instrument": "USD_JPY", "reason": "tokyo is shut at 13:30"}
        r = w.select_market(now)
        check("plan for a closed market -> fixed sessions", r.get("source") == "fixed sessions", f"{r}")
    except Exception as exc2:  # noqa: BLE001
        check("select_market scenarios ran", False, repr(exc2))
        traceback.print_exc()
    finally:
        st.get = real_get
        if had_shadow:
            cfg.AGENT_SHADOW = old_shadow
        elif hasattr(cfg, "AGENT_SHADOW"):
            del cfg.AGENT_SHADOW


# ----------------------------------------------------------------------------
# 10. Optional: outcomes script + analysis report (uses real OANDA history)
# ----------------------------------------------------------------------------
def t_outcomes():
    heading("10. Outcomes script and analysis report (--outcomes)")
    import runpy
    path = os.path.join(HERE, "pyTrade_agent_outcomes.py")
    if not os.path.exists(path):
        return skip("outcomes script", "pyTrade_agent_outcomes.py not found")
    n_dec = count_rows(TEST_DB) or 0
    info(f"{n_dec} test decisions; running the outcomes script against the test DB")
    old_argv = sys.argv
    sys.argv = [path]
    try:
        runpy.run_path(path, run_name="__main__")
    except SystemExit:
        pass
    except Exception as exc:  # noqa: BLE001
        check("outcomes script ran", False, repr(exc))
    finally:
        sys.argv = old_argv
    n_out = count_rows(TEST_DB, "agent_outcomes") or 0
    check("outcomes rows were written to the test DB", n_out > 0,
          f"{n_out} rows (0 may mean the script uses its own DB path)")
    try:
        from api.agent_analysis import build_report
    except Exception as exc:  # noqa: BLE001
        return skip("analysis report", f"api.agent_analysis not importable ({exc!r}) - Prompt 4 not built yet?")
    con = sqlite3.connect(f"file:{TEST_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        report = build_report(con, "all", None)
        check("build_report() runs on the test DB", isinstance(report, dict) and "available" in report,
              f"available={report.get('available')}")
        if report.get("available"):
            comp = report.get("comparison", {})
            info(f"comparison n={comp.get('n')} agent_eff={comp.get('agent_eff')} "
                 f"fixed_eff={comp.get('fixed_eff')} base_eff={comp.get('base_eff')}")
    finally:
        con.close()


# ----------------------------------------------------------------------------
def run(fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        check(f"{fn.__name__} completed without crashing", False, repr(exc))
        traceback.print_exc()


def main():
    started = time.time()
    print("pyTrade offline self-test  -  real time now:", datetime.now(timezone.utc).strftime("%a %d %b %Y %H:%M UTC"))
    for fn in (t_environment, t_sessions, t_pairs, t_oanda, t_news, t_settings, t_agent):
        run(fn)
    original = MODS.get("_oanda_original")
    if original is not None:
        mod("oanda_api_handler").get_Candles = original
    print("\n" + "=" * 60)
    print("SUMMARY  " + "  ".join(f"{k}: {v}" for k, v in COUNTS.items()) + f"   ({time.time() - started:.0f}s)")
    if COUNTS["FAIL"]:
        print("Some checks FAILED. Copy the output above and send it for diagnosis.")
    elif COUNTS["WARN"]:
        print("No failures, but read the WARN lines.")
    else:
        print("All checks passed.")
    if ARGS.keep_db:
        print(f"Test database kept at: {TEST_DB}")
    else:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
    return 1 if COUNTS["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())