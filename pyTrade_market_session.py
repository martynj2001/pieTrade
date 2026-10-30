from datetime import datetime, time, timezone, timedelta
import logging
import re


# Checks for Open markets.

# Market opening times dB in UTC, set for continuous 24 hour trading

# TODO : Add market switch based on the most profitable pair rather than simple time (Open/Close)
# FUTURE: This will be ineffective and should be modified to switch to the most profitable pair rather
# than simply being time based (ie dont leave a market because of time, stay until it becomes unprofitable)

market_sessions = {
    "sydney": {"open": 22, "close": 7},     # 22:00 - 07:00 UTC
    "tokyo": {"open": 0, "close": 9},       # 00:00 - 09:00 UTC
    "london": {"open": 8, "close": 17},     # 08:00 - 17:00 UTC
    "new_york": {"open": 13, "close": 22}   # 13:00 - 22:00 UTC
}

market_instruments = { # session best pair
    "sydney": "AUD_USD", 
    "tokyo": "USD_JPY",
    "london": "EUR_USD",
    "new_york": "GBP_USD"
}

def is_weekend(now: datetime):

    wd = now.weekday()  # Monday=0 ... Sunday=6

    if wd == 5:  # Saturday
        return True

    if wd == 6 and now.hour < 22:  # Sunday before 22:00 UTC
        return True

    return False

def get_open_session(now: datetime):

    hour = now.hour

    open_market = {
            "market": None,
            "instrument": None
        }

    if is_weekend(now):
        return open_market

    for name, hours in market_sessions.items():

        start = hours["open"]
        end = hours["close"]

        # Normal Session (no midnight wrap)
        if start <= end:
            if start <= hour < end:
                open_market["market"] = name
                open_market["instrument"] = market_instruments[name]
                return open_market
        #Overnight session (wraps past misdnight)
        else:
            if hour >= start or hour < end:
                open_market["market"] = name
                open_market["instrument"] = market_instruments[name]
                return open_market
    # Should never happen!        
    return open_market

session_pairs = {  # candidate pairs the AI agent may choose from, per session
    "sydney": ["AUD_USD", "NZD_USD", "USD_JPY"],
    "tokyo": ["USD_JPY", "AUD_USD", "EUR_JPY"],
    "london": ["EUR_USD", "GBP_USD", "USD_CHF", "EUR_GBP"],
    "new_york": ["GBP_USD", "EUR_USD", "USD_CAD", "USD_JPY"],
}

_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"}
_QUOTE_CURRENCIES = {"USD", "JPY", "CAD", "CHF", "AUD", "NZD", "GBP"}  # needed by get_quote_to_gbp

def get_open_sessions(now: datetime) -> list:
    """Return the names of ALL open sessions (overlaps give several; [] on weekends)."""
    if is_weekend(now):
        return []
    hour = now.hour
    names = []
    for name, hours in market_sessions.items():
        start = hours["open"]
        end = hours["close"]
        if (start <= hour < end) if start <= end else (hour >= start or hour < end):
            names.append(name)
    return names

def valid_session_pairs() -> dict:
    """Return session_pairs, logging an error and dropping any pair that fails its checks."""
    import pyTrade_instruments as instruments
    log = logging.getLogger("pyTrade.MarketSession")
    valid = {}
    for name, pairs in session_pairs.items():
        valid[name] = []
        for index, pair in enumerate(pairs):
            problem = None
            if not re.fullmatch(r"[A-Z]{3}_[A-Z]{3}", pair):
                problem = "bad format"
            else:
                base, quote = pair.split("_")
                expected_jpy = pair.endswith("_JPY")
                if base not in _CURRENCIES or quote not in _CURRENCIES:
                    problem = "unsupported currency"
                elif quote not in _QUOTE_CURRENCIES:
                    problem = "quote currency has no GBP conversion"
                elif (
                    instruments.pip_size(pair) != (0.01 if expected_jpy else 0.0001)
                    or instruments.min_sl_dist(pair) <= 0
                    or instruments.price_precision(pair) != (3 if expected_jpy else 5)
                ):
                    problem = "instrument settings do not match"
                elif index == 0 and pair != market_instruments.get(name):
                    problem = "first pair differs from the fixed session pair"
            if problem:
                log.error("Dropping %s from %s session pairs: %s", pair, name, problem)
            else:
                valid[name].append(pair)
    return valid

def is_market_closing(now: datetime, market: str, mins_before_closing=15):
# TODO: This may need to be 15mins to make sure trade are closed the last cycle be closing.
    hours = market_sessions[market]
    close_hour = hours["close"]
    close_dt = now.replace (hour=close_hour, minute=0, second=0, microsecond=0)

    # Handle midnight crossing sessions (like sydney)
    if hours["open"] > hours["close"]:
        if now.hour >= hours["open"]:
            close_dt += timedelta(days=1)

    # Claculate remaining market session time
    time_to_close = close_dt - now

    return timedelta(0) < time_to_close <= timedelta(minutes=mins_before_closing) 

def next_open(now: datetime):
    
    """Return the next UTC datetime when any market session is open.
    Walks forward one hour at a time (sessions start on the hour) and
    asks get_open_session() if a market is open. Gives up after 8 days.
    """
    candidate = now.replace(minute=0, second=0, microsecond=0)
    for _ in range(24 * 8):
        candidate += timedelta(hours=1)
        if get_open_session(candidate)["market"] is not None:
            return candidate
    return None
