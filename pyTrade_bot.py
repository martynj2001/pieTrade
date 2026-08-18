
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

    def __init__(self):
        super().__init__()
        self.running = True

    def stop_bot(self):
        self.running = False

    def run_bot(self):

        self.msg.emit("Starting pyTrade Bot ......")

        #Configure logging
        logging.basicConfig(
            filename=f"{datetime.now(timezone.utc).strftime("%d%m%y-%H%M")}-pyTrade.log",
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s : %(message)s',
        )
        self.msg.emit("Log created.")

        last_checked = None

        client =  API(access_token=config.OANDA_API_KEY, environment=config.OANDA_ENVIRON)
        
        while self.running: 
            current_time = datetime.now(timezone.utc)
            # Get Open Market
            open_market = market.getSession()
            self.msg.emit(f"Trading {open_market["instrument"]} in {open_market["market"]} ")    

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
                    
                    order = ema.strat_5020_Pullback(price)
                    if order is None:
                        self.msg.emit("Strategy conditions not met")
                    else:
                        self.msg.emit("Entry point detected & order placed:\n"
                        f'Instrument: {order["order"]["instrument"]}\n'
                        f'Units: {order["order"]["units"]}\n'
                        f'Stop Loss: {order["order"]["stopLossOnFill"]}\n'
                        f'Take Profit: {order["order"]["takeProfitOnFill"]}\n')
                        # Requires some error handling to confirm order placed and
                        # check there are no open orders........
                        oanda.place_order(order)
                        # Wait for order to close before continueing.
                    last_checked = current_time.minute # Update to prevent re-triggering
            time.sleep(10)
        self.finished.emit()