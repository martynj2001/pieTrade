# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pyTrade_GUIqDkezH.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QPlainTextEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTabWidget, QVBoxLayout, QWidget)
import resources_rc
import resources_rc

class Ui_pyTrade(object):
    def setupUi(self, pyTrade):
        if not pyTrade.objectName():
            pyTrade.setObjectName(u"pyTrade")
        pyTrade.resize(778, 642)
        icon = QIcon()
        icon.addFile(u":/images/images/icon_32.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        pyTrade.setWindowIcon(icon)
        self.layoutWidget = QWidget(pyTrade)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(30, 10, 709, 571))
        self.verticalLayout_3 = QVBoxLayout(self.layoutWidget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.lb_logo = QLabel(self.layoutWidget)
        self.lb_logo.setObjectName(u"lb_logo")
        self.lb_logo.setPixmap(QPixmap(u":/images/images/logo_gui.png"))
        self.lb_logo.setScaledContents(True)

        self.horizontalLayout_2.addWidget(self.lb_logo)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pb_Start = QPushButton(self.layoutWidget)
        self.pb_Start.setObjectName(u"pb_Start")
        font = QFont()
        font.setPointSize(16)
        self.pb_Start.setFont(font)
        self.pb_Start.setCheckable(True)

        self.horizontalLayout.addWidget(self.pb_Start)

        self.pb_Stop = QPushButton(self.layoutWidget)
        self.pb_Stop.setObjectName(u"pb_Stop")
        self.pb_Stop.setEnabled(False)
        self.pb_Stop.setFont(font)
        self.pb_Stop.setStyleSheet(u"background-color: rgb(224, 27, 36);\n"
"color: white;\n"
"")

        self.horizontalLayout.addWidget(self.pb_Stop)


        self.horizontalLayout_2.addLayout(self.horizontalLayout)

        self.lb_strategy = QLabel(self.layoutWidget)
        self.lb_strategy.setObjectName(u"lb_strategy")
        font1 = QFont()
        font1.setPointSize(14)
        self.lb_strategy.setFont(font1)
        self.lb_strategy.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.lb_strategy)

        self.cb_strategy = QComboBox(self.layoutWidget)
        self.cb_strategy.addItem("")
        self.cb_strategy.addItem("")
        self.cb_strategy.setObjectName(u"cb_strategy")

        self.horizontalLayout_2.addWidget(self.cb_strategy)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalSpacer_2 = QSpacerItem(678, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.verticalLayout.addItem(self.horizontalSpacer_2)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.lb_Title_1 = QLabel(self.layoutWidget)
        self.lb_Title_1.setObjectName(u"lb_Title_1")
        self.lb_Title_1.setFont(font1)

        self.horizontalLayout_4.addWidget(self.lb_Title_1)

        self.lb_market = QLabel(self.layoutWidget)
        self.lb_market.setObjectName(u"lb_market")
        self.lb_market.setFont(font1)

        self.horizontalLayout_4.addWidget(self.lb_market)

        self.lb_title_2 = QLabel(self.layoutWidget)
        self.lb_title_2.setObjectName(u"lb_title_2")
        self.lb_title_2.setFont(font1)

        self.horizontalLayout_4.addWidget(self.lb_title_2)

        self.lb_instr = QLabel(self.layoutWidget)
        self.lb_instr.setObjectName(u"lb_instr")
        self.lb_instr.setFont(font1)

        self.horizontalLayout_4.addWidget(self.lb_instr)


        self.verticalLayout.addLayout(self.horizontalLayout_4)


        self.verticalLayout_3.addLayout(self.verticalLayout)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.verticalLayout_3.addItem(self.horizontalSpacer_3)

        self.lb_Markets = QLabel(self.layoutWidget)
        self.lb_Markets.setObjectName(u"lb_Markets")
        font2 = QFont()
        font2.setPointSize(18)
        self.lb_Markets.setFont(font2)
        self.lb_Markets.setStyleSheet(u"color: rgb(224, 27, 36);")
        self.lb_Markets.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.lb_Markets)

        self.lb_time = QLabel(self.layoutWidget)
        self.lb_time.setObjectName(u"lb_time")
        self.lb_time.setFont(font2)
        self.lb_time.setStyleSheet(u"color: rgb(224, 27, 36);")
        self.lb_time.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.lb_time)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.lb_AB_3 = QLabel(self.layoutWidget)
        self.lb_AB_3.setObjectName(u"lb_AB_3")
        self.lb_AB_3.setFont(font1)

        self.horizontalLayout_8.addWidget(self.lb_AB_3)

        self.lb_ac_openpos = QLabel(self.layoutWidget)
        self.lb_ac_openpos.setObjectName(u"lb_ac_openpos")
        self.lb_ac_openpos.setFont(font1)
        self.lb_ac_openpos.setMidLineWidth(0)
        self.lb_ac_openpos.setTextFormat(Qt.TextFormat.PlainText)
        self.lb_ac_openpos.setMargin(2)

        self.horizontalLayout_8.addWidget(self.lb_ac_openpos)

        self.lb_AB_4 = QLabel(self.layoutWidget)
        self.lb_AB_4.setObjectName(u"lb_AB_4")
        self.lb_AB_4.setFont(font1)

        self.horizontalLayout_8.addWidget(self.lb_AB_4)

        self.lb_ac_opentrades = QLabel(self.layoutWidget)
        self.lb_ac_opentrades.setObjectName(u"lb_ac_opentrades")
        self.lb_ac_opentrades.setFont(font1)
        self.lb_ac_opentrades.setMidLineWidth(0)
        self.lb_ac_opentrades.setTextFormat(Qt.TextFormat.PlainText)
        self.lb_ac_opentrades.setMargin(2)

        self.horizontalLayout_8.addWidget(self.lb_ac_opentrades)


        self.verticalLayout_2.addLayout(self.horizontalLayout_8)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.verticalLayout_2.addItem(self.horizontalSpacer_4)

        self.line = QFrame(self.layoutWidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_2.addWidget(self.line)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.verticalLayout_2.addItem(self.horizontalSpacer_6)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.lb_AB = QLabel(self.layoutWidget)
        self.lb_AB.setObjectName(u"lb_AB")
        self.lb_AB.setFont(font1)

        self.horizontalLayout_3.addWidget(self.lb_AB)

        self.lb_ac_balance = QLabel(self.layoutWidget)
        self.lb_ac_balance.setObjectName(u"lb_ac_balance")
        self.lb_ac_balance.setFont(font1)
        self.lb_ac_balance.setMidLineWidth(0)
        self.lb_ac_balance.setTextFormat(Qt.TextFormat.PlainText)
        self.lb_ac_balance.setMargin(2)

        self.horizontalLayout_3.addWidget(self.lb_ac_balance)

        self.lb_AB_5 = QLabel(self.layoutWidget)
        self.lb_AB_5.setObjectName(u"lb_AB_5")
        self.lb_AB_5.setFont(font1)

        self.horizontalLayout_3.addWidget(self.lb_AB_5)

        self.lb_ac_unrealPL = QLabel(self.layoutWidget)
        self.lb_ac_unrealPL.setObjectName(u"lb_ac_unrealPL")
        self.lb_ac_unrealPL.setFont(font1)
        self.lb_ac_unrealPL.setMidLineWidth(0)
        self.lb_ac_unrealPL.setTextFormat(Qt.TextFormat.PlainText)
        self.lb_ac_unrealPL.setMargin(2)

        self.horizontalLayout_3.addWidget(self.lb_ac_unrealPL)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.lb_AB_2 = QLabel(self.layoutWidget)
        self.lb_AB_2.setObjectName(u"lb_AB_2")
        self.lb_AB_2.setFont(font1)

        self.horizontalLayout_5.addWidget(self.lb_AB_2)

        self.lb_ac_NAV = QLabel(self.layoutWidget)
        self.lb_ac_NAV.setObjectName(u"lb_ac_NAV")
        self.lb_ac_NAV.setFont(font1)
        self.lb_ac_NAV.setMidLineWidth(0)
        self.lb_ac_NAV.setTextFormat(Qt.TextFormat.PlainText)
        self.lb_ac_NAV.setMargin(2)

        self.horizontalLayout_5.addWidget(self.lb_ac_NAV)

        self.lb_AB_6 = QLabel(self.layoutWidget)
        self.lb_AB_6.setObjectName(u"lb_AB_6")
        self.lb_AB_6.setFont(font1)

        self.horizontalLayout_5.addWidget(self.lb_AB_6)

        self.lb_ac_realPL = QLabel(self.layoutWidget)
        self.lb_ac_realPL.setObjectName(u"lb_ac_realPL")
        self.lb_ac_realPL.setFont(font1)
        self.lb_ac_realPL.setMidLineWidth(0)
        self.lb_ac_realPL.setTextFormat(Qt.TextFormat.PlainText)
        self.lb_ac_realPL.setMargin(2)

        self.horizontalLayout_5.addWidget(self.lb_ac_realPL)


        self.verticalLayout_2.addLayout(self.horizontalLayout_5)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.verticalLayout_2.addItem(self.horizontalSpacer_5)

        self.line_2 = QFrame(self.layoutWidget)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_2.addWidget(self.line_2)

        self.tabWidget = QTabWidget(self.layoutWidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tb_Candles = QWidget()
        self.tb_Candles.setObjectName(u"tb_Candles")
        self.label = QLabel(self.tb_Candles)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(290, 90, 91, 16))
        self.tabWidget.addTab(self.tb_Candles, "")
        self.tb_Output = QWidget()
        self.tb_Output.setObjectName(u"tb_Output")
        self.pte_logOutput = QPlainTextEdit(self.tb_Output)
        self.pte_logOutput.setObjectName(u"pte_logOutput")
        self.pte_logOutput.setGeometry(QRect(10, 10, 681, 221))
        self.tabWidget.addTab(self.tb_Output, "")

        self.verticalLayout_2.addWidget(self.tabWidget)


        self.verticalLayout_3.addLayout(self.verticalLayout_2)


        self.retranslateUi(pyTrade)

        self.tabWidget.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(pyTrade)
    # setupUi

    def retranslateUi(self, pyTrade):
        pyTrade.setWindowTitle(QCoreApplication.translate("pyTrade", u"pyTrade", None))
        self.lb_logo.setText("")
        self.pb_Start.setText(QCoreApplication.translate("pyTrade", u"Start", None))
        self.pb_Stop.setText(QCoreApplication.translate("pyTrade", u"Stop", None))
        self.lb_strategy.setText(QCoreApplication.translate("pyTrade", u"Strategy: ", None))
        self.cb_strategy.setItemText(0, QCoreApplication.translate("pyTrade", u"EMA Pullback", None))
        self.cb_strategy.setItemText(1, QCoreApplication.translate("pyTrade", u"Breakout", None))

        self.lb_Title_1.setText(QCoreApplication.translate("pyTrade", u"Current Market:", None))
        self.lb_market.setText(QCoreApplication.translate("pyTrade", u"-", None))
        self.lb_title_2.setText(QCoreApplication.translate("pyTrade", u"Current Instrument: ", None))
        self.lb_instr.setText(QCoreApplication.translate("pyTrade", u"-", None))
        self.lb_Markets.setText(QCoreApplication.translate("pyTrade", u"Markets Closed", None))
        self.lb_time.setText(QCoreApplication.translate("pyTrade", u"00:00", None))
        self.lb_AB_3.setText(QCoreApplication.translate("pyTrade", u"Open Positions:", None))
        self.lb_ac_openpos.setText(QCoreApplication.translate("pyTrade", u"-", None))
        self.lb_AB_4.setText(QCoreApplication.translate("pyTrade", u"Open Trades:", None))
        self.lb_ac_opentrades.setText(QCoreApplication.translate("pyTrade", u"-", None))
        self.lb_AB.setText(QCoreApplication.translate("pyTrade", u"Account Balance: ", None))
        self.lb_ac_balance.setText(QCoreApplication.translate("pyTrade", u"-", None))
        self.lb_AB_5.setText(QCoreApplication.translate("pyTrade", u"Unrealised P/L:", None))
        self.lb_ac_unrealPL.setText(QCoreApplication.translate("pyTrade", u"-", None))
        self.lb_AB_2.setText(QCoreApplication.translate("pyTrade", u"Net Asset Value (NAV):", None))
        self.lb_ac_NAV.setText(QCoreApplication.translate("pyTrade", u"-", None))
        self.lb_AB_6.setText(QCoreApplication.translate("pyTrade", u"Realised P/L:", None))
        self.lb_ac_realPL.setText(QCoreApplication.translate("pyTrade", u"-", None))
        self.label.setText(QCoreApplication.translate("pyTrade", u"Coming Soon", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tb_Candles), QCoreApplication.translate("pyTrade", u"Candle Chart", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tb_Output), QCoreApplication.translate("pyTrade", u"Output", None))
    # retranslateUi

