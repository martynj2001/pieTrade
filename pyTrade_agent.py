"""AI pair/market selector: chooses which (market, instrument) the bot watches for an hour."""
import json
import logging
import re
import sqlite3
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas_ta_classic as ta
from oandapyV20 import API

import config
import oanda_api_handler as oanda
import pyTrade_instruments as instruments
import pyTrade_market_session as market
import pyTrade_trades_db as trades_db

logger = logging.getLogger("pyTrade.Agent")

SYSTEM = (
    "You select ONE forex pair and market session to trade for the next hour for an "
    "automated bot. The bot trades M15 EMA-pullback and Donchian-breakout strategies, "
    "which only work in trending, volatile conditions; it rejects entries unless "
    "ADX(14) > 24 and the H1 trend agrees with the trade direction. Prefer candidates "
    "with higher adx, larger h1_distance_atr and volatility_expanding true. Choose ONLY "
    "from the candidates given, copying the market and instrument strings exactly. Reply "
    "with ONLY a JSON object: {\"market\": \"...\", \"instrument\": \"...\", \"reason\": "
    "\"<max 20 words>\"}."
)

RETRY_MINUTES = 5


class AgentPlanner:
    """Plans the next hour's (market, instrument) on a background thread."""

    def __init__(self, trade_guards, news_filter) -> None:
        self.trade_guards = trade_guards
        self.news_filter = news_filter
        self.plans: dict[datetime, dict] = {}
        self.pending: Optional[tuple[datetime, Future]] = None
        self.retry_after: Optional[datetime] = None
        self.last_result: Optional[dict] = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._oanda: Optional[API] = None

    def tick(self, now: datetime) -> None:
        """Collect a finished plan and submit a new request when needed; never blocks."""
        if self.pending is not None and self.pending[1].done():
            hour, future = self.pending
            self.pending = None
            try:
                plan = future.result()
            except Exception:
                logger.exception("Agent plan request failed")
                plan = None
            if plan is None:
                self.retry_after = now + timedelta(minutes=RETRY_MINUTES)
                self.last_result = {
                    "status": "failed", "time": now.isoformat(),
                    "retry_at": self.retry_after.isoformat(),
                }
            else:
                self.plans[hour] = plan
                self.last_result = {"status": "ok", "time": now.isoformat(), "retry_at": None}

        current_hour = now.replace(minute=0, second=0, microsecond=0)
        for hour in [h for h in self.plans if h < current_hour]:
            del self.plans[hour]

        if self.pending is not None or (self.retry_after is not None and now < self.retry_after):
            return
        target = current_hour + timedelta(hours=1) if now.minute >= 55 else current_hour
        if target not in self.plans:
            self.pending = (target, self._executor.submit(self._make_plan, target))
            self.last_result = {"status": "waiting", "time": now.isoformat(), "retry_at": None}

    def current_plan(self, now: datetime) -> Optional[dict]:
        """Plan for the current hour, only if its market is open now."""
        plan = self.plans.get(now.replace(minute=0, second=0, microsecond=0))
        if plan is not None and plan["market"] in market.get_open_sessions(now):
            return plan
        return None

    def next_plan(self, now: datetime) -> Optional[dict]:
        """Plan already made for the next hour, if any."""
        return self.plans.get(now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))

    def _safe(self, text: str) -> str:
        """Remove API keys from text before it is logged or stored."""
        for name in ("ANTHROPIC_API_KEY", "OANDA_API_KEY"):
            key = str(getattr(config, name, "") or "").strip()
            if key:
                text = text.replace(key, "***")
        return text

    def _client(self) -> API:
        if self._oanda is None:
            self._oanda = API(access_token=config.OANDA_API_KEY.strip(), environment=config.OANDA_ENVIRON)
        return self._oanda

    def _stats(self, instrument: str) -> Optional[dict]:
        """Trend/volatility stats for one instrument, or None if its data is unusable."""
        try:
            m15 = oanda.get_Candles(self._client(), instrument)
            h1 = oanda.get_Candles(self._client(), instrument, granularity="H1")
            columns = ["open", "high", "low", "close"]
            for df in (m15, h1):
                if df is None or len(df) < 60 or df[columns].isna().any().any():
                    return None
            adx = float(self.trade_guards.calculate_adx(m15).iloc[-1])
            atr = ta.atr(m15["high"], m15["low"], m15["close"], length=14)
            atr_last = float(atr.iloc[-1])
            atr_mean = float(atr.iloc[-14:].mean())
            h1_close = float(h1["close"].iloc[-1])
            h1_ema = float(h1["close"].ewm(span=50, adjust=False).mean().iloc[-1])
            h1_atr = float(ta.atr(h1["high"], h1["low"], h1["close"], length=14).iloc[-1])
            values = (adx, atr_last, atr_mean, h1_close, h1_ema, h1_atr)
            if any(v != v for v in values) or h1_atr <= 0:
                return None
            return {
                "adx": round(adx, 1),
                "atr_pips": round(atr_last / instruments.pip_size(instrument), 1),
                "volatility_expanding": atr_last > atr_mean,
                "h1_trend": "up" if h1_close > h1_ema else "down",
                "h1_distance_atr": round(abs(h1_close - h1_ema) / h1_atr, 2),
            }
        except Exception:
            logger.exception("Could not build stats for %s", instrument)
            return None

    def _make_plan(self, target: datetime) -> Optional[dict]:
        """Ask the model for the target hour's pair and always record one decision row."""
        model = getattr(config, "AGENT_MODEL", "claude-haiku-5-5")
        row = {
            "decision_time": datetime.now(timezone.utc).isoformat(),
            "target_hour": target.isoformat(),
            "mode": "shadow" if getattr(config, "AGENT_SHADOW", True) else "live",
            "status": "error",
            "model": model,
        }
        plan = None
        try:
            plan = self._decide(target, model, row)
        except Exception as exc:
            row["status"] = "error"
            row["error"] = self._safe(f"{type(exc).__name__}: {exc}")
            logger.error("Agent request failed: %s", row["error"])
        try:
            trades_db.insert_row("agent_decisions", row)
        except (OSError, sqlite3.Error, ValueError):
            logger.exception("Could not save agent decision")
        return plan

    def _decide(self, target: datetime, model: str, row: dict) -> Optional[dict]:
        """Build candidates, call the model and validate its answer (fills `row`)."""
        probe = target + timedelta(minutes=1)
        pairs = market.valid_session_pairs()
        found = [(s, i) for s in market.get_open_sessions(probe) for i in pairs.get(s, [])]
        fixed = market.get_open_session(probe)
        row["fixed_market"] = fixed["market"]
        row["fixed_instrument"] = fixed["instrument"]

        blocked = self.news_filter.blocked_during(target, target + timedelta(hours=1))
        excluded = [{"market": s, "instrument": i} for s, i in found if set(i.split("_")) & blocked]
        row["excluded_news"] = json.dumps(excluded)

        stats: dict[str, Optional[dict]] = {}
        candidates = []
        for session, instrument in found:
            if {"market": session, "instrument": instrument} in excluded:
                continue
            if instrument not in stats:
                stats[instrument] = self._stats(instrument)
            if stats[instrument] is not None:
                candidates.append({"market": session, "instrument": instrument, **stats[instrument]})
        row["candidates"] = json.dumps(candidates)
        if not candidates:
            row["status"] = "no_candidates"
            return None
        row["baseline_instrument"] = max(candidates, key=lambda c: c["adx"])["instrument"]

        import anthropic  # lazy: the bot must start without the SDK or key
        client = anthropic.Anthropic(
            api_key=getattr(config, "ANTHROPIC_API_KEY", None) or None,
            max_retries=1, timeout=30.0,
        )
        started = time.monotonic()
        response = client.messages.create(
            model=model,
            max_tokens=300,
            system=SYSTEM,
            messages=[{"role": "user", "content": json.dumps(
                {"hour_utc": target.isoformat(), "candidates": candidates})}],
        )
        row["latency_s"] = round(time.monotonic() - started, 2)
        row["input_tokens"] = response.usage.input_tokens
        row["output_tokens"] = response.usage.output_tokens

        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        cleaned = re.sub(r"```(?:json)?", "", text)
        start = cleaned.find("{")
        try:
            answer, _ = json.JSONDecoder().raw_decode(cleaned[start:]) if start >= 0 else (None, 0)
        except ValueError:
            answer = None
        chosen = None
        if isinstance(answer, dict):
            chosen = next(
                (c for c in candidates
                 if c["market"] == answer.get("market") and c["instrument"] == answer.get("instrument")),
                None,
            )
        if chosen is None:
            row["status"] = "invalid"
            row["error"] = self._safe(text[:500])
            return None

        reason = str(answer.get("reason", ""))[:200]
        row.update(status="ok", market=chosen["market"], instrument=chosen["instrument"], reason=reason)
        return {
            "market": chosen["market"],
            "instrument": chosen["instrument"],
            "reason": reason,
            "target_hour": target.isoformat(),
            "decided_at": row["decision_time"],
            "latency_s": row["latency_s"],
            "fixed_market": fixed["market"],
            "fixed_instrument": fixed["instrument"],
        }
