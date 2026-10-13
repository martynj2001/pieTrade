from datetime import datetime, time, timezone, timedelta


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

