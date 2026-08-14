##########################################################
#      Main handler for OANDA Trading API                #
##########################################################
# Description:                                           #
#                                                        #
#                                                        #
#                                                        #
##########################################################
import pandas as pd
import config
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders

#define variables
timeframe = config.TIMEFRAME    # will eventually be set by GUI & then AI
instrument = config.INSTRUMENT  # will eventually be set by GUI & then AI


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
def place_order(client, data):

    r = orders.OrderCreate(config.OANDA_ACCOUNT_ID, data=data)
    client.request(r)
    print(f"Placed order for{instrument} with stop loss at {round(data["order"]["stopLossOnFill"], 3)} and take profit at {round(data["order"]["takeProfitOnFill"], 3)}")
    