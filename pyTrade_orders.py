"""
pyTrade Order Management Module

Provides common order creation, position sizing, and data parameter formatting
for OANDA v20 orders used across all strategy engines (Trend Following, Breakout, etc.).
"""

import logging
from typing import Any, Dict, Optional, Union
import config


class OrderManager:
    """
    Handles position sizing calculations and order payload generation for OANDA API.
    """

    def __init__(
        self,
        money_risk: float = config.MONEY_RISK,
        min_sl_dist: float = 0.05,
        price_precision: int = 3,
        default_order_type: str = "MARKET",
    ) -> None:
        """
        Initialize the OrderManager.

        :param money_risk: Capital at risk per trade in account currency
        :param min_sl_dist: Minimum stop loss distance in price units to prevent oversized units
        :param price_precision: Decimal precision for price fields (default: 3)
        :param default_order_type: OANDA order type (default: 'MARKET')
        """
        self.money_risk = money_risk
        self.min_sl_dist = min_sl_dist
        self.price_precision = price_precision
        self.default_order_type = default_order_type
        self.logger = logging.getLogger("pyTrade.OrderManager")

    def calculate_units(
        self,
        signal: Union[str, bool],
        entry_price: float,
        stop_loss: float,
        money_risk: Optional[float] = None,
    ) -> int:
        """
        Calculate the number of units to trade using risk-based position sizing.

        Units = money_risk / stop_loss_distance

        :param signal: 'BUY', 'SELL', 'LONG', 'SHORT', or boolean (True=BUY, False=SELL)
        :param entry_price: Planned entry price
        :param stop_loss: Stop loss price level
        :param money_risk: Optional override for money risk
        :return: Number of units as a positive integer (direction applied during order formatting)
        """
        risk_amount = money_risk if money_risk is not None else self.money_risk
        sl_distance = abs(entry_price - stop_loss)

        if sl_distance < self.min_sl_dist:
            self.logger.warning(
                "Stop loss distance (%.5f) below minimum (%.5f); clamping to minimum",
                sl_distance,
                self.min_sl_dist,
            )
            sl_distance = self.min_sl_dist

        units = int(risk_amount / sl_distance)
        units = max(1, units)

        self.logger.debug(
            "calculate_units: Signal=%s, Entry=%.5f, SL=%.5f, SL_Dist=%.5f, Risk=%.2f -> Units=%d",
            str(signal),
            entry_price,
            stop_loss,
            sl_distance,
            risk_amount,
            units,
        )
        return units

    def build_order_data(
        self,
        instrument: str,
        units: int,
        stop_loss: float,
        take_profit: float,
        signal: Optional[Union[str, bool]] = None,
        order_type: Optional[str] = None,
        price_precision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Build the data dictionary payload required by OANDA v20 OrderCreate endpoint.

        :param instrument: Currency pair / instrument (e.g., 'USD_JPY')
        :param units: Position size (unsigned or signed)
        :param stop_loss: Stop loss price
        :param take_profit: Take profit price
        :param signal: 'BUY', 'SELL', 'LONG', 'SHORT', or bool (True=BUY, False=SELL)
        :param order_type: Order type (default: 'MARKET')
        :param price_precision: Decimal places for prices
        :return: OANDA order payload dictionary
        """
        prec = price_precision if price_precision is not None else self.price_precision
        ord_type = order_type if order_type is not None else self.default_order_type

        # Determine signed units
        signed_units = abs(units)
        if signal is not None:
            if isinstance(signal, str) and signal.upper() in ("SELL", "SHORT"):
                signed_units = -abs(units)
            elif isinstance(signal, bool) and not signal:
                signed_units = -abs(units)
        elif units < 0:
            signed_units = units

        data = {
            "order": {
                "instrument": instrument,
                "units": signed_units,
                "type": ord_type,
                "stopLossOnFill": {"price": f"{stop_loss:.{prec}f}"},
                "takeProfitOnFill": {"price": f"{take_profit:.{prec}f}"},
            }
        }

        self.logger.debug("build_order_data generated: %s", data)

        return data

    def create_order_params(
        self,
        instrument: str,
        signal: Union[str, bool],
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        money_risk: Optional[float] = None,
        order_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Helper method to calculate units and generate the complete OANDA order payload.

        :param instrument: Currency pair / instrument (e.g. 'USD_JPY')
        :param signal: 'BUY' or 'SELL'
        :param entry_price: Entry price
        :param stop_loss: Stop loss price
        :param take_profit: Take profit price
        :param money_risk: Risk capital override
        :param order_type: Order type override
        :return: OANDA order payload dictionary
        """
        units = self.calculate_units(
            signal=signal,
            entry_price=entry_price,
            stop_loss=stop_loss,
            money_risk=money_risk,
        )

        return self.build_order_data(
            instrument=instrument,
            units=units,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal=signal,
            order_type=order_type,
        )


# Module-level convenience functions matching procedural strategy calls

_default_order_manager = OrderManager()


def order_units(
    trade_type: Union[str, bool],
    entry_price: float,
    stop_loss: float,
    money_risk: float = config.MONEY_RISK,
) -> int:
    """
    Calculate order units based on risk capital and stop loss distance.

    :param trade_type: True/False or 'BUY'/'SELL'
    :param entry_price: Entry price level
    :param stop_loss: Stop loss price level
    :param money_risk: Total money risk in account currency
    :return: Position units
    """
    return _default_order_manager.calculate_units(
        signal=trade_type,
        entry_price=entry_price,
        stop_loss=stop_loss,
        money_risk=money_risk,
    )


def order_data(
    stop_loss: float,
    take_profit: float,
    instrument: str,
    units: int,
    trade_type: Optional[Union[str, bool]] = None,
    price_precision: int = 3,
) -> Dict[str, Any]:
    """
    Build OANDA v20 order parameters payload.

    :param stop_loss: Stop loss price
    :param take_profit: Take profit price
    :param instrument: Instrument symbol (e.g. 'USD_JPY')
    :param units: Position units
    :param trade_type: True/False or 'BUY'/'SELL'
    :param price_precision: Decimal formatting precision
    :return: Order payload dictionary
    """
    return _default_order_manager.build_order_data(
        instrument=instrument,
        units=units,
        stop_loss=stop_loss,
        take_profit=take_profit,
        signal=trade_type,
        price_precision=price_precision,
    )


def create_order_from_signal(
    instrument: str,
    signal: str,
    entry: float,
    stop: float,
    tp: float,
    money_risk: float = config.MONEY_RISK,
    price_precision: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for worker threads to build order payload directly
    from strategy engine output tuple (signal, entry, stop, tp).

    :param instrument: Instrument symbol (e.g. 'USD_JPY')
    :param signal: 'BUY' or 'SELL'
    :param entry: Entry price
    :param stop: Stop loss price
    :param tp: Take profit price
    :param money_risk: Risk capital
    :param price_precision: Price decimal precision
    :return: OANDA order payload dictionary, or None if signal is 'NONE'
    """
    if signal.upper() not in ("BUY", "SELL"):
        return None

    return _default_order_manager.create_order_params(
        instrument=instrument,
        signal=signal,
        entry_price=entry,
        stop_loss=stop,
        take_profit=tp,
        money_risk=money_risk,
    )
