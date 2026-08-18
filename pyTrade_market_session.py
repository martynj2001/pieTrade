from datetime import datetime, timezone
import time

# Checks for Open markets.

# Market opening times dB in UTC, set for continuous 24 hour trading

market_sessions = {
    "sydney": {"open": 22, "close": 0},     # 22:00 - 00:00 UTC
    "tokyo": {"open": 0, "close": 8},       # 00:00 - 08:00 UTC
    "london": {"open": 8, "close": 17},     # 08:00 - 17:00 UTC
    "new_york": {"open": 17, "close": 22}   # 17:00 - 22:00 UTC
}

market_instruments = {
    "sydney": "AUD_USD", 
    "tokyo": "USD_JPY",
    "london": "EUR_USD",
    "new_york": "GBP_USD"
}

def getOpenInstr(session):
    return market_instruments[session]

def getSession():

    current_time = datetime.now(timezone.utc)
    hour = current_time.hour

    open_market = {
        "market": "",
        "instrument": ""
    }

    for name, hours in market_sessions.items():

        start = hours["open"]
        end = hours["close"]

        if start <= end:
            # Normal day session
            if start <= hour < end: # Open market
                open_market["market"] = name
                open_market["instrument"] = getOpenInstr(name)
        else:
            # Night session
            if hour >= start or hour < end:
                open_market["market"] = name
                open_market["instrument"] = getOpenInstr(name)

    return open_market