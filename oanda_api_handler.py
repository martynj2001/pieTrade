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
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.trades as trades
import time
import logging


#define variables
timeframe = config.TIMEFRAME    # will eventually be set by GUI & then AI

# Get latest Candle Data
def get_Candles(client, inst, retries=5):

    params = {
        "granularity": timeframe,
        "price": "A", 
        "count": 200
    }

    candles = []

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
            return r.response
        except Exception as e:
            print(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None

# Function: Return Account Summary
def account_summery(client, retries=5):

    r = accounts.AccountSummary(accountID=config.OANDA_ACCOUNT_ID)

    for attempt in range(retries):
        try:
            client.request(r)
            summary = r.response["account"]
            # Convert numeric fields
            return {
                "balance": round(float(summary["balance"]), 2),
                "NAV": round(float(summary["NAV"]), 2),
                "marginAvailable": float(summary["marginAvailable"]),
                "marginUsed": float(summary["marginUsed"]),
                "unrealizedPL": round(float(summary["unrealizedPL"]), 2),
                "openTradeCount": int(summary["openTradeCount"]),
                "openPositionCount": int(summary["openPositionCount"]),
                "pl": float(summary["pl"])
            }
        except Exception as e:
            print(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None

# Function: Return current Open Positions
def open_positions(client, retries=5):

    r = positions.OpenPositions(accountID=config.OANDA_ACCOUNT_ID)

    for attempt in range(retries):
        try:
            pos = client.request(r)['positions']
            return pos #return response
        except Exception as e:
            print(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None

def close_position(client, instr, retries=5):

    close_posiiton_log = logging.getLogger("Close Position")

    data = {
          "longUnits": "ALL",
          "shortUnits": "ALL"
        }

    close_posiiton_log.debug(f'Closing open positions for: {instr}')

    # Close locking orders: TP/SL etc.
    results = close_tpsl_orders(client, instr)

    if not results:
        close_posiiton_log.debug("close_tpsl_orders() returned and empty list")
    #TODO: Deal with failing to close 1 TP/SL order - a false in the dict 'results'.
    r = positions.PositionClose(accountID=config.OANDA_ACCOUNT_ID, instrument=instr, data=data)
    for attempt in range(retries):
        try:
            response = client.request(r)
            return response #return response
        except Exception as e:
            close_posiiton_log.debug(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None

def get_tp_sl_orders(client, instr, retries=5):

    tpsl = ["STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP_LOSS"]
    tpsl_orders = []

    r = orders.OrderList(config.OANDA_ACCOUNT_ID)

    for attempt in range(retries):
        try:
            orders_res = client.request(r)["orders"]
            for order in orders_res:
                if order["instrument"] == instr and order["type"] in tpsl:
                    tpsl_orders.append(order["id"])
            return tpsl_orders
        except Exception as e:
            print(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None

def close_tpsl_orders(client, instr, retries=5):

    close_posiiton_log = logging.getLogger("Close Position")

    #Get open tp & sl child orders for given instrument
    order_nos = get_tp_sl_orders(client, instr)
    closure_results = {}

    if not order_nos:
        # No Tp/SL orders to close
        close_posiiton_log.debug("No RP/SL orders to close")
        return closure_results

    for orderID in order_nos:
        success = False
        for attempt in range(retries):
            try:
                r = orders.OrderCancel(config.OANDA_ACCOUNT_ID, orderID)
                client.request(r)
                success = True
                break
            except Exception as e:
                print(f'Request failed (attempt: {attempt + 1}): {e}')
                time.sleep(1)
        closure_results[orderID] = success
        if not success:
            close_posiiton_log.debug(f"Failed to cancel order {orderID} after {retries} attempts")
    return closure_results

def server_position_exists(client, instrument, retries=5):

    r = positions.OpenPositions(config.OANDA_ACCOUNT_ID)
    for attempt in range(retries):
        try:
            response = client.request(r)
        except Exception as e:
            print(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)

    for pos in response.get("positions", []):
        if pos["instrument"] == instrument:
            # Position exists AND has non-zero units
            long_units = int(pos["long"]["units"])
            short_units = int(pos["short"]["units"])
            if long_units != 0 or short_units != 0:
                return True

    return False

def getTradeTime(client, tradeID, retries=5):

    # Get trade details
    r = trades.TradeDetails(accountID=config.OANDA_ACCOUNT_ID, tradeID=tradeID)

    for attempt in range(retries):
        try:
            trade = client.request(r)["trade"]["openTime"]
            return trade
        except Exception as e:
            print(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None
            
    

