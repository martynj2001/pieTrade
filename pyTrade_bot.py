
from PySide6.QtCore import QObject, Signal

from datetime import datetime, timezone
import time
from oandapyV20 import API
import oanda_api_handler as oanda
import EMA_Trend_following as ema
import pyTrade_market_session as market
import logging
import config

class OandaInfoFilter(logging.Filter):
    def filter(self, record):
        # Suppress only specific noisy INFO messages
        blocked = [
            "summary"
        ]

        # Only filter INFO logs, keep WARNING/ERROR untouched
        if record.levelno == logging.INFO:
            return not any(msg in record.getMessage() for msg in blocked)

        return True

class pyTradeWorker(QObject):

    msg = Signal(str)
    finished = Signal()
    market_info = Signal(dict)
    account = Signal(dict)
   
    def __init__(self):
        super().__init__()
        self.running = True

    def stop_bot(self):
        self.running = False

    def run_bot(self):

        #Configure logging
        logging.basicConfig(
            filename=f"{datetime.now(timezone.utc).strftime('%d%m%y-%H%M')}-pyTrade.log",
            level=logging.DEBUG if config.DEBUG_LOGGING else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
        )
        logger = logging.getLogger("pyTrade")
        val_logger = logging.getLogger("Validation")
        oanda_logger = logging.getLogger("oandapyV20.oandapyV20")
        # Apply logging filter
        # Attach filter to OANDA logger
        oanda_logger.addFilter(OandaInfoFilter())
        

        self.msg.emit("pyTrade Bot started and Log created.")
        logger.info("pyTrade Bot started and Log created")

        last_checked = None
        current_market = ""
        trade = False
        position_closed = False

        # Open API connection
        client =  API(access_token=config.OANDA_API_KEY.strip(), environment=config.OANDA_ENVIRON)
        
        while self.running: 

            current_time = datetime.now(timezone.utc)

            # Get Open Market
            open_market = []
            open_market = market.get_open_session(current_time)

            if open_market["market"] is not None:
                if open_market["market"] != current_market:
                    self.msg.emit(f"Trading {open_market["instrument"]} in {open_market["market"]}") 
                    logger.info(f"Trading {open_market["instrument"]} in {open_market["market"]}")
                    self.market_info.emit(open_market)
                    current_market = open_market["market"]
                    trade = True
            elif open_market["market"] is None and trade:
                self.msg.emit("Markets Closed")
                logger.warning("Markets Closed: No active market session at %s UTC", str(current_time))
                trade = False

            # Get Account Summery & update GUI
            summery = oanda.account_summery(client)
            if summery is None:
                oanda_logger.error("API call: Failed to get Account Summary (oanda.account_sumary())")
            self.account.emit(summery)
            open_pos = summery['openPositionCount']

            if trade:
                # Check for new 15 min candle
                if current_time.minute % 15 == 0 and current_time.second < 10:
                    # Check if the 15 min interval has changed since the last check
                    if last_checked != current_time.minute:
                
                        self.msg.emit("Checking for trade signals")

                        price = oanda.get_Candles(client, open_market["instrument"])

                        if price is not None:
                            price = ema.get_indicators(price, high_ind=50, low_ind=20)
                            self.msg.emit("New Candles recieved and indicators set")
                        else:
                            self.msg.emit("Failed to get Candles")
                            oanda_logger.error("API Call: Failed to get Candles")

                        if open_pos > 0: # There are open positions, so get the open positions data
                            self.msg.emit(f"You have {open_pos} open positions - checking position validity")
                            positions = oanda.open_positions(client)
                            position_closed = False
                            for position in positions:
                                #TODO: Push the generation of position data dict in to Oanda API handler
                                pos = ema.positions_data(position)
                                #TODO: Validate Oanda API call /trade is not None
                                pos["trade_time"] = oanda.getTradeTime(client, pos["tradeID"])
                                validity = ema.position_Validity_Check(pos, price, open_market["market"])

                                val_logger.info(f'Position: Instrument: {validity["instrument"]}, Reason: {validity["reason"]}, Validity: {validity["validity"]}')

                                if not validity["validity"]:
                                    posClose_res = None
                                    if oanda.server_position_exists(client, position["instrument"]):
                                        val_logger.debug(f'closePosition called for: {position["instrument"]}')
                                        posClose_res = oanda.close_position(client, position["instrument"])
                                    if posClose_res is None:
                                        self.msg.emit(f'Failed to Close Position - {validity["instrument"]}')
                                        oanda_logger.error(f'API Call: Failed to Close Position - {pos["instrument"]} - {validity["reason"]}')
                                    else:
                                        self.msg.emit(f'Position Closed - {pos["instrument"]}: {validity["reason"]}')
                                        logger.info(f'Position Closed - {pos["instrument"]}: {validity["reason"]}')
                                        position_closed = True
                                break

                        if not position_closed:  # No positions closed, check this candle for new entry signals

                            order = ema.strat_5020_Pullback(price, open_market["instrument"])
                
                            if order is None:
                                self.msg.emit("Strategy conditions not met")
                            else:
                                order_res = oanda.place_order(client, order)
                                if order_res is not None:
                                    self.msg.emit("Entry point detected & order placed:\n"
                                    f'Instrument: {order["order"]["instrument"]}\n'
                                    f'Units: {order["order"]["units"]}\n'
                                    f'Stop Loss: {order["order"]["stopLossOnFill"]}\n'
                                    f'Take Profit: {order["order"]["takeProfitOnFill"]}\n'
                                    f'Order No.: {order_res["orderCreateTransaction"]["id"]}')
                                    logger.info("Entry point detected & order placed:\n"
                                        f"Instrument: {order["order"]["instrument"]}\n"
                                        f"Units: {order["order"]["units"]}\n")
                                else:
                                    self.msg.emit("Entry point detected - Order failed to place!")
                                    oanda_logger.error("API Call: Entry point detected - Order failed to place!")
                            
                        last_checked = current_time.minute # Update to prevent re-triggering
                time.sleep(10)
        self.finished.emit()


