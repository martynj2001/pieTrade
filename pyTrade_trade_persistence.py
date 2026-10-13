"""Persistence of trade lifecycle events (open / close / sync) via pyTrade_trades_db."""
import logging
import sqlite3
from typing import Any, Dict, Iterable, Optional

import oanda_api_handler as oanda
import pyTrade_trades_db as trades_db


def persist_filled_trades(
    order_response: Dict[str, Any],
    order: Dict[str, Any],
    strategy_name: str,
    session: str,
    account_balance: float,
    risk_percent: float,
    logger: logging.Logger,
    signal_data: Optional[Dict[str, Any]] = None,
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
            if signal_data:
                try:
                    trades_db.insert_signal_data({"trade_id": str(trade_id), **signal_data})
                except (OSError, sqlite3.Error, TypeError, ValueError, KeyError):
                    logger.exception("Could not save signal data for trade %s", trade_id)
        except (OSError, sqlite3.Error, TypeError, ValueError, KeyError):
            logger.exception("Could not save opened trade %s", trade_id)


def calculate_pnl_pips(
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


def persist_closed_trades(
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
                pnl_pips = calculate_pnl_pips(stored_trade, exit_price)
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


def sync_closed_trades(
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
                pnl_pips=calculate_pnl_pips(local_trade, exit_price),
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
