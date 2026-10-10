# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pyTrade_GUI_v2ygKBWl.ui'
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
    QLabel, QMainWindow, QPlainTextEdit, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout,
    QWidget)
import resources_rc

class Ui_pyTrade_v2(object):
    def setupUi(self, pyTrade_v2):
        if not pyTrade_v2.objectName():
            pyTrade_v2.setObjectName(u"pyTrade_v2")
        pyTrade_v2.resize(1072, 820)
        self.centralwidget = QWidget(pyTrade_v2)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_7 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.frame_12 = QFrame(self.centralwidget)
        self.frame_12.setObjectName(u"frame_12")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_12.sizePolicy().hasHeightForWidth())
        self.frame_12.setSizePolicy(sizePolicy)
        self.frame_12.setMinimumSize(QSize(0, 30))
        self.frame_12.setMaximumSize(QSize(16777215, 50))
        self.frame_12.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_12.setFrameShadow(QFrame.Shadow.Sunken)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_12)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(-1, 0, 0, 0)
        self.frame_14 = QFrame(self.frame_12)
        self.frame_14.setObjectName(u"frame_14")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_14.sizePolicy().hasHeightForWidth())
        self.frame_14.setSizePolicy(sizePolicy1)
        self.frame_14.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_14.setFrameShadow(QFrame.Shadow.Plain)
        self.horizontalLayout_6 = QHBoxLayout(self.frame_14)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_10 = QLabel(self.frame_14)
        self.label_10.setObjectName(u"label_10")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.label_10.sizePolicy().hasHeightForWidth())
        self.label_10.setSizePolicy(sizePolicy2)
        self.label_10.setPixmap(QPixmap(u":/images/images/logo_gui.png"))
        self.label_10.setScaledContents(False)

        self.horizontalLayout_6.addWidget(self.label_10)


        self.horizontalLayout_5.addWidget(self.frame_14)

        self.frame_15 = QFrame(self.frame_12)
        self.frame_15.setObjectName(u"frame_15")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.frame_15.sizePolicy().hasHeightForWidth())
        self.frame_15.setSizePolicy(sizePolicy3)
        self.frame_15.setMinimumSize(QSize(165, 0))
        self.frame_15.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_15.setFrameShadow(QFrame.Shadow.Plain)
        self.horizontalLayout_9 = QHBoxLayout(self.frame_15)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.lb_Markets = QLabel(self.frame_15)
        self.lb_Markets.setObjectName(u"lb_Markets")
        self.lb_Markets.setMinimumSize(QSize(90, 0))
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.lb_Markets.setFont(font)
        self.lb_Markets.setStyleSheet(u"color: red;")

        self.horizontalLayout_9.addWidget(self.lb_Markets)


        self.horizontalLayout_5.addWidget(self.frame_15)

        self.frame_16 = QFrame(self.frame_12)
        self.frame_16.setObjectName(u"frame_16")
        sizePolicy1.setHeightForWidth(self.frame_16.sizePolicy().hasHeightForWidth())
        self.frame_16.setSizePolicy(sizePolicy1)
        font1 = QFont()
        font1.setPointSize(14)
        self.frame_16.setFont(font1)
        self.frame_16.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_16.setFrameShadow(QFrame.Shadow.Plain)
        self.horizontalLayout_7 = QHBoxLayout(self.frame_16)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.pb_Start = QPushButton(self.frame_16)
        self.pb_Start.setObjectName(u"pb_Start")
        icon = QIcon()
        icon.addFile(u":/icons/icons/play_circle_24dp_F19E39_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pb_Start.setIcon(icon)
        self.pb_Start.setIconSize(QSize(24, 24))

        self.horizontalLayout_7.addWidget(self.pb_Start)

        self.pb_Stop = QPushButton(self.frame_16)
        self.pb_Stop.setObjectName(u"pb_Stop")
        icon1 = QIcon()
        icon1.addFile(u":/icons/icons/stop_circle_24dp_F19E39_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pb_Stop.setIcon(icon1)
        self.pb_Stop.setIconSize(QSize(24, 24))

        self.horizontalLayout_7.addWidget(self.pb_Stop)


        self.horizontalLayout_5.addWidget(self.frame_16)

        self.frame_17 = QFrame(self.frame_12)
        self.frame_17.setObjectName(u"frame_17")
        self.frame_17.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_17.setFrameShadow(QFrame.Shadow.Plain)
        self.horizontalLayout_8 = QHBoxLayout(self.frame_17)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.pb_minimise = QPushButton(self.frame_17)
        self.pb_minimise.setObjectName(u"pb_minimise")
        icon2 = QIcon()
        icon2.addFile(u":/icons/icons/minimize_24dp_F19E39_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pb_minimise.setIcon(icon2)
        self.pb_minimise.setIconSize(QSize(24, 24))

        self.horizontalLayout_8.addWidget(self.pb_minimise)

        self.pb_fullscreen = QPushButton(self.frame_17)
        self.pb_fullscreen.setObjectName(u"pb_fullscreen")
        icon3 = QIcon()
        icon3.addFile(u":/icons/icons/fullscreen.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pb_fullscreen.setIcon(icon3)
        self.pb_fullscreen.setIconSize(QSize(24, 24))

        self.horizontalLayout_8.addWidget(self.pb_fullscreen)

        self.pb_close = QPushButton(self.frame_17)
        self.pb_close.setObjectName(u"pb_close")
        icon4 = QIcon()
        icon4.addFile(u":/icons/icons/close_24dp_F19E39_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pb_close.setIcon(icon4)
        self.pb_close.setIconSize(QSize(24, 24))

        self.horizontalLayout_8.addWidget(self.pb_close)


        self.horizontalLayout_5.addWidget(self.frame_17)


        self.verticalLayout_7.addWidget(self.frame_12)

        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.frame = QFrame(self.frame_2)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.Box)
        self.frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.verticalLayout = QVBoxLayout(self.frame)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frame_5 = QFrame(self.frame)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.Shape.Box)
        self.frame_5.setFrameShadow(QFrame.Shadow.Sunken)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_5)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_20 = QLabel(self.frame_5)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setMinimumSize(QSize(30, 30))
        self.label_20.setMaximumSize(QSize(30, 30))
        self.label_20.setPixmap(QPixmap(u":/icons/icons/menu_24dp_F19E39_FILL0_wght400_GRAD0_opsz24.svg"))
        self.label_20.setScaledContents(True)

        self.horizontalLayout_2.addWidget(self.label_20)

        self.label_9 = QLabel(self.frame_5)
        self.label_9.setObjectName(u"label_9")
        font2 = QFont()
        font2.setPointSize(16)
        self.label_9.setFont(font2)
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_2.addWidget(self.label_9)


        self.verticalLayout.addWidget(self.frame_5)

        self.frame_6 = QFrame(self.frame)
        self.frame_6.setObjectName(u"frame_6")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.frame_6.sizePolicy().hasHeightForWidth())
        self.frame_6.setSizePolicy(sizePolicy4)
        self.frame_6.setFrameShape(QFrame.Shape.Box)
        self.frame_6.setFrameShadow(QFrame.Shadow.Sunken)
        self.verticalLayout_6 = QVBoxLayout(self.frame_6)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.frame_31 = QFrame(self.frame_6)
        self.frame_31.setObjectName(u"frame_31")
        sizePolicy4.setHeightForWidth(self.frame_31.sizePolicy().hasHeightForWidth())
        self.frame_31.setSizePolicy(sizePolicy4)
        self.frame_31.setMaximumSize(QSize(16777215, 16777215))
        self.frame_31.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_31.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_14 = QVBoxLayout(self.frame_31)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.pb_output = QPushButton(self.frame_31)
        self.pb_output.setObjectName(u"pb_output")
        sizePolicy4.setHeightForWidth(self.pb_output.sizePolicy().hasHeightForWidth())
        self.pb_output.setSizePolicy(sizePolicy4)

        self.verticalLayout_14.addWidget(self.pb_output)

        self.pb_settings = QPushButton(self.frame_31)
        self.pb_settings.setObjectName(u"pb_settings")
        sizePolicy4.setHeightForWidth(self.pb_settings.sizePolicy().hasHeightForWidth())
        self.pb_settings.setSizePolicy(sizePolicy4)

        self.verticalLayout_14.addWidget(self.pb_settings)

        self.pb_candles = QPushButton(self.frame_31)
        self.pb_candles.setObjectName(u"pb_candles")
        sizePolicy4.setHeightForWidth(self.pb_candles.sizePolicy().hasHeightForWidth())
        self.pb_candles.setSizePolicy(sizePolicy4)

        self.verticalLayout_14.addWidget(self.pb_candles)

        self.pb_openpositions = QPushButton(self.frame_31)
        self.pb_openpositions.setObjectName(u"pb_openpositions")
        sizePolicy4.setHeightForWidth(self.pb_openpositions.sizePolicy().hasHeightForWidth())
        self.pb_openpositions.setSizePolicy(sizePolicy4)

        self.verticalLayout_14.addWidget(self.pb_openpositions)


        self.verticalLayout_6.addWidget(self.frame_31)

        self.frame_13 = QFrame(self.frame_6)
        self.frame_13.setObjectName(u"frame_13")
        sizePolicy2.setHeightForWidth(self.frame_13.sizePolicy().hasHeightForWidth())
        self.frame_13.setSizePolicy(sizePolicy2)
        self.frame_13.setMinimumSize(QSize(0, 100))
        self.frame_13.setMaximumSize(QSize(16777215, 0))
        self.frame_13.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_13.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_13)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_11 = QLabel(self.frame_13)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_4.addWidget(self.label_11)

        self.comboBox = QComboBox(self.frame_13)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")

        self.horizontalLayout_4.addWidget(self.comboBox)


        self.verticalLayout_6.addWidget(self.frame_13, 0, Qt.AlignmentFlag.AlignTop)


        self.verticalLayout.addWidget(self.frame_6)

        self.frame_3 = QFrame(self.frame)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.Shape.Box)
        self.frame_3.setFrameShadow(QFrame.Shadow.Sunken)
        self.horizontalLayout_14 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.label_19 = QLabel(self.frame_3)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setMinimumSize(QSize(30, 30))
        self.label_19.setMaximumSize(QSize(30, 30))
        self.label_19.setPixmap(QPixmap(u":/icons/icons/list_alt_24dp_F19E39_FILL0_wght400_GRAD0_opsz24.svg"))
        self.label_19.setScaledContents(True)
        self.label_19.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_14.addWidget(self.label_19)

        self.label = QLabel(self.frame_3)
        self.label.setObjectName(u"label")
        self.label.setFont(font2)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_14.addWidget(self.label)


        self.verticalLayout.addWidget(self.frame_3, 0, Qt.AlignmentFlag.AlignTop)

        self.frame_4 = QFrame(self.frame)
        self.frame_4.setObjectName(u"frame_4")
        sizePolicy4.setHeightForWidth(self.frame_4.sizePolicy().hasHeightForWidth())
        self.frame_4.setSizePolicy(sizePolicy4)
        self.frame_4.setFrameShape(QFrame.Shape.Box)
        self.frame_4.setFrameShadow(QFrame.Shadow.Sunken)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.frame_9 = QFrame(self.frame_4)
        self.frame_9.setObjectName(u"frame_9")
        self.frame_9.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_9.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_4 = QVBoxLayout(self.frame_9)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label_2 = QLabel(self.frame_9)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout_4.addWidget(self.label_2)

        self.label_3 = QLabel(self.frame_9)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout_4.addWidget(self.label_3)

        self.label_5 = QLabel(self.frame_9)
        self.label_5.setObjectName(u"label_5")

        self.verticalLayout_4.addWidget(self.label_5)

        self.label_8 = QLabel(self.frame_9)
        self.label_8.setObjectName(u"label_8")

        self.verticalLayout_4.addWidget(self.label_8)


        self.horizontalLayout_3.addWidget(self.frame_9)

        self.frame_8 = QFrame(self.frame_4)
        self.frame_8.setObjectName(u"frame_8")
        sizePolicy3.setHeightForWidth(self.frame_8.sizePolicy().hasHeightForWidth())
        self.frame_8.setSizePolicy(sizePolicy3)
        self.frame_8.setMinimumSize(QSize(65, 0))
        self.frame_8.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_8.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_8)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.lb_market = QLabel(self.frame_8)
        self.lb_market.setObjectName(u"lb_market")

        self.verticalLayout_3.addWidget(self.lb_market)

        self.lb_instr = QLabel(self.frame_8)
        self.lb_instr.setObjectName(u"lb_instr")

        self.verticalLayout_3.addWidget(self.lb_instr)

        self.lb_openpos = QLabel(self.frame_8)
        self.lb_openpos.setObjectName(u"lb_openpos")

        self.verticalLayout_3.addWidget(self.lb_openpos)

        self.lb_opentrades = QLabel(self.frame_8)
        self.lb_opentrades.setObjectName(u"lb_opentrades")

        self.verticalLayout_3.addWidget(self.lb_opentrades)


        self.horizontalLayout_3.addWidget(self.frame_8)

        self.frame_7 = QFrame(self.frame_4)
        self.frame_7.setObjectName(u"frame_7")
        self.frame_7.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_7.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_7)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_4 = QLabel(self.frame_7)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout_2.addWidget(self.label_4)

        self.label_12 = QLabel(self.frame_7)
        self.label_12.setObjectName(u"label_12")

        self.verticalLayout_2.addWidget(self.label_12)

        self.label_7 = QLabel(self.frame_7)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout_2.addWidget(self.label_7)

        self.label_6 = QLabel(self.frame_7)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout_2.addWidget(self.label_6)


        self.horizontalLayout_3.addWidget(self.frame_7)

        self.frame_10 = QFrame(self.frame_4)
        self.frame_10.setObjectName(u"frame_10")
        sizePolicy3.setHeightForWidth(self.frame_10.sizePolicy().hasHeightForWidth())
        self.frame_10.setSizePolicy(sizePolicy3)
        self.frame_10.setMinimumSize(QSize(65, 0))
        self.frame_10.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_10.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_5 = QVBoxLayout(self.frame_10)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.lb_ac_balance = QLabel(self.frame_10)
        self.lb_ac_balance.setObjectName(u"lb_ac_balance")

        self.verticalLayout_5.addWidget(self.lb_ac_balance)

        self.lb_ac_NAV = QLabel(self.frame_10)
        self.lb_ac_NAV.setObjectName(u"lb_ac_NAV")

        self.verticalLayout_5.addWidget(self.lb_ac_NAV)

        self.lb_ac_unrealPL = QLabel(self.frame_10)
        self.lb_ac_unrealPL.setObjectName(u"lb_ac_unrealPL")

        self.verticalLayout_5.addWidget(self.lb_ac_unrealPL)

        self.lb_ac_realPL = QLabel(self.frame_10)
        self.lb_ac_realPL.setObjectName(u"lb_ac_realPL")

        self.verticalLayout_5.addWidget(self.lb_ac_realPL)


        self.horizontalLayout_3.addWidget(self.frame_10)


        self.verticalLayout.addWidget(self.frame_4)


        self.horizontalLayout.addWidget(self.frame)

        self.frame_11 = QFrame(self.frame_2)
        self.frame_11.setObjectName(u"frame_11")
        self.frame_11.setFrameShape(QFrame.Shape.Box)
        self.frame_11.setFrameShadow(QFrame.Shadow.Sunken)
        self.verticalLayout_8 = QVBoxLayout(self.frame_11)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.frame_18 = QFrame(self.frame_11)
        self.frame_18.setObjectName(u"frame_18")
        self.frame_18.setFrameShape(QFrame.Shape.Box)
        self.frame_18.setFrameShadow(QFrame.Shadow.Sunken)
        self.horizontalLayout_13 = QHBoxLayout(self.frame_18)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.label_21 = QLabel(self.frame_18)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setMinimumSize(QSize(30, 30))
        self.label_21.setMaximumSize(QSize(30, 30))
        self.label_21.setPixmap(QPixmap(u":/icons/icons/dashboard_2_24dp_F19E39_FILL0_wght400_GRAD0_opsz24.svg"))
        self.label_21.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_13.addWidget(self.label_21)

        self.label_14 = QLabel(self.frame_18)
        self.label_14.setObjectName(u"label_14")
        font3 = QFont()
        font3.setFamilies([u"Ubuntu"])
        font3.setPointSize(16)
        self.label_14.setFont(font3)
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_13.addWidget(self.label_14)


        self.verticalLayout_8.addWidget(self.frame_18)

        self.frame_19 = QFrame(self.frame_11)
        self.frame_19.setObjectName(u"frame_19")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.frame_19.sizePolicy().hasHeightForWidth())
        self.frame_19.setSizePolicy(sizePolicy5)
        self.frame_19.setFrameShape(QFrame.Shape.Box)
        self.frame_19.setFrameShadow(QFrame.Shadow.Sunken)
        self.verticalLayout_9 = QVBoxLayout(self.frame_19)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.stackedWidget = QStackedWidget(self.frame_19)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.pg_openpositions = QWidget()
        self.pg_openpositions.setObjectName(u"pg_openpositions")
        self.verticalLayout_10 = QVBoxLayout(self.pg_openpositions)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.frame_23 = QFrame(self.pg_openpositions)
        self.frame_23.setObjectName(u"frame_23")
        self.frame_23.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_23.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_11 = QVBoxLayout(self.frame_23)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.label_15 = QLabel(self.frame_23)
        self.label_15.setObjectName(u"label_15")
        font4 = QFont()
        font4.setPointSize(12)
        font4.setBold(True)
        self.label_15.setFont(font4)
        self.label_15.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_11.addWidget(self.label_15, 0, Qt.AlignmentFlag.AlignTop)


        self.verticalLayout_10.addWidget(self.frame_23, 0, Qt.AlignmentFlag.AlignTop)

        self.frame_24 = QFrame(self.pg_openpositions)
        self.frame_24.setObjectName(u"frame_24")
        sizePolicy4.setHeightForWidth(self.frame_24.sizePolicy().hasHeightForWidth())
        self.frame_24.setSizePolicy(sizePolicy4)
        self.frame_24.setStyleSheet(u"background-image: url(:/images/images/Icon_trans.png);\n"
"background-repeat: no-repeat;\n"
"background-position: center;")
        self.frame_24.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_24.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_15 = QHBoxLayout(self.frame_24)
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.horizontalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.positions_cards = QScrollArea(self.frame_24)
        self.positions_cards.setObjectName(u"positions_cards")
        self.positions_cards.setFrameShape(QFrame.Shape.NoFrame)
        self.positions_cards.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 524, 542))
        self.positions_cards.setWidget(self.scrollAreaWidgetContents)

        self.horizontalLayout_15.addWidget(self.positions_cards)


        self.verticalLayout_10.addWidget(self.frame_24)

        self.stackedWidget.addWidget(self.pg_openpositions)
        self.pg_candles = QWidget()
        self.pg_candles.setObjectName(u"pg_candles")
        self.verticalLayout_13 = QVBoxLayout(self.pg_candles)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.frame_25 = QFrame(self.pg_candles)
        self.frame_25.setObjectName(u"frame_25")
        self.frame_25.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_25.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_12 = QVBoxLayout(self.frame_25)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.label_16 = QLabel(self.frame_25)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setFont(font4)
        self.label_16.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_12.addWidget(self.label_16, 0, Qt.AlignmentFlag.AlignTop)


        self.verticalLayout_13.addWidget(self.frame_25)

        self.frame_26 = QFrame(self.pg_candles)
        self.frame_26.setObjectName(u"frame_26")
        sizePolicy4.setHeightForWidth(self.frame_26.sizePolicy().hasHeightForWidth())
        self.frame_26.setSizePolicy(sizePolicy4)
        self.frame_26.setStyleSheet(u"background-image: url(:/images/images/Icon_trans.png);\n"
"background-repeat: no-repeat;\n"
"background-position: center;")
        self.frame_26.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_26.setFrameShadow(QFrame.Shadow.Raised)

        self.verticalLayout_13.addWidget(self.frame_26)

        self.stackedWidget.addWidget(self.pg_candles)
        self.pg_output = QWidget()
        self.pg_output.setObjectName(u"pg_output")
        self.verticalLayout_15 = QVBoxLayout(self.pg_output)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.frame_27 = QFrame(self.pg_output)
        self.frame_27.setObjectName(u"frame_27")
        font5 = QFont()
        font5.setBold(True)
        self.frame_27.setFont(font5)
        self.frame_27.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_27.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_16 = QHBoxLayout(self.frame_27)
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.label_17 = QLabel(self.frame_27)
        self.label_17.setObjectName(u"label_17")
        self.label_17.setFont(font4)
        self.label_17.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_16.addWidget(self.label_17)


        self.verticalLayout_15.addWidget(self.frame_27, 0, Qt.AlignmentFlag.AlignTop)

        self.frame_28 = QFrame(self.pg_output)
        self.frame_28.setObjectName(u"frame_28")
        sizePolicy4.setHeightForWidth(self.frame_28.sizePolicy().hasHeightForWidth())
        self.frame_28.setSizePolicy(sizePolicy4)
        self.frame_28.setStyleSheet(u"background-image: url(:/images/images/Icon_trans.png);\n"
"background-repeat: no-repeat;\n"
"background-position: center;")
        self.frame_28.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_28.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_17 = QHBoxLayout(self.frame_28)
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.pte_logOutput = QPlainTextEdit(self.frame_28)
        self.pte_logOutput.setObjectName(u"pte_logOutput")
        sizePolicy5.setHeightForWidth(self.pte_logOutput.sizePolicy().hasHeightForWidth())
        self.pte_logOutput.setSizePolicy(sizePolicy5)
        self.pte_logOutput.setStyleSheet(u"background: transparent;\n"
"border: line 1px;")

        self.horizontalLayout_17.addWidget(self.pte_logOutput)


        self.verticalLayout_15.addWidget(self.frame_28)

        self.stackedWidget.addWidget(self.pg_output)
        self.pg_settings = QWidget()
        self.pg_settings.setObjectName(u"pg_settings")
        self.verticalLayout_17 = QVBoxLayout(self.pg_settings)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.frame_29 = QFrame(self.pg_settings)
        self.frame_29.setObjectName(u"frame_29")
        self.frame_29.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_29.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_16 = QVBoxLayout(self.frame_29)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.label_18 = QLabel(self.frame_29)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setFont(font4)
        self.label_18.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_16.addWidget(self.label_18, 0, Qt.AlignmentFlag.AlignTop)


        self.verticalLayout_17.addWidget(self.frame_29)

        self.frame_30 = QFrame(self.pg_settings)
        self.frame_30.setObjectName(u"frame_30")
        sizePolicy4.setHeightForWidth(self.frame_30.sizePolicy().hasHeightForWidth())
        self.frame_30.setSizePolicy(sizePolicy4)
        self.frame_30.setStyleSheet(u"background-image: url(:/images/images/Icon_trans.png);\n"
"background-repeat: no-repeat;\n"
"background-position: center;")
        self.frame_30.setFrameShape(QFrame.Shape.Box)
        self.frame_30.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_17.addWidget(self.frame_30)

        self.stackedWidget.addWidget(self.pg_settings)

        self.verticalLayout_9.addWidget(self.stackedWidget)


        self.verticalLayout_8.addWidget(self.frame_19)

        self.frame_20 = QFrame(self.frame_11)
        self.frame_20.setObjectName(u"frame_20")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.frame_20.sizePolicy().hasHeightForWidth())
        self.frame_20.setSizePolicy(sizePolicy6)
        self.frame_20.setMaximumSize(QSize(16777215, 30))
        self.frame_20.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_20.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_10 = QHBoxLayout(self.frame_20)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.frame_21 = QFrame(self.frame_20)
        self.frame_21.setObjectName(u"frame_21")
        self.frame_21.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_21.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_11 = QHBoxLayout(self.frame_21)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.label_13 = QLabel(self.frame_21)
        self.label_13.setObjectName(u"label_13")
        font6 = QFont()
        font6.setPointSize(8)
        self.label_13.setFont(font6)

        self.horizontalLayout_11.addWidget(self.label_13)


        self.horizontalLayout_10.addWidget(self.frame_21)

        self.frame_22 = QFrame(self.frame_20)
        self.frame_22.setObjectName(u"frame_22")
        self.frame_22.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_22.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_12 = QHBoxLayout(self.frame_22)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.size_grip = QFrame(self.frame_22)
        self.size_grip.setObjectName(u"size_grip")
        self.size_grip.setFrameShape(QFrame.Shape.StyledPanel)
        self.size_grip.setFrameShadow(QFrame.Shadow.Raised)

        self.horizontalLayout_12.addWidget(self.size_grip, 0, Qt.AlignmentFlag.AlignRight)


        self.horizontalLayout_10.addWidget(self.frame_22)


        self.verticalLayout_8.addWidget(self.frame_20)


        self.horizontalLayout.addWidget(self.frame_11)


        self.verticalLayout_7.addWidget(self.frame_2)

        pyTrade_v2.setCentralWidget(self.centralwidget)

        self.retranslateUi(pyTrade_v2)

        self.stackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(pyTrade_v2)
    # setupUi

    def retranslateUi(self, pyTrade_v2):
        pyTrade_v2.setWindowTitle(QCoreApplication.translate("pyTrade_v2", u"MainWindow", None))
        self.label_10.setText("")
        self.lb_Markets.setText(QCoreApplication.translate("pyTrade_v2", u"Markets Closed", None))
        self.pb_Start.setText(QCoreApplication.translate("pyTrade_v2", u"Start", None))
        self.pb_Stop.setText(QCoreApplication.translate("pyTrade_v2", u"Stop", None))
        self.pb_minimise.setText("")
        self.pb_fullscreen.setText("")
        self.pb_close.setText("")
        self.label_20.setText("")
        self.label_9.setText(QCoreApplication.translate("pyTrade_v2", u"Menu", None))
        self.pb_output.setText(QCoreApplication.translate("pyTrade_v2", u"Output/Log", None))
        self.pb_settings.setText(QCoreApplication.translate("pyTrade_v2", u"Open Positions", None))
        self.pb_candles.setText(QCoreApplication.translate("pyTrade_v2", u"Candles Chart", None))
        self.pb_openpositions.setText(QCoreApplication.translate("pyTrade_v2", u"Settings", None))
        self.label_11.setText(QCoreApplication.translate("pyTrade_v2", u"Primary Strategy", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("pyTrade_v2", u"EMA Pullback", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("pyTrade_v2", u"Breakout", None))

        self.label_19.setText("")
        self.label.setText(QCoreApplication.translate("pyTrade_v2", u"Account Summary", None))
        self.label_2.setText(QCoreApplication.translate("pyTrade_v2", u"Open Market:", None))
        self.label_3.setText(QCoreApplication.translate("pyTrade_v2", u"Current Instrument:", None))
        self.label_5.setText(QCoreApplication.translate("pyTrade_v2", u"Open Positions", None))
        self.label_8.setText(QCoreApplication.translate("pyTrade_v2", u"Open Trades", None))
        self.lb_market.setText(QCoreApplication.translate("pyTrade_v2", u"..", None))
        self.lb_instr.setText(QCoreApplication.translate("pyTrade_v2", u"..", None))
        self.lb_openpos.setText(QCoreApplication.translate("pyTrade_v2", u"..", None))
        self.lb_opentrades.setText(QCoreApplication.translate("pyTrade_v2", u"..", None))
        self.label_4.setText(QCoreApplication.translate("pyTrade_v2", u"Account Balance:", None))
        self.label_12.setText(QCoreApplication.translate("pyTrade_v2", u"NAV:", None))
        self.label_7.setText(QCoreApplication.translate("pyTrade_v2", u"Unrealised P/L:", None))
        self.label_6.setText(QCoreApplication.translate("pyTrade_v2", u"Realised P/L:", None))
        self.lb_ac_balance.setText(QCoreApplication.translate("pyTrade_v2", u"..", None))
        self.lb_ac_NAV.setText(QCoreApplication.translate("pyTrade_v2", u"..", None))
        self.lb_ac_unrealPL.setText(QCoreApplication.translate("pyTrade_v2", u"..", None))
        self.lb_ac_realPL.setText(QCoreApplication.translate("pyTrade_v2", u"..", None))
        self.label_21.setText("")
        self.label_14.setText(QCoreApplication.translate("pyTrade_v2", u"Dashboard", None))
        self.label_15.setText(QCoreApplication.translate("pyTrade_v2", u"Open Positions", None))
        self.label_16.setText(QCoreApplication.translate("pyTrade_v2", u"Candles", None))
        self.label_17.setText(QCoreApplication.translate("pyTrade_v2", u"Output/Log", None))
        self.label_18.setText(QCoreApplication.translate("pyTrade_v2", u"Bot Settings", None))
        self.label_13.setText(QCoreApplication.translate("pyTrade_v2", u"pyTrade v0.2 Created by SimpleDesigns 2026", None))
    # retranslateUi

