from PySide6.QtCore import QObject, Signal
from datetime import datetime, timezone
import sqlite3
import time
from typing import Any, Dict, Iterable
from oandapyV20 import API

import oanda_api_handler as oanda
from pyTrade_TrendFollowing_Strategy import TrendFollowingEngine
from pyTrade_Breakout_Strategy import BreakoutEngine
from pyTrade_validation import Validation
from pyTrade_orders import OrderManager
import pyTrade_market_session as market
import pyTrade_trades_db as trades_db
from trade_guards import TradeGuards

import logging
import config


def _persist_filled_trades(
    order_response: Dict[str, Any],
    order: Dict[str, Any],
    strategy_name: str,
    session: str,
    account_balance: float,
    risk_percent: float,
    logger: logging.Logger,
) -> None:
    """Store trades OANDA confirms were opened by a filled order."""
    fill = order_response.get("orderFillTransaction")
    if not isinstance(fill, dict):
        logger.warning(
            "Order response had no fill transaction; no trade was saved"
        )
        return

    opened_trades = []
    if isinstance(fill.get("tradeOpened"), dict):
        opened_trades.append(fill["tradeOpened"])
    opened_trades.extend(
        trade
        for trade in fill.get("tradesOpened", [])
        if isinstance(trade, dict)
    )
    if not opened_trades:
        logger.warning(
            "Order fill for %s did not open a new trade; no trade was saved",
            fill.get("instrument", order.get("order", {}).get("instrument")),
        )
        return

    requested_units = abs(int(order["order"]["units"]))
    for opened_trade in opened_trades:
        trade_id = opened_trade.get("tradeID")
        if trade_id is None:
            logger.error("OANDA opened trade response is missing tradeID: %s", opened_trade)
            continue
        units = int(float(opened_trade["units"]))
        allocated_risk = (
            account_balance
            * risk_percent
            * abs(units)
            / requested_units
            if requested_units
            else 0.0
        )
        trade_data = {
            "trade_id": str(trade_id),
            "instrument": fill.get(
                "instrument", order["order"]["instrument"]
            ),
            "direction": "BUY" if units > 0 else "SELL",
            "strategy": strategy_name,
            "entry_time": fill.get("time"),
            "entry_price": float(fill["price"]),
            "stop_loss": float(
                order["order"]["stopLossOnFill"]["price"]
            ),
            "take_profit": float(
                order["order"]["takeProfitOnFill"]["price"]
            ),
            "units": abs(units),
            "risk_amount": allocated_risk,
            "status": "OPEN",
            "session": session,
        }
        try:
            trades_db.insert_trade(trade_data)
            logger.info("Saved opened OANDA trade %s to local database", trade_id)
        except (OSError, sqlite3.Error, TypeError, ValueError, KeyError):
            logger.exception("Could not save opened trade %s", trade_id)


def _calculate_pnl_pips(
    trade: Dict[str, Any],
    exit_price: float,
) -> float:
    """Calculate signed pips from a stored trade and its exit price."""
    entry_price = float(trade["entry_price"])
    pip_size = 0.01 if trade["instrument"].endswith("_JPY") else 0.0001
    price_change = (
        exit_price - entry_price
        if trade["direction"].upper() == "BUY"
        else entry_price - exit_price
    )
    return round(price_change / pip_size, 2)


def _persist_closed_trades(
    close_response: Dict[str, Any],
    close_reason: str,
    logger: logging.Logger,
) -> None:
    """Persist realized outcomes for trades closed by an OANDA position fill."""
    fill_transactions = [
        close_response.get("longOrderFillTransaction"),
        close_response.get("shortOrderFillTransaction"),
    ]
    closed_trade_count = 0
    for fill in fill_transactions:
        if not isinstance(fill, dict):
            continue

        closed_trades = fill.get("tradesClosed", [])
        if isinstance(closed_trades, dict):
            closed_trades = [closed_trades]
        elif not isinstance(closed_trades, (list, tuple)):
            closed_trades = []
        if isinstance(fill.get("tradeClosed"), dict):
            closed_trades = [*closed_trades, fill["tradeClosed"]]
        for closed_trade in closed_trades:
            trade_id = closed_trade.get("tradeID")
            if trade_id is None:
                logger.error(
                    "OANDA close transaction is missing tradeID: %s",
                    closed_trade,
                )
                continue

            trade_id = str(trade_id)
            try:
                stored_trade = trades_db.get_trade_by_id(trade_id)
                if stored_trade is None:
                    logger.warning(
                        "Closed OANDA trade %s is not in the local database",
                        trade_id,
                    )
                    continue

                exit_price = float(fill["price"])
                pnl_pips = _calculate_pnl_pips(stored_trade, exit_price)
                realized_pl = float(closed_trade["realizedPL"])
                updated = trades_db.update_trade_close(
                    trade_id=trade_id,
                    exit_time=fill["time"],
                    exit_price=exit_price,
                    pnl_currency=realized_pl,
                    pnl_pips=pnl_pips,
                    close_reason=close_reason,
                )
                if updated:
                    closed_trade_count += 1
                    trades_db.insert_trade_event(
                        trade_id,
                        "CLOSED",
                        close_reason,
                        event_time=fill["time"],
                    )
                    logger.info(
                        "Saved realized close outcome for trade %s: P&L=%s",
                        trade_id,
                        realized_pl,
                    )
            except (OSError, sqlite3.Error, TypeError, ValueError, KeyError):
                logger.exception("Could not save close outcome for trade %s", trade_id)

    if not closed_trade_count:
        logger.warning(
            "Position close returned no recognized closed trades to save"
        )


def _sync_closed_trades(
    client,
    open_positions: Iterable[Dict[str, Any]],
    logger: logging.Logger,
) -> None:
    """Reconcile DB-open trades against OANDA to capture SL/TP/manual closes."""
    active_trade_ids = set()
    for position in open_positions:
        for side in ("long", "short"):
            active_trade_ids.update(
                str(trade_id)
                for trade_id in position.get(side, {}).get("tradeIDs", [])
            )

    try:
        local_open_trades = trades_db.get_open_trades()
    except (OSError, sqlite3.Error):
        logger.exception("Could not read open trades for close reconciliation")
        return

    for local_trade in local_open_trades:
        trade_id = str(local_trade["trade_id"])
        if trade_id in active_trade_ids:
            continue

        trade_details = oanda.getTradeDetails(client, trade_id)
        if not trade_details or trade_details.get("state") != "CLOSED":
            continue

        try:
            exit_price = float(trade_details["averageClosePrice"])
            pnl_currency = float(trade_details["realizedPL"])
            exit_time = trade_details["closeTime"]
            updated = trades_db.update_trade_close(
                trade_id=trade_id,
                exit_time=exit_time,
                exit_price=exit_price,
                pnl_currency=pnl_currency,
                pnl_pips=_calculate_pnl_pips(local_trade, exit_price),
                close_reason="OANDA trade closed outside the bot",
            )
            if updated:
                trades_db.insert_trade_event(
                    trade_id,
                    "CLOSED",
                    "OANDA trade closed outside the bot",
                    event_time=exit_time,
                )
                logger.info(
                    "Reconciled closed OANDA trade %s: P&L=%s",
                    trade_id,
                    pnl_currency,
                )
        except (OSError, sqlite3.Error, TypeError, ValueError, KeyError):
            logger.exception(
                "Could not reconcile close details for trade %s",
                trade_id,
            )


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
    market_open = Signal(bool)
    account = Signal(dict)
   
    def __init__(
        self,
        strategy=None,
        validator=None,
        order_manager=None,
        trade_guards=None,
    ):
        super().__init__()
        self.running = True
        self.strategy = strategy if strategy is not None else TrendFollowingEngine()
        self.validator = validator if validator is not None else Validation()
        self.order_manager = order_manager if order_manager is not None else OrderManager()
        self.trade_guards = (
            trade_guards if trade_guards is not None else TradeGuards()
        )

    def stop_bot(self):
        self.running = False

    def on_set_strategy(self, strat):

        if strat == "EMA Pullback":
            self.strategy = TrendFollowingEngine()
        else: # Breakout
            self.strategy = BreakoutEngine()


    def run_bot(self):

        # Configure logging -----------------------------------------------------------------

        logging.basicConfig(
            filename=f"{datetime.now(timezone.utc).strftime('%d%m%y-%H%M')}-pyTrade.log",
            level=logging.DEBUG if config.DEBUG_LOGGING else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
        )

       
        logger = logging.getLogger("pyTrade")
        val_logger = logging.getLogger("Validation")
        oanda_logger = logging.getLogger("oandapyV20.oandapyV20")

        logging.getLogger("urllib3").setLevel(logging.INFO)

        # Apply logging filter
        # Attach filter to OANDA logger
        oanda_logger.addFilter(OandaInfoFilter())
        
        # ----------------------------------------------------------------------------------

        try:
                database_path = trades_db.create_database()
                logger.info("Trade database ready at %s", database_path)
        except (OSError, sqlite3.Error):
                logger.exception("Could not initialize the local trade database")

        self.msg.emit("pyTrade Bot started and Log created.")
        logger.info("pyTrade Bot started and Log created")

        self.msg.emit(f"Running Strategy: {self.strategy.strategy_name}")
        logger.info("Running Strategy: %s", self.strategy.strategy_name)

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
                time.sleep(1000) # Sleep for 1000 seconds before checking again
                #TODO: Add mechanisum to check time until the next market open session (if it is less than 1000 seconds then dont sleep for the full 1000 seconds)
            if trade:
                # Get Account Summary & update GUI
                summary = oanda.account_summery(client)
                if summary is None:
                    self.msg.emit("Failed to get account summary")
                    oanda_logger.error("API call: Failed to get Account Summary (oanda.account_sumary())")
                    time.sleep(10)
                    continue
                self.account.emit(summary)
                # Check for new 15 min candle
                if current_time.minute % 15 == 0 and current_time.second < 10:
                    # Check if the 15 min interval has changed since the last check
                    if last_checked != current_time.minute:
                
                        self.msg.emit("Checking for trade signals")

                        price = oanda.get_Candles(client, open_market["instrument"])

                        if price is not None:
                            price = self.strategy.add_indicators(price)
                            self.msg.emit("New Candles recieved and indicators set")
                        else:
                            self.msg.emit("Failed to get Candles")
                            oanda_logger.error("API Call: Failed to get Candles")
                            last_checked = current_time.minute
                            time.sleep(10)
                            continue
                        
                        positions = oanda.open_positions(client)
                        if positions is None:
                            self.msg.emit("Failed to fetch open positions")
                            oanda_logger.error("API Call: Failed to get open positions")
                            last_checked = current_time.minute
                            time.sleep(10)
                            continue

                        _sync_closed_trades(client, positions, logger)
                        if positions:
                            self.msg.emit(
                                f"You have {len(positions)} open positions "
                                "- checking position validity"
                            )
                            oanda_logger.debug(f"Open positions: {positions}")
                            position_closed = False
                            for position in positions:
                                position["strategy"] = self.strategy.strategy_name
                                pos = self.validator.extract_position_data(position)
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
                                validity = self.validator.validate_position(pos, price, open_market["market"], self.strategy.strategy_name)
                                val_logger.info(f'Position: Instrument: {validity["instrument"]}, Reason: {validity["reason"]}, Validity: {validity["validity"]}')

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
                                            _persist_closed_trades(
                                                posClose_res,
                                                validity["reason"],
                                                logger,
                                            )
                                            self.msg.emit(f'Position Closed - {pos["instrument"]}: {validity["reason"]}')
                                            logger.info(f'Position Closed - {pos["instrument"]}: {validity["reason"]}')
                                            position_closed = True
                                break

                        if not position_closed:  # No positions closed, check this candle for new entry signals

                            signal, entry, stop, tp = self.strategy.get_signal(price)
                
                            if signal not in ("BUY", "SELL") or entry is None or stop is None or tp is None:
                                self.msg.emit("Strategy conditions not met")
                            else:
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
                                    strategy_name = self.strategy.strategy_name
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
                                        order = self.order_manager.create_order_params(
                                            instrument=open_market["instrument"],
                                            signal=signal,
                                            entry_price=entry,
                                            stop_loss=stop,
                                            take_profit=tp,
                                            account_balance=summary["balance"],
                                        )
                                        order_res = oanda.place_order(client, order)

                                        if order_res is not None:
                                            _persist_filled_trades(
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
                                            )
                                            self.msg.emit(
                                                "Entry point detected & order placed: "
                                                f'Instrument: {order["order"]["instrument"]} '
                                                f'Units: {order["order"]["units"]} '
                                                f'Stop Loss: {order["order"]["stopLossOnFill"]} '
                                                f'Take Profit: {order["order"]["takeProfitOnFill"]} '
                                                f'Order No.: {order_res["orderCreateTransaction"]["id"]}'
                                            )
                                            logger.info(
                                                "Entry point detected & order placed:\n"
                                                "Instrument: %s\nUnits: %s",
                                                order["order"]["instrument"],
                                                order["order"]["units"],
                                            )
                                        else:
                                            self.msg.emit(
                                                "Entry point detected - Order failed to place!"
                                            )
                                            oanda_logger.error(
                                                "API Call: Entry point detected - "
                                                "Order failed to place!"
                                            )
                            
                        last_checked = current_time.minute # Update to prevent re-triggering
            time.sleep(10)
        self.finished.emit()
