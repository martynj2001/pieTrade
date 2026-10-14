"""
pyTrade Order Management Module

Provides common order creation, position sizing, and data parameter formatting
for OANDA v20 orders used across all strategy engines (Trend Following, Breakout, etc.).
"""

import logging
from typing import Any, Dict, Optional, Union
import config
import pyTrade_instruments


class OrderManager:
    """
    Handles position sizing calculations and order payload generation for OANDA API.
    """

    def __init__(
        self,
        money_risk: float = config.MONEY_RISK,
        risk_percent: float = config.RISK_PERCENT,
        min_sl_dist: float = 0.05,
        price_precision: int = 3,
        default_order_type: str = "MARKET",
    ) -> None:
        """
        Initialize the OrderManager.

        :param money_risk: Fallback capital at risk per trade in account currency,
            used only when no account balance is available to compute a
            percentage-based risk amount.
        :param risk_percent: Fraction of account balance to risk per trade
            (e.g. 0.02 = 2%). Used whenever an account balance is supplied.
        :param min_sl_dist: Minimum stop loss distance in price units to prevent oversized units
        :param price_precision: Decimal precision for price fields (default: 3)
        :param default_order_type: OANDA order type (default: 'MARKET')
        """
        self.money_risk = money_risk
        self.risk_percent = risk_percent
        self.min_sl_dist = min_sl_dist
        self.price_precision = price_precision
        self.default_order_type = default_order_type
        self.logger = logging.getLogger("pyTrade.OrderManager")

    def calculate_units(
        self,
        signal: Union[str, bool],
        entry_price: float,
        stop_loss: float,
        account_balance: Optional[float] = None,
        risk_percent: Optional[float] = None,
        money_risk: Optional[float] = None,
        instrument: Optional[str] = None,
    ) -> int:
        """
        Calculate the number of units to trade using risk-based position sizing.

        When an account balance is supplied, risk is calculated as a percentage
        of that balance (risk_amount = account_balance * risk_percent), so
        position size scales up/down with the account instead of using a fixed
        money amount. If no balance is supplied, falls back to the fixed
        money_risk amount for backward compatibility.

        Units = risk_amount / stop_loss_distance

        :param signal: 'BUY', 'SELL', 'LONG', 'SHORT', or boolean (True=BUY, False=SELL)
        :param entry_price: Planned entry price
        :param stop_loss: Stop loss price level
        :param account_balance: Current account balance in account currency. When
            provided, risk is computed as a percentage of this balance.
        :param risk_percent: Optional override for the risk percentage (fraction,
            e.g. 0.02 for 2%). Only used when account_balance is supplied.
        :param money_risk: Optional override for the fixed money risk amount,
            used only when account_balance is not supplied.
        :param instrument: Optional instrument symbol for pair-specific minimum stop distance.
        :return: Number of units as a positive integer (direction applied during order formatting)
        """
        if account_balance is not None:
            pct = risk_percent if risk_percent is not None else self.risk_percent
            risk_amount = account_balance * pct
        else:
            risk_amount = money_risk if money_risk is not None else self.money_risk

        sl_distance = abs(entry_price - stop_loss)

        minimum_sl_dist = (
            pyTrade_instruments.min_sl_dist(instrument)
            if instrument is not None
            else self.min_sl_dist
        )

        if sl_distance < minimum_sl_dist:
            self.logger.warning(
                "Stop loss distance (%.5f) below minimum (%.5f); clamping to minimum",
                sl_distance,
                minimum_sl_dist,
            )
            sl_distance = minimum_sl_dist

        units = int(risk_amount / sl_distance)
        units = max(1, units)

        self.logger.debug(
            "calculate_units: Signal=%s, Entry=%.5f, SL=%.5f, SL_Dist=%.5f, "
            "Balance=%s, Risk=%.2f -> Units=%d",
            str(signal),
            entry_price,
            stop_loss,
            sl_distance,
            f"{account_balance:.2f}" if account_balance is not None else "N/A",
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
        account_balance: Optional[float] = None,
        risk_percent: Optional[float] = None,
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
        :param account_balance: Current account balance; when supplied, position
            size is risk_percent of this balance instead of a fixed money amount
        :param risk_percent: Risk percentage override (fraction, e.g. 0.02 for 2%)
        :param money_risk: Fixed risk capital override, used only when
            account_balance is not supplied
        :param order_type: Order type override
        :return: OANDA order payload dictionary
        """
        units = self.calculate_units(
            signal=signal,
            entry_price=entry_price,
            stop_loss=stop_loss,
            account_balance=account_balance,
            risk_percent=risk_percent,
            money_risk=money_risk,
            instrument=instrument,
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
    account_balance: Optional[float] = None,
    risk_percent: Optional[float] = None,
    money_risk: Optional[float] = None,
) -> int:
    """
    Calculate order units based on risk capital and stop loss distance.

    :param trade_type: True/False or 'BUY'/'SELL'
    :param entry_price: Entry price level
    :param stop_loss: Stop loss price level
    :param account_balance: Current account balance; when supplied, position
        size is risk_percent of this balance instead of a fixed money amount
    :param risk_percent: Risk percentage override (fraction, e.g. 0.02 for 2%)
    :param money_risk: Fixed money risk override, used only when
        account_balance is not supplied
    :return: Position units
    """
    return _default_order_manager.calculate_units(
        signal=trade_type,
        entry_price=entry_price,
        stop_loss=stop_loss,
        account_balance=account_balance,
        risk_percent=risk_percent,
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
    account_balance: Optional[float] = None,
    risk_percent: Optional[float] = None,
    money_risk: Optional[float] = None,
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
    :param account_balance: Current account balance; when supplied, position
        size is risk_percent of this balance instead of a fixed money amount
    :param risk_percent: Risk percentage override (fraction, e.g. 0.02 for 2%)
    :param money_risk: Fixed risk capital override, used only when
        account_balance is not supplied
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
        account_balance=account_balance,
        risk_percent=risk_percent,
        money_risk=money_risk,
    )
