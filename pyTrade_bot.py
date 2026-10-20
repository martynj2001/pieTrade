from PySide6.QtCore import QObject, Signal
from datetime import datetime, timezone
import sqlite3
import time
from oandapyV20 import API

import oanda_api_handler as oanda
from pyTrade_TrendFollowing_Strategy import TrendFollowingEngine
from pyTrade_Breakout_Strategy import BreakoutEngine
from pyTrade_validation import Validation
from pyTrade_orders import OrderManager
import pyTrade_market_session as market
import pyTrade_trades_db as trades_db
from pyTrade_trade_guards import TradeGuards
from pyTrade_position_data import build_position_cards
from pyTrade_trade_persistence import persist_filled_trades, persist_closed_trades, sync_closed_trades
from pyTrade_signal_data import build_signal_data

import logging
import config


class OandaInfoFilter(logging.Filter):
    def filter(self, record):
        # Suppress only specific noisy INFO messages
        blocked = [
            "summary"
        ]

        # Only filter INFO logs, keep WARNING/ERROR untouched
        if record.levelno == logging.INFO or record.levelno == logging.DEBUG:
            return not any(msg in record.getMessage() for msg in blocked)

        return True

class pyTradeWorker(QObject):

    msg = Signal(str)
    finished = Signal()
    market_info = Signal(dict)
    market_open = Signal(bool)
    account = Signal(dict)
    positions = Signal(list)
    candles = Signal(str, object)
    trade_levels = Signal(list)
   
    def __init__(
        self,
        strategy=None,
        validator=None,
        order_manager=None,
        trade_guards=None,
    ):
        super().__init__()
        self.running = True
        self.strategy_primary = strategy if strategy is not None else TrendFollowingEngine()
        self.strategy_secondary = (
            BreakoutEngine() if isinstance(self.strategy_primary, TrendFollowingEngine)
            else TrendFollowingEngine()
        )
        self.validator = validator if validator is not None else Validation()
        self.order_manager = order_manager if order_manager is not None else OrderManager()
        self.trade_guards = (
            trade_guards if trade_guards is not None else TradeGuards()
        )

    def _strategy_engine(self, name):
        """Return the strategy engine matching a stored strategy name, or None."""
        for engine in (self.strategy_primary, self.strategy_secondary):
            if engine.strategy_name == name:
                return engine
        return None

    def _publish_positions(self, client, positions):
        """Send the current open positions (with trade details) to the GUI."""
        open_trades = oanda.open_trades(client)
        if open_trades is None:
            logging.getLogger("pyTrade_bot").error("API Call: Failed to get open trades for position cards")
        self.positions.emit(build_position_cards(positions, open_trades))

    def _publish_trade_levels(self) -> None:
        """Send all open-trade price levels (entry/SL/TP) to the GUI chart."""
        logger = logging.getLogger("pyTrade")
        try:
            open_trades = trades_db.get_open_trades()
        except (OSError, sqlite3.Error):
            logger.exception("Could not read open trades for chart levels")
            return
        levels = []
        for trade in open_trades:
            levels.append({
                "id": str(trade["trade_id"]),
                "instrument": trade["instrument"],
                "direction": trade["direction"],
                "entry_price": float(trade["entry_price"]) if trade["entry_price"] is not None else None,
                "stop_loss": float(trade["stop_loss"]) if trade["stop_loss"] is not None else None,
                "take_profit": float(trade["take_profit"]) if trade["take_profit"] is not None else None,
            })
        self.trade_levels.emit(levels)

    def _sleep(self, seconds):
        # Sleep in short slices so stop_bot() takes effect promptly
        end = time.monotonic() + seconds
        while self.running and time.monotonic() < end:
            time.sleep(min(0.2, max(0, end - time.monotonic())))

    def stop_bot(self):
        self.running = False

    def on_set_strategy(self, strat):

        if strat == "EMA Pullback":
            primary_type, secondary_type = TrendFollowingEngine, BreakoutEngine
        else: # Breakout
            primary_type, secondary_type = BreakoutEngine, TrendFollowingEngine

        # Reuse existing engines; only construct when the strategy actually changes
        if not isinstance(self.strategy_primary, primary_type):
            self.strategy_primary = primary_type()
        if not isinstance(self.strategy_secondary, secondary_type):
            self.strategy_secondary = secondary_type()


    def _try_entry(self, strategy, price, client, open_market, summary, logger, oanda_logger):
       
        """Look for an entry signal on one strategy and place the order if the guards pass.
        Returns True if the strategy produced a trade signal (whether or not it was
        accepted by the guards), False if its conditions were not met.
        """
        signal, entry, stop, tp = strategy.get_signal(
            price,
            instrument=open_market["instrument"],
        )

        if signal not in ("BUY", "SELL") or entry is None or stop is None or tp is None:
            return False

        h1_price = oanda.get_Candles(
            client,
            open_market["instrument"],
            granularity="H1",
        )
        if h1_price is None:
            self.msg.emit(
                "Failed to get H1 candles; entry rejected"
            )
            oanda_logger.error(
                "Could not retrieve H1 candles for %s; "
                "rejecting signal",
                open_market["instrument"],
            )
        else:
            strategy_name = strategy.strategy_name
            if strategy_name == "Breakout":
                level_column = (
                    "DC_Upper"
                    if signal == "BUY"
                    else "DC_Lower"
                )
                if (
                    level_column not in price.columns
                    or price.empty
                    or price[level_column].iloc[-1]
                    is None
                ):
                    guard_passed = False
                    logger.error(
                        "Cannot validate breakout: missing "
                        "%s breakout level",
                        level_column,
                    )
                else:
                    guard_passed = (
                        self.trade_guards.validate_breakout(
                            price,
                            h1_price,
                            float(
                                price[level_column].iloc[-1]
                            ),
                            signal,
                        )
                    )
            elif strategy_name in {
                "EMA_TrendFollowing",
                "TrendFollowing",
            }:
                guard_passed = (
                    self.trade_guards.validate_trend_following(
                        price,
                        h1_price,
                        signal,
                    )
                )
            else:
                guard_passed = False
                logger.error(
                    "No trade guards configured for "
                    "strategy %s",
                    strategy_name,
                )

            if not guard_passed:
                self.msg.emit(
                    "Trade signal rejected by qualification guards"
                )
                logger.info(
                    "Trade signal rejected by qualification guards"
                )
            else:
                quote_to_gbp = oanda.get_quote_to_gbp(
                    client,
                    open_market["instrument"],
                )
                if quote_to_gbp is None:
                    self.msg.emit(
                        "Failed to get GBP conversion rate; entry rejected"
                    )
                    oanda_logger.error(
                        "Could not retrieve GBP conversion rate for %s; "
                        "rejecting signal",
                        open_market["instrument"],
                    )
                    return True

                order = self.order_manager.create_order_params(
                    instrument=open_market["instrument"],
                    signal=signal,
                    entry_price=entry,
                    stop_loss=stop,
                    take_profit=tp,
                    account_balance=summary["balance"],
                    quote_to_gbp=quote_to_gbp,
                    margin_available=summary["marginAvailable"],
                )
                if order is None:
                    self.msg.emit("Trade skipped: stop too tight for available margin")
                    logger.warning(
                        "Trade skipped: stop too tight for available margin on %s",
                        open_market["instrument"],
                    )
                    return True
                order_res = oanda.place_order(client, order)

                if order_res is not None and "orderFillTransaction" not in order_res:
                    reason = order_res.get("orderCancelTransaction", {}).get("reason", "UNKNOWN")
                    self.msg.emit(f"Order NOT filled - cancelled by OANDA: {reason}")
                    oanda_logger.error("Order NOT filled - cancelled by OANDA: %s", reason)
                    return True

                if order_res is not None:
                    try:
                        signal_data = build_signal_data(strategy, signal, price, self.trade_guards, logger)
                    except Exception:
                        logger.exception("Could not build signal data")
                        signal_data = None
                    persist_filled_trades(
                        order_response=order_res,
                        order=order,
                        strategy_name=strategy_name,
                        session=open_market["market"],
                        account_balance=float(
                            summary["balance"]
                        ),
                        risk_percent=float(
                            getattr(
                                self.order_manager,
                                "risk_percent",
                                config.RISK_PERCENT,
                            )
                        ),
                        logger=logger,
                        signal_data=signal_data,
                    )
                    self._publish_trade_levels()
                    message = (
                        "Entry point detected & order placed: "
                        f'Instrument: {order["order"]["instrument"]} '
                        f'Units: {order["order"]["units"]} '
                        f'Stop Loss: {order["order"]["stopLossOnFill"]} '
                        f'Take Profit: {order["order"]["takeProfitOnFill"]} '
                        f'Order No.: {order_res["orderCreateTransaction"]["id"]}'
                    )
                    self.msg.emit(message)
                    logger.info(message)
                else:
                    message = "Entry point detected - Order failed to place!"
                    self.msg.emit(message)
                    oanda_logger.error(message)
        return True


    def run_bot(self):

        # Logging is configured by pyTrade_logging.setup_logging() at app startup ----------

        logger = logging.getLogger("pyTrade")
        val_logger = logging.getLogger("Validation")
        oanda_logger = logging.getLogger("oandapyV20.oandapyV20")

        # Apply logging filter
        logger.addFilter(OandaInfoFilter())
        val_logger.addFilter(OandaInfoFilter())
        oanda_logger.addFilter(OandaInfoFilter())
        # ----------------------------------------------------------------------------------

        # Change the version after every major modification, change or update 
        self.msg.emit("pyTrade version 1.1 last modified 19 Oct 2026")
        logger.info("pyTrade version 1.1 last modified 19 Oct 2026")

        self.msg.emit("pyTrade Bot started and Log created.")
        logger.info("pyTrade Bot started and Log created")

        
        try:
            database_path = trades_db.create_database()
            logger.info("Trade database ready at %s", database_path)
            self.msg.emit(f"Trade database ready at {database_path}")
        except (OSError, sqlite3.Error):
                logger.exception("Could not initialize the local trade database")

        self._publish_trade_levels()

        self.msg.emit(f"Primary Strategy: {self.strategy_primary.strategy_name}")
        logger.info("Primary Strategy: %s", self.strategy_primary.strategy_name)
        self.msg.emit(f"Secondary Strategy: {self.strategy_secondary.strategy_name}")
        logger.info("Secondary Strategy: %s", self.strategy_secondary.strategy_name)

        last_checked = None
        current_market = ""
        trade = False

        # Open API connection
        client =  API(access_token=config.OANDA_API_KEY.strip(), environment=config.OANDA_ENVIRON)
     
                 
        while self.running: 

            current_time = datetime.now(timezone.utc)
            position_closed = False
        
            # Get Open Market
            open_market = market.get_open_session(current_time)
            if open_market["market"] is not None:
                if open_market["market"] != current_market:
                    self.msg.emit(f"Trading {open_market['instrument']} in {open_market['market']}") 
                    logger.info(f"Trading {open_market['instrument']} in {open_market['market']}")
                    self.market_info.emit(open_market)
                    current_market = open_market["market"]
                    self.market_open.emit(True)
                    trade = True
            elif open_market["market"] is None and trade:
                self.msg.emit("Markets Closed")
                logger.warning("Markets Closed: No active market session at %s UTC", str(current_time))
                self.market_info.emit({"market": None, "instrument": None})
                self.market_open.emit(False)
                trade = False
            elif open_market["market"] is None and not trade:
                #TODO: Add some sort of timer so you know bot is still alive.
                self.market_info.emit({"market": None, "instrument": None})
                self.market_open.emit(False)
                self.msg.emit("Markets Closed")
                trade = False
                wait = (market.next_open(current_time) - current_time).total_seconds()
                self._sleep(min(1000, max(1, wait)))
                #TODO: Add mechanisum to check time until the next market open session (if it is less than 1000 seconds then dont sleep for the full 1000 seconds)
            if trade:
                # Get Account Summary & update GUI
                summary = oanda.account_summery(client)
                if summary is None:
                    self.msg.emit("Failed to get account summary")
                    oanda_logger.error("API call: Failed to get Account Summary (oanda.account_sumary())")
                    self._sleep(10)
                    continue
                self.account.emit(summary)
                # Check for new 15 min candle
                if current_time.minute % 15 == 0 and current_time.second < 10:
                    # Check if the 15 min interval has changed since the last check
                    if last_checked != current_time.minute:
                
                        self.msg.emit("Checking for trade signals")

                        price = oanda.get_Candles(client, open_market["instrument"]) 

                        if price is not None:
                            raw_price = price.copy()
                            price = self.strategy_primary.add_indicators(price)
                            self.candles.emit(open_market["instrument"], price.copy()) 
                            self.msg.emit("New Candles recieved and indicators set")
                        else:
                            self.msg.emit("Failed to get Candles")
                            oanda_logger.error("API Call: Failed to get Candles")
                            last_checked = current_time.minute
                            self._sleep(10)
                            continue
                        
                        positions = oanda.open_positions(client)
                        if positions is None:
                            self.msg.emit("Failed to fetch open positions")
                            oanda_logger.error("API Call: Failed to get open positions")
                            last_checked = current_time.minute
                            self._sleep(10)
                            continue

                        sync_closed_trades(client, positions, logger)
                        if positions:
                            self.msg.emit(
                                f"You have {len(positions)} open positions "
                                "- checking position validity"
                            )
                            oanda_logger.debug(f"Open positions: {positions}")
                            position_closed = False
                            indicator_cache = {self.strategy_primary.strategy_name: price}
                            for position in positions:
                                pos = self.validator.extract_position_data(position)

                                # Validate with the strategy the trade was opened under (stored in the DB)
                                pos_strategy = self.strategy_primary
                                try:
                                    stored = trades_db.get_trade_by_id(str(pos["tradeID"])) if pos["tradeID"] else None
                                except (OSError, sqlite3.Error):
                                    logger.exception("Could not read strategy for trade %s", pos["tradeID"])
                                    stored = None
                                if stored and stored.get("strategy"):
                                    engine = self._strategy_engine(stored["strategy"])
                                    if engine is not None:
                                        pos_strategy = engine
                                    else:
                                        logger.warning(
                                            "Trade %s has unknown strategy %s; using primary strategy rules",
                                            pos["tradeID"], stored["strategy"],
                                        )
                                else:
                                    logger.warning(
                                        "No stored strategy for trade %s; using primary strategy rules",
                                        pos["tradeID"],
                                    )
                                pos["strategy"] = pos_strategy.strategy_name

                                if pos_strategy.strategy_name not in indicator_cache:
                                    indicator_cache[pos_strategy.strategy_name] = pos_strategy.add_indicators(raw_price.copy())
                                pos_price = indicator_cache[pos_strategy.strategy_name]

                                pos["trade_time"] = oanda.getTradeTime(client, pos["tradeID"])
                                if pos["trade_time"] is None:
                                    self.msg.emit(
                                        f"Skipping validation: missing trade time for {pos['instrument']}"
                                    )
                                    oanda_logger.error(
                                        "API Call: Failed to get trade time for tradeID %s",
                                        pos["tradeID"],
                                    )
                                    continue
                                validity = self.validator.validate_position(pos, pos_price, open_market["market"], pos_strategy.strategy_name)
                                val_logger.info(f'Position: Instrument: {validity["instrument"]}, Strategy: {pos_strategy.strategy_name}, Reason: {validity["reason"]}, Validity: {validity["validity"]}')

                                if not validity["validity"]: #Position is no longer valid
                                    posClose_res = None
                                    if oanda.server_position_exists(client, position["instrument"]):
                                        val_logger.debug(f'closePosition called for: {position["instrument"]}')
                                        
                                        posClose_res = oanda.close_position(client, position["instrument"])
                                        
                                        if posClose_res is None:
                                            self.msg.emit(f'DEBUG::Failed to Close Position - {validity["instrument"]}')
                                            oanda_logger.debug(f'API Call DEBUG: Didnt send, debugging - {pos["instrument"]} - {validity["reason"]}')
                                            #self.msg.emit(f'Failed to Close Position - {validity["instrument"]}')
                                            #oanda_logger.error(f'API Call: Failed to Close Position - {pos["instrument"]} - {validity["reason"]}')
                                        else:
                                            persist_closed_trades(
                                                posClose_res,
                                                validity["reason"],
                                                logger,
                                            )
                                            self._publish_trade_levels()
                                            self.msg.emit(f'Position Closed - {pos["instrument"]}: {validity["reason"]}')
                                            logger.info(f'Position Closed - {pos["instrument"]}: {validity["reason"]}')
                                            position_closed = True
                                break

                        if position_closed:
                            positions = oanda.open_positions(client)
                        if positions is not None:
                            self._publish_positions(client, positions)

                        if not position_closed:  # No positions closed, check this candle for new entry signals

                            for index, strategy in enumerate((self.strategy_primary, self.strategy_secondary)):
                                if index == 0:
                                    strat_price = price
                                else:
                                    # Secondary strategy needs its own indicator set on the raw candles
                                    strat_price = strategy.add_indicators(raw_price.copy())
                                    if strat_price is None or strat_price.empty:
                                        self.msg.emit(f"{strategy.strategy_name}: could not calculate indicators")
                                        break
                                if self._try_entry(strategy, strat_price, client, open_market, summary, logger, oanda_logger):
                                    break
                                if index == 0:
                                    msg = (
                                        f"No trade signal from primary strategy ({strategy.strategy_name}) "
                                        f"- moving to secondary strategy ({self.strategy_secondary.strategy_name})"
                                    )
                                    self.msg.emit(msg)
                                    logger.info(msg)
                                else:
                                    self.msg.emit("Strategy conditions not met (primary and secondary)")
                            
                        self._publish_trade_levels()

                        last_checked = current_time.minute # Update to prevent re-triggering
            self._sleep(10)
        self.finished.emit()
