# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pyTrade_GUIzkTsLA.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QSizePolicy, QWidget)
import resources_rc

class Ui_pyTrade(object):
    def setupUi(self, pyTrade):
        if not pyTrade.objectName():
            pyTrade.setObjectName(u"pyTrade")
        pyTrade.resize(790, 375)
        icon = QIcon()
        icon.addFile(u"images/windows/Square44x44Logo.altform-unplated_targetsize-24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        pyTrade.setWindowIcon(icon)
        self.lb_Pairs = QLabel(pyTrade)
        self.lb_Pairs.setObjectName(u"lb_Pairs")
        self.lb_Pairs.setGeometry(QRect(560, 30, 131, 32))
        font = QFont()
        font.setPointSize(14)
        self.lb_Pairs.setFont(font)
        self.lb_currentPairs = QLabel(pyTrade)
        self.lb_currentPairs.setObjectName(u"lb_currentPairs")
        self.lb_currentPairs.setGeometry(QRect(480, 40, 261, 21))
        self.lb_currentPairs.setFont(font)
        self.lb_Output = QLabel(pyTrade)
        self.lb_Output.setObjectName(u"lb_Output")
        self.lb_Output.setGeometry(QRect(50, 110, 171, 41))
        self.lb_Output.setFont(font)
        self.line = QFrame(pyTrade)
        self.line.setObjectName(u"line")
        self.line.setGeometry(QRect(60, 90, 691, 21))
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)
        self.pte_logOutput = QPlainTextEdit(pyTrade)
        self.pte_logOutput.setObjectName(u"pte_logOutput")
        self.pte_logOutput.setGeometry(QRect(50, 160, 691, 191))
        self.lb_logo = QLabel(pyTrade)
        self.lb_logo.setObjectName(u"lb_logo")
        self.lb_logo.setGeometry(QRect(60, 30, 161, 41))
        self.lb_logo.setPixmap(QPixmap(u":/images/logo_gui.png"))
        self.lb_logo.setScaledContents(True)
        self.widget = QWidget(pyTrade)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(270, 30, 253, 34))
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.pb_Start = QPushButton(self.widget)
        self.pb_Start.setObjectName(u"pb_Start")
        font1 = QFont()
        font1.setPointSize(16)
        self.pb_Start.setFont(font1)
        self.pb_Start.setCheckable(True)

        self.horizontalLayout.addWidget(self.pb_Start)

        self.pb_Stop = QPushButton(self.widget)
        self.pb_Stop.setObjectName(u"pb_Stop")
        self.pb_Stop.setEnabled(False)
        self.pb_Stop.setFont(font1)
        self.pb_Stop.setStyleSheet(u"background-color: rgb(224, 27, 36);\n"
"color: white;\n"
"")

        self.horizontalLayout.addWidget(self.pb_Stop)


        self.retranslateUi(pyTrade)

        QMetaObject.connectSlotsByName(pyTrade)
    # setupUi

    def retranslateUi(self, pyTrade):
        pyTrade.setWindowTitle(QCoreApplication.translate("pyTrade", u"pyTrade", None))
        self.lb_Pairs.setText(QCoreApplication.translate("pyTrade", u"Trading Pairs:", None))
        self.lb_currentPairs.setText("")
        self.lb_Output.setText(QCoreApplication.translate("pyTrade", u"Output:", None))
        self.lb_logo.setText("")
        self.pb_Start.setText(QCoreApplication.translate("pyTrade", u"Start", None))
        self.pb_Stop.setText(QCoreApplication.translate("pyTrade", u"Stop", None))
    # retranslateUi

