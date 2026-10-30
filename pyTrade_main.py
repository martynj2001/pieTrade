import logging
import sys
from PySide6 import QtWidgets as qtw
from PySide6.QtCore import QThread, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPalette
import resources_rc # Contains GUI resources (images etc.)
from datetime import datetime, timezone

from ui_pyTrade_GUI_v2 import Ui_pyTrade_v2
import pyTrade_bot as pyt
import pyTrade_market_session as market
from position_cards import PositionCardsPanel
from spinner_overlay import SpinnerOverlay
from candle_chart import CandleChartPanel
from pyTrade_logging import setup_logging
import pyTrade_settings as settings
from settings_panel import SettingsPanel

log = logging.getLogger("pyTrade.main")


def apply_dark_theme(app):
    # Force a dark look regardless of the desktop/launcher environment
    app.setStyle("Fusion")
    if hasattr(app.styleHints(), "setColorScheme"):
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    pal = QPalette()
    for role, colour in (
        (QPalette.ColorRole.Window, "#2b2b2b"), (QPalette.ColorRole.WindowText, "#e6e6e6"),
        (QPalette.ColorRole.Base, "#1e1e1e"), (QPalette.ColorRole.AlternateBase, "#2b2b2b"),
        (QPalette.ColorRole.Text, "#e6e6e6"), (QPalette.ColorRole.Button, "#353535"),
        (QPalette.ColorRole.ButtonText, "#e6e6e6"), (QPalette.ColorRole.ToolTipBase, "#353535"),
        (QPalette.ColorRole.ToolTipText, "#e6e6e6"), (QPalette.ColorRole.Highlight, "#F19E39"),
        (QPalette.ColorRole.HighlightedText, "#000000"),
        # Frame (Box/Sunken) borders are drawn from these roles
        (QPalette.ColorRole.Light, "#4a4a4a"), (QPalette.ColorRole.Midlight, "#3f3f3f"),
        (QPalette.ColorRole.Mid, "#2f2f2f"), (QPalette.ColorRole.Dark, "#1a1a1a"),
        (QPalette.ColorRole.Shadow, "#000000"), (QPalette.ColorRole.PlaceholderText, "#888888"),
    ):
        pal.setColor(role, QColor(colour))
    app.setPalette(pal)


class App_pyTrade(qtw.QMainWindow, Ui_pyTrade_v2):

    started = False

    def __init__(self):
        super().__init__()

        self.setupUi(self)

        # Remove the OS title bar (set here so Qt Designer regenerations don't overwrite it)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self._drag_pos = None

        # Button event handlers
        self.pb_Start.clicked.connect(self.btn_Start_Clicked) #change to start btn clicked
        self.pb_Stop.clicked.connect(self.btn_Stop_Clicked) #change to stop btn clicked
        self.pb_close.clicked.connect(self.btn_Close_Clicked)
        self.pb_minimise.clicked.connect(self.showMinimized)
        self.pb_fullscreen.clicked.connect(self.fullscreen_Clicked)

        # Menu navigation (button names in the UI file are swapped vs their labels)
        pages = {
            self.pb_candles: self.pg_candles,
            self.pb_output: self.pg_output,
            self.pb_settings: self.pg_openpositions,  # labelled "Open Positions"
            self.pb_openpositions: self.pg_settings,  # labelled "Settings"
        }
        for button, page in pages.items():
            button.clicked.connect(lambda _=False, p=page: self.stackedWidget.setCurrentWidget(p))

        self.position_panel = PositionCardsPanel(self.positions_cards)
        self.candle_chart = CandleChartPanel(self.candle_chart)
        self.settings_panel = SettingsPanel()
        self.settings_panel.settings_applied.connect(self._update_strategy_label)
        self._update_strategy_label(settings.load())
        settings_scroll = qtw.QScrollArea(self.frame_30)
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setWidget(self.settings_panel)
        settings_layout = qtw.QVBoxLayout(self.frame_30)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.addWidget(settings_scroll)
        self.spinner = SpinnerOverlay(self.centralwidget)
        self.log_spinner = SpinnerOverlay(self.pte_logOutput, diameter=40)
        self._closing = False
        self._stopping = False

        self.lb_Markets.setVisible(False) # Close Markets Label
        # Timer counting down to next open market.
        self._next_open = None
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)   # 1 second
        self.countdown_timer.timeout.connect(self._tick_countdown)

        self.stackedWidget.setCurrentWidget(self.pg_output)
        
        self.show()

    # Without a title bar, allow dragging the window by its background
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _update_strategy_label(self, values: dict) -> None:
        """Show 'Selected Strategy' in single mode, otherwise 'Primary Strategy'."""
        single = values.get("strategy_mode") == "single"
        self.label_11.setText("Selected Strategy" if single else "Primary Strategy")

    def btn_Start_Clicked(self):
    
        log.info("Start button clicked - starting bot")
        self.settings_panel.set_running(True)
        self.pb_Start.setStyleSheet("background-color: #4CE063; color: white;")
        self.pb_Stop.setStyleSheet(" ")
        self.pb_Start.setEnabled(False)
        self.pb_Stop.setEnabled(True)
    
        # Start pyTrade Worker Thread
        self.thread = QThread() # type: ignore
        self.worker = pyt.pyTradeWorker()

        self.worker.moveToThread(self.thread)

        self.comboBox.currentTextChanged.connect(self.worker.on_set_strategy)
        self.comboBox.setEnabled(False)
        self.worker.on_set_strategy(self.comboBox.currentText())
        self.worker.apply_settings(settings.load())
        self.settings_panel.settings_applied.connect(self.worker.apply_settings)

        self.thread.started.connect(self.worker.run_bot)
        self.worker.msg.connect(self.update_output)
        self.worker.finished.connect(self.thread.quit)
        self.worker.market_info.connect(self.update_market_info)
        self.worker.market_open.connect(self.update_market_open)
        self.worker.account.connect(self.update_account_info)
        self.worker.positions.connect(self.position_panel.update_positions)
        self.worker.candles.connect(self.candle_chart.update_candles)
        self.worker.trade_levels.connect(self.candle_chart.update_trade_levels)

        self.thread.finished.connect(self._on_thread_finished)
        self.thread.start()

        self.started = True
    
    def btn_Stop_Clicked(self):

        log.info("Stop button clicked")
        self.settings_panel.set_running(False)
        if self.started:
            self.update_output("Stopping.....")
            self.pb_Stop.setStyleSheet("background-color: rgb(224, 27, 36);")
            self.pb_Stop.setEnabled(False)
            self.comboBox.setEnabled(True)
            self.countdown_timer.stop()
            self.lb_Markets.setVisible(False)
            self.lb_market.setVisible(True)
            self.lb_instr.setVisible(True)

            # Wait for the worker thread without blocking the GUI, so the spinner keeps turning
            self.started = False
            self._stopping = True
            self.log_spinner.start()
            self.worker.stop_bot()

        elif not self._stopping:
            self.update_output("pyTrade Bot not started. Click Start to start trading.")

    def _on_thread_finished(self):

        self.log_spinner.stop()
        self.settings_panel.set_running(False)
        if self._stopping:
            self._stopping = False
            self.pb_Start.setStyleSheet(" ")
            self.pb_Start.setEnabled(True)
            self.update_output("pyTrade Bot stopped.")

    def btn_Close_Clicked(self):

        log.info("Close button clicked - shutting down")
        if self._closing:
            return
        self._closing = True
        self.update_output("Shutting Down .....")

        if self.started or self._stopping:
            # Wait for the worker thread without blocking the GUI, so the spinner keeps turning
            self.started = False
            self.spinner.start()
            self.centralwidget.setEnabled(False)
            self.thread.finished.connect(self._finish_close)
            self.worker.stop_bot()
        else:
            self.close()

    def _finish_close(self):

        self.spinner.stop()
        self.close()

    def fullscreen_Clicked(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self._update_fullscreen_icon()

    def _update_fullscreen_icon(self):
        name = "close_fullscreen" if self.isFullScreen() else "fullscreen"
        self.pb_fullscreen.setIcon(QIcon(f":/icons/icons/{name}.svg"))

    def update_output(self, msg=' '):
        current_time = datetime.now(timezone.utc).strftime("%d/%m/%y-%H:%M")
        msg = f"{current_time}: {msg}" 
        self.pte_logOutput.appendPlainText(msg)

    def update_market_info(self, market_info):

        if market_info["market"] is None:
            self.lb_market.setText("N/A")
            self.lb_instr.setText("N/A")
            return

        market = market_info["market"].replace("_", " ").title()
        instr = market_info["instrument"].replace("_", "/")
        self.lb_market.setText(market)
        self.lb_instr.setText(instr)

    def update_market_open(self, is_open):
        if is_open:
            self.countdown_timer.stop()
            self.lb_Markets.setText("Markets Closed") # Reset for next time
            self.lb_market.setStyleSheet("color: #2ECC71;")
            self.lb_instr.setStyleSheet("color: #2ECC71;")
            self.lb_Markets.setVisible(False)
            
        else:
            self.lb_market.setStyleSheet("color: rgb(224, 27, 36);")
            self.lb_instr.setStyleSheet("color: rgb(224, 27, 36);")
            self.lb_Markets.setVisible(True)
            self._next_open = market.next_open(datetime.now(timezone.utc))
            self._tick_countdown()          # show immediately, don't wait 1s
            self.countdown_timer.start()

    def update_account_info(self, account_info):

        if account_info["NAV"] < 0:
            self.lb_ac_NAV.setStyleSheet("color: rgb(224, 27, 36);")
        else:
            self.lb_ac_NAV.setStyleSheet("color: #2ECC71;")

        if account_info["balance"] < 0:
            self.lb_ac_balance.setStyleSheet("color: rgb(224, 27, 36);")
        else:
            self.lb_ac_balance.setStyleSheet("color: #2ECC71;")

        if account_info["pl"] < 0:
            self.lb_ac_realPL.setStyleSheet("color: rgb(224, 27, 36);")
        else:
            self.lb_ac_realPL.setStyleSheet("color: #2ECC71;")

        if account_info["unrealizedPL"] < 0:
            self.lb_ac_unrealPL.setStyleSheet("color: rgb(224, 27, 36);")
        else:
            self.lb_ac_unrealPL.setStyleSheet("color: #2ECC71;")

        self.lb_ac_NAV.setText("£ " + str(account_info["NAV"]))
        self.lb_openpos.setText(str(account_info["openPositionCount"]))
        self.lb_opentrades.setText(str(account_info["openTradeCount"]))
        self.lb_ac_realPL.setText(str(account_info["pl"]))
        self.lb_ac_unrealPL.setText(str(account_info["unrealizedPL"]))
        self.lb_ac_balance.setText("£ " + str(account_info["balance"]))

    def _tick_countdown(self):
        if self._next_open is None:
            return
        secs = int((self._next_open - datetime.now(timezone.utc)).total_seconds())
        if secs <= 0:
            self.lb_Markets.setText("Markets opening...")
            return
        days, rem = divmod(secs, 86400)
        hours, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)
        text = f"{hours:02}:{mins:02}:{secs:02}"
        if days:
            text = f"{days}d {text}"
        self.lb_Markets.setText(f"Markets Closed - opens in {text}")

#Boiler plate - runs App
if __name__ == "__main__":

    setup_logging()
    log.info("pyTrade GUI started")

    app = qtw.QApplication(sys.argv)
    apply_dark_theme(app)
    app.setApplicationName("pyTrade")
    app.setDesktopFileName("pyTrade")  # matches ~/Desktop/pyTrade.desktop so the taskbar groups/icons correctly
    app_icon = QIcon()
    for size in (32, 64, 256):
        app_icon.addFile(f":/images/images/icon_{size}.png")
    app.setWindowIcon(app_icon)
    form = App_pyTrade()

    sys.exit(app.exec()) 