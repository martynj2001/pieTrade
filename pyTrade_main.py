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

        self.show()

    def btn_Start_Clicked(self):
    
        self.pb_Start.setStyleSheet("background-color: #4CE063; color: white;")
        self.pb_Stop.setStyleSheet(" ")
        self.pb_Start.setEnabled(False)
        self.pb_Stop.setEnabled(True)
    
        # Start pyTrade Worker Thread
        self.thread = QThread()
        self.worker = pyt.pyTradeWorker()

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run_bot)
        self.worker.msg.connect(self.update_output)
        self.worker.finished.connect(self.thread.quit)

        self.thread.start()

        self.started = True
    
    def btn_Stop_Clicked(self):

        self.update_output("Stopping.....")

        if self.started:
            self.pb_Start.setStyleSheet(" ")
            self.pb_Start.setEnabled(True)
            self.pb_Stop.setStyleSheet("background-color: rgb(224, 27, 36);")
            self.pb_Stop.setEnabled(False)
            msg = "pyTrade Bot stopped."
            self.update_output(msg=msg)
            self.started = False

            # Quite pyTrade_bot worker thread
            self.worker.stop_bot()
            self.thread.quit()
            self.thread.wait()
        else:
            msg = "pyTrade Bot not started. Click Start to start trading."
            self.update_output(msg=msg)

    
    def update_output(self, msg=' '):
        current_time = datetime.now(timezone.utc).strftime("%d/%m/%y-%H:%M")
        msg = f"{current_time}: {msg}" #need to format time to make it readable.
        self.pte_logOutput.appendPlainText(msg)

#Boiler plate - runs App
if __name__ == "__main__":

    app = qtw.QApplication(sys.argv)
    form = App_pyTrade()

    sys.exit(app.exec()) 