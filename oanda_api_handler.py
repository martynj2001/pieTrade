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

logger = logging.getLogger("oanda_api_handler")

#define variables
timeframe = config.TIMEFRAME    # will eventually be set by GUI & then AI

# Get latest Candle Data
def get_Candles(client, inst, retries=5, granularity=None):

    params = {
        "granularity": granularity or timeframe,
        "price": "A", 
        "count": 200
    }

    r = instruments.InstrumentsCandles(instrument=inst, params=params)
    for attempt in range(retries):
        try:
            candles = client.request(r)['candles']
            break
        except Exception as e:
            logger.error(f'Request failed (attempt: {attempt + 1}): {e}')
            if attempt == retries - 1:
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
            logger.error(f'Request failed (attempt: {attempt + 1}): {e}')
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
            logger.error(f'Request failed (attempt: {attempt + 1}): {e}')
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
            logger.error(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None

def open_trades(client, retries=5):
    """Return all open trades (units, unrealised P/L, TP/SL orders), or None on failure."""
    r = trades.OpenTrades(accountID=config.OANDA_ACCOUNT_ID)

    for attempt in range(retries):
        try:
            return client.request(r)['trades']
        except Exception as e:
            logger.error(f'Request failed fetching open trades (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None

def close_position(client, instr, retries=5):

    close_position_log = logging.getLogger("close_position")
    close_position_log.debug("Attempting to Close Position")

    # Only request closure of the side(s) that actually hold units. OANDA
    # rejects a CLOSEOUT request for a side with no position
    # (CLOSEOUT_POSITION_DOESNT_EXIST), and since longUnits/shortUnits are
    # closed in a single batched transaction, that rejection also drags down
    # the valid side (CLOSEOUT_POSITION_REJECT) - resulting in the whole
    # close failing even though a real position exists on the other side.
    long_units, short_units = get_position_units(client, instr)

    if long_units is None and short_units is None:
        close_position_log.error(f'Could not determine open units for {instr}; aborting position close')
        return None

    data = {}
    if long_units:
        data["longUnits"] = "ALL"
    if short_units:
        data["shortUnits"] = "ALL"

    if not data:
        close_position_log.debug(f'No open long or short units for {instr}; nothing to close')
        return {}

    close_position_log.debug(f'Closing open positions for: {instr}')

    # Close locking orders: TP/SL etc.
    results = close_tpsl_orders(client, instr)

    if results is None:
        # None indicates an API failure while fetching/cancelling TP/SL orders,
        # as opposed to an empty dict which means there was nothing to cancel.
        close_position_log.error(
            f'Failed to retrieve/cancel TP/SL orders for {instr}; aborting position close'
        )
        return None

    failed_orders = [order_id for order_id, success in results.items() if not success]
    if failed_orders:
        close_position_log.error(
            f'Failed to cancel TP/SL order(s) {failed_orders} for {instr}; aborting position close'
        )
        return None

    if not results:
        close_position_log.debug("close_tpsl_orders() returned an empty dict - no TP/SL orders to cancel")

    r = positions.PositionClose(accountID=config.OANDA_ACCOUNT_ID, instrument=instr, data=data)
    for attempt in range(retries):
        try:
            response = client.request(r)
            return response #return response
        except Exception as e:
            close_position_log.debug(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None

def get_position_units(client, instr, retries=5):
    """Return (long_units, short_units) as ints for the given instrument's
    open position. Returns (0, 0) if the instrument has no open position.
    Returns (None, None) if the request could not be completed after retries.
    """

    get_units_log = logging.getLogger("get_position_units")

    r = positions.OpenPositions(accountID=config.OANDA_ACCOUNT_ID)
    for attempt in range(retries):
        try:
            response = client.request(r)
            for pos in response.get("positions", []):
                if pos["instrument"] == instr:
                    long_units = int(pos.get("long", {}).get("units", 0))
                    short_units = int(pos.get("short", {}).get("units", 0))
                    get_units_log.debug(
                        f"Units for instrument {instr}: long={long_units}, short={short_units}"
                    )
                    return long_units, short_units
            get_units_log.debug(f"No open position found for instrument {instr}")
            return 0, 0
        except Exception as e:
            get_units_log.error(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None, None

def get_position_trade_ids(client, instr, retries=5):

    get_td_id = logging.getLogger("get_position_trade_ids")

    r = positions.OpenPositions(accountID=config.OANDA_ACCOUNT_ID)
    for attempt in range(retries):
        try:
            response = client.request(r)
            for pos in response.get("positions", []):
                if pos["instrument"] == instr:
                    trade_ids = []
                    trade_ids += pos.get("long", {}).get("tradeIDs", [])
                    trade_ids += pos.get("short", {}).get("tradeIDs", [])
                    get_td_id.debug(f"Trade IDs for instrument {instr}: {trade_ids}")
                    return trade_ids
            return []
        except Exception as e:
            get_td_id.error(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return []

def get_tp_sl_orders(client, instr, retries=5):

    get_tpsl = logging.getLogger("get_tp_sl_orders")

    tpsl = ["STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP_LOSS"]
    tpsl_orders = []
    get_tpsl.debug(f"Getting TP/SL orders for instrument: {instr}")

    # TP/SL child orders are linked to a tradeID, not an instrument.
    # First resolve which open trades belong to this instrument's position.
    trade_ids = {str(tid) for tid in get_position_trade_ids(client, instr)}
    if not trade_ids:
        get_tpsl.debug(f"No open trades found for instrument {instr}")
        return tpsl_orders
    get_tpsl.debug(f"Resolved trade IDs for instrument {instr}: {trade_ids}")
    r = orders.OrdersPending(config.OANDA_ACCOUNT_ID)
    for attempt in range(retries):
        try:
            orders_res = client.request(r)["orders"]
            get_tpsl.debug(f"Pending orders response for instrument {instr}: {orders_res}")
            for order in orders_res:
                if order.get("type") in tpsl and str(order.get("tradeID")) in trade_ids:
                    tpsl_orders.append(order["id"])
                    get_tpsl.debug(f"Found TP/SL order for instrument {instr}: {order['id']}")
            get_tpsl.debug(f"Total TP/SL orders found for instrument {instr}: {len(tpsl_orders)}")
            return tpsl_orders
        except Exception as e:
            get_tpsl.error(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    # All retries exhausted without success - distinguish this API failure (None)
    # from "no TP/SL orders found" (empty list) so callers can react appropriately.
    return None

def close_tpsl_orders(client, instr, retries=5):

    close_position_log = logging.getLogger("close_tpsl_orders")
    close_position_log.debug(f"Closing TP/SL orders for instrument: {instr}")

    #Get open tp & sl child orders for given instrument
    order_nos = get_tp_sl_orders(client, instr)

    if order_nos is None:
        # API failure while fetching TP/SL orders - propagate as failure, not "nothing to close"
        close_position_log.error(f"Failed to fetch TP/SL orders for {instr} after retries")
        return None

    closure_results = {}

    if not order_nos:
        # Empty list: no TP/SL orders exist for this instrument - nothing to cancel
        close_position_log.debug("No TP/SL orders to close")
        return closure_results

    for orderID in order_nos:
        success = False
        for attempt in range(retries):
            try:
                r = orders.OrderCancel(config.OANDA_ACCOUNT_ID, orderID)
                client.request(r)
                success = True
                close_position_log.debug(f"Successfully cancelled order {orderID}")
                break
            except Exception as e:
                close_position_log.error(f'Request failed (attempt: {attempt + 1}): {e}')
                time.sleep(1)
        closure_results[orderID] = success
        if not success:
            close_position_log.error(f"Failed to cancel order {orderID} after {retries} attempts")
    return closure_results

def server_position_exists(client, instrument, retries=5):

    r = positions.OpenPositions(config.OANDA_ACCOUNT_ID)
    for attempt in range(retries):
        try:
            response = client.request(r)
            for pos in response.get("positions", []):
                if pos["instrument"] == instrument:
                    # Position exists AND has non-zero units
                    long_units = int(pos["long"]["units"])
                    short_units = int(pos["short"]["units"])
                    if long_units != 0 or short_units != 0:
                        return True
                    return False
            # Request succeeded but no matching instrument was found - the
            # position doesn't exist, so stop here instead of retrying.
            return False
        except Exception as e:
            logger.error(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return False

def getTradeTime(client, tradeID, retries=5):

    # Get trade details
    r = trades.TradeDetails(accountID=config.OANDA_ACCOUNT_ID, tradeID=tradeID)

    for attempt in range(retries):
        try:
            trade = client.request(r)["trade"]["openTime"]
            return trade
        except Exception as e:
            logger.error(f'Request failed (attempt: {attempt + 1}): {e}')
            time.sleep(1)
    return None


def getTradeDetails(client, tradeID, retries=5):
    """Return OANDA's full trade details, including realized close data."""
    r = trades.TradeDetails(
        accountID=config.OANDA_ACCOUNT_ID,
        tradeID=tradeID,
    )
    for attempt in range(retries):
        try:
            return client.request(r).get("trade")
        except Exception as e:
            logger.error(
                "Request failed while fetching trade %s (attempt: %s): %s",
                tradeID,
                attempt + 1,
                e,
            )
            time.sleep(1)
    return None
            
    
