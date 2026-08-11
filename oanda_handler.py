##########################################################
#      Main handler for OANDA Trading API                #
##########################################################
# Description:                                           #
#                                                        #
#                                                        #
#                                                        #
##########################################################
import pandas as pd
import pandas_ta_classic as ta
import config
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders

#define variables
timeframe = config.TIMEFRAME    # will eventually be set by GUI & then AI
instrument = config.INSTRUMENT  # will eventually be set by GUI & then AI

#Connect to Oanda API
def connect():
    #Set up OANDA connection
    client =  API(access_token=config.OANDA_API_KEY)
    return client

# Get latest Candle Data
def get_Candles(client):

    params = {
        "granularity": timeframe,
        "price": "A"
    }

    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    candles = client.request(r)['candles']
    candles

    #Convert to Panda's DataFrame
    data = []

    for c in candles:
        if c["complete"]:
            data.append({
                "time": c["time"],
                "open": float(c["ask"]["o"]),
                "high": float(c["ask"]["h"]),
                "low": float(c["ask"]["l"]),
                "close": float(c["ask"]["c"])
            })
    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"])
    return df

# Function: Place Order
def place_order(client, stop_loss, take_profit):

    # probaly build data structure in the strategy module
    data = {
        "order": {
            "instrument": instrument,
            "units": 1, 
            "type": "MARKET",
            "stopLossOnFill": {"price": f"{stop_loss:.3f}"},
            "takeProfitOnFill": {"price": f"{take_profit:.3f}"}
        }
    }
    r = orders.OrderCreate(config.OANDA_ACCOUNT_ID, data=data)
    client.request(r)
    print(f"Placed order for{instrument} with stop loss at {round(stop_loss, 3)} and take profit at {round(take_profit, 3)}")
    #print(f"Order response {r.response}")