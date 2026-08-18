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
from oandapyV20.exceptions import V20Error
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders
import time


#define variables
timeframe = config.TIMEFRAME    # will eventually be set by GUI & then AI
#instrument = config.INSTRUMENT  # will eventually be set by GUI & then AI


# Get latest Candle Data
def get_Candles(client, inst, retries=5):

    params = {
        "granularity": timeframe,
        "price": "A", 
        "count": 200
    }

    r = instruments.InstrumentsCandles(instrument=inst, params=params)
    for attempt in range(retries):
        try:
            candles = client.request(r)['candles']
            break
        except Exception as e:
            print(f'Request failed (attempt: {attempt + 1}): {e}')
            if attempt == retries:
                return None
            time.sleep(1)

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
def place_order(client, data, retries=5):

    r = orders.OrderCreate(config.OANDA_ACCOUNT_ID, data=data)
    for attempt in range(retries):
            try:
                client.request(r)
                return #return response
            except Exception as e:
                print(f'Request failed (attempt: {attempt + 1}): {e}')
                time.sleep(1)
    return None
   
    