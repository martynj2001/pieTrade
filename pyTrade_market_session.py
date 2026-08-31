from datetime import datetime, time, timezone


# Checks for Open markets.

# Market opening times dB in UTC, set for continuous 24 hour trading

# FUTURE: This will be ineffective and should be modified to switch to the most profitable pair rather
# than simply being time based (ie dont leave a market because of time, stay until it becomes unprofitable)

market_sessions = {
    "sydney": {"open": 22, "close": 7},     # 22:00 - 00:00 UTC
    "tokyo": {"open": 0, "close": 8},       # 00:00 - 08:00 UTC
    "london": {"open": 8, "close": 17},     # 08:00 - 17:00 UTC
    "new_york": {"open": 17, "close": 22}   # 17:00 - 22:00 UTC
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
            "market": "",
            "instrument": "",

        }

    if not is_weekend(now):

        for name, hours in market_sessions.items():

            start = hours["open"]
            end = hours["close"]

            if start <= end:
                if start <= hour < end:
                    open_market["market"] = name
                    open_market["instrument"] = market_instruments[name]
                    return open_market
            else:
                if hour >= start or hour < end:
                    open_market["market"] = name
                    open_market["instrument"] = market_instruments[name]
                    return open_market
    return None

'''def getOpenInstr(session):
    return market_instruments[session]


def getSession():

    current_time = datetime.now(timezone.utc)
    print(current_time)
    hour = current_time.hour
    day = current_time.weekday()

    open_market = {
        "market": "",
        "instrument": "",
        "day": day
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

    return open_market'''