import sys
from PySide6 import QtWidgets as qtw
from PySide6.QtCore import QThread
import resources_rc # Contains GUI resources (images etc.)
from datetime import datetime, timezone

from ui_pyTrade_GUI import Ui_pyTrade
import pyTrade_bot as pyt


class App_pyTrade(qtw.QWidget, Ui_pyTrade):

    started = False

    def __init__(self):
        super().__init__()

        self.setupUi(self)

        # Button event handlers
        self.pb_Start.clicked.connect(self.btn_Start_Clicked) #change to start btn clicked
        self.pb_Stop.clicked.connect(self.btn_Stop_Clicked) #change to stop btn clicked

        self.lb_Markets.setVisible(False)
        self.lb_time.setVisible(False)
        
        self.show()

    def btn_Start_Clicked(self):
    
        self.pb_Start.setStyleSheet("background-color: #4CE063; color: white;")
        self.pb_Stop.setStyleSheet(" ")
        self.pb_Start.setEnabled(False)
        self.pb_Stop.setEnabled(True)
    
        # Start pyTrade Worker Thread
        self.thread = QThread() # type: ignore
        self.worker = pyt.pyTradeWorker()

        self.worker.moveToThread(self.thread)

        self.cb_strategy.currentTextChanged.connect(self.worker.on_set_strategy)
        self.cb_strategy.setEnabled(False)
        self.worker.on_set_strategy(self.cb_strategy.currentText())

        self.thread.started.connect(self.worker.run_bot)
        self.worker.msg.connect(self.update_output)
        self.worker.finished.connect(self.thread.quit)
        self.worker.market_info.connect(self.update_market_info)
        self.worker.market_open.connect(self.update_market_open)
        self.worker.account.connect(self.update_account_info)

        self.thread.start()

        self.started = True
    
    def btn_Stop_Clicked(self):

        self.update_output("Stopping.....")

        if self.started:
            #Update the GUI
            self.pb_Start.setStyleSheet(" ")
            self.pb_Start.setEnabled(True)
            self.pb_Stop.setStyleSheet("background-color: rgb(224, 27, 36);")
            self.pb_Stop.setEnabled(False)
            self.cb_strategy.setEnabled(False)
            self.lb_Markets.setVisible(False)
            self.lb_time.setVisible(False)
            self.lb_time.setVisible(False)
            self.lb_Title_1.setVisible(True)
            self.lb_title_2.setVisible(True)
            self.lb_market.setVisible(True)
            self.lb_instr.setVisible(True)

            msg = "pyTrade Bot stopped."
            self.update_output(msg=msg)
            self.started = False

            # Quit pyTrade_bot worker thread
            self.worker.stop_bot()
            self.thread.quit()
            self.thread.wait()

        else:
            msg = "pyTrade Bot not started. Click Start to start trading."
            self.update_output(msg=msg)

    
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
            self.lb_market.setStyleSheet("color: #2ECC71;")
            self.lb_instr.setStyleSheet("color: #2ECC71;")
            self.lb_Markets.setVisible(False)
            self.lb_time.setVisible(False)
            self.lb_Title_1.setVisible(True)
            self.lb_title_2.setVisible(True)
            self.lb_market.setVisible(True)
            self.lb_instr.setVisible(True)
        else:
            self.lb_market.setStyleSheet("color: rgb(224, 27, 36);")
            self.lb_instr.setStyleSheet("color: rgb(224, 27, 36);")
            self.lb_Markets.setVisible(True)
            self.lb_time.setVisible(True)
            self.lb_Title_1.setVisible(False)
            self.lb_title_2.setVisible(False)
            self.lb_market.setVisible(False)
            self.lb_instr.setVisible(False)

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
        self.lb_ac_openpos.setText(str(account_info["openPositionCount"]))
        self.lb_ac_opentrades.setText(str(account_info["openTradeCount"]))
        self.lb_ac_realPL.setText(str(account_info["pl"]))
        self.lb_ac_unrealPL.setText(str(account_info["unrealizedPL"]))
        self.lb_ac_balance.setText("£ " + str(account_info["balance"]))

#Boiler plate - runs App
if __name__ == "__main__":

    app = qtw.QApplication(sys.argv)
    form = App_pyTrade()

    sys.exit(app.exec()) 