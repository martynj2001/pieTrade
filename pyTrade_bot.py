
from PySide6.QtCore import QObject, Signal

from datetime import datetime, timezone
import time
from oandapyV20 import API
import oanda_api_handler as oanda
import EMA_Trend_following as ema
import pyTrade_market_session as market
import logging
import config

class pyTradeWorker(QObject):

    msg = Signal(str)
    finished = Signal()
    market_info = Signal(dict)
    account = Signal(dict)
    # TODO: Add log screen to GUI - view Log.
    # log = Signal(str)

    def __init__(self):
        super().__init__()
        self.running = True

    def stop_bot(self):
        self.running = False

    def run_bot(self):

        #Configure logging
        logging.basicConfig(
            filename=f"{datetime.now(timezone.utc).strftime('%d%m%y-%H%M')}-pyTrade.log",
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
        )

        logger = logging.getLogger("pyTrade")

        self.msg.emit("pyTrade Bot started and Log created.")
        logger.info("pyTrade Bot started and Log created")

        last_checked = None
        current_market = ""
        trade = False

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
                logger.warning("No active market session at %s UTC", str(current_time))
                trade = False

            # Get Account Summery & update GUI
            summery = oanda.account_summery(client)
            self.account.emit(summery)

            if trade:
                # Check for new 15 min candle
                if current_time.minute % 15 == 0 and current_time.second < 10:
                    # Check if the 15 min interval has changed since the last check
                    if last_checked != current_time.minute:
                
                        self.msg.emit("Checking for trade signals")

                        price = oanda.get_Candles(client, open_market["instrument"]) # pyright: ignore[reportOptionalSubscript]
                        if price is not None:
                            price = ema.get_indicators(price, high_ind=50, low_ind=20)
                            self.msg.emit("New Candles recieved and indicators set")
                        else:
                            self.msg.emit("Failed to get Candles")
                            logger.error("Failed to get Candles")
                        
                        order = ema.strat_5020_Pullback(price, open_market["instrument"])

                        if order is None:
                            self.msg.emit("Strategy conditions not met")
                        else:
                            self.msg.emit("Entry point detected & order placed:\n"
                            f'Instrument: {order["order"]["instrument"]}\n'
                            f'Units: {order["order"]["units"]}\n'
                            f'Stop Loss: {order["order"]["stopLossOnFill"]}\n'
                            f'Take Profit: {order["order"]["takeProfitOnFill"]}\n')
                            logging.info("Entry point detected & order placed:\n"
                                f'Instrument: {order["order"]["instrument"]}')
                            # TODO: Error handling to confirm order placed and
                            # TODO: Check there are no open orders........
                            oanda.place_order(client, order)
                        last_checked = current_time.minute # Update to prevent re-triggering
                time.sleep(10)
        self.finished.emit()
