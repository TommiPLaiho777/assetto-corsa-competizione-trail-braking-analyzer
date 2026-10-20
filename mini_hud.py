"""Detached, frameless alpha-layer Qt HUD with its own minimize/close buttons.

Does not poll telemetry or access ACC: it only receives finalized messages.
Users can move the text by dragging it. No full-window opaque rectangle.
"""
from __future__ import annotations

from PyQt5.QtCore import QEvent, QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (QApplication, QGraphicsDropShadowEffect, QHBoxLayout,
                             QLabel, QToolButton, QVBoxLayout, QWidget)

from hud_presentation import HUDMessage


class MiniHUD(QWidget):
    visibilityChanged = pyqtSignal()

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setObjectName('MiniHUD')
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowTitle('Advanced Trail Braking – Mini HUD')
        self.setMinimumSize(350, 155)
        self.resize(440, 165)
        self._drag_origin = None
        self._window_origin = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 1, 10, 8)
        root.setSpacing(0)
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addStretch(1)
        self.min_button = self._control('−', 'Minimize Mini HUD')
        self.close_button = self._control('×', 'Close Mini HUD (reopen from detailed window)')
        self.min_button.clicked.connect(self.showMinimized)
        self.close_button.clicked.connect(self.close)
        controls.addWidget(self.min_button)
        controls.addWidget(self.close_button)
        root.addLayout(controls)

        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(14)
        self.number = QLabel('–')
        self.number.setObjectName('MiniNumber')
        self.number.setFixedWidth(105)
        self.number.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.number.setFont(QFont('Segoe UI', 77, QFont.Black))
        self.feedback = QLabel('Waiting for completed corner')
        self.feedback.setObjectName('MiniFeedback')
        self.feedback.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.feedback.setWordWrap(True)
        self.feedback.setFont(QFont('Segoe UI', 16, QFont.DemiBold))
        line.addWidget(self.number)
        line.addWidget(self.feedback, stretch=1)
        root.addLayout(line, stretch=1)

        for item in (self.number, self.feedback):
            item.setStyleSheet('background: transparent; border: none;')
            shadow = QGraphicsDropShadowEffect(item)
            shadow.setBlurRadius(8)
            shadow.setOffset(2, 2)
            shadow.setColor(QColor(0, 0, 0, 245))
            item.setGraphicsEffect(shadow)
            item.installEventFilter(self)
        # All HUD content paints on Qt's transparent surface. Never use the
        # global app theme's opaque QWidget background on this top-level.
        self.setStyleSheet('''
            QWidget#MiniHUD { background: transparent; border: none; }
            QLabel { background: transparent; border: none; }
            QToolButton { background: transparent; border: none;
                color: rgba(233,240,246,205); font-size: 21px;
                font-weight: 700; padding: 0px; }
            QToolButton:hover { color: white; }
        ''')
        self.set_message(HUDMessage(None, 'Waiting for completed corner', '#BEC9D6', '#BEC9D6'))
        self._place_initially()

    @staticmethod
    def _control(symbol, tooltip):
        button = QToolButton()
        button.setText(symbol)
        button.setToolTip(tooltip)
        button.setFixedSize(29, 27)
        button.setAutoRaise(True)
        return button

    def _place_initially(self):
        from PyQt5.QtCore import QSettings
        stored = QSettings('AdvancedTrailBraking', 'RotationCoach').value('miniHudPos')
        if isinstance(stored, QPoint):
            self.move(stored)
        else:
            screen = QApplication.primaryScreen()
            if screen is not None:
                geo = screen.availableGeometry()
                self.move(geo.right() - self.width() - 32, geo.top() + 75)

    def set_message(self, msg: HUDMessage):
        self.number.setText(msg.number)
        self.number.setStyleSheet('background: transparent; border: none; color: ' + msg.number_color + ';')
        self.feedback.setText(msg.text)
        self.feedback.setStyleSheet('background: transparent; border: none; color: ' + msg.text_color + ';')

    def eventFilter(self, source, event):
        if source in (self.number, self.feedback):
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_origin = event.globalPos()
                self._window_origin = self.pos()
                return True
            if event.type() == QEvent.MouseMove and self._drag_origin is not None:
                self.move(self._window_origin + event.globalPos() - self._drag_origin)
                return True
            if event.type() == QEvent.MouseButtonRelease and self._drag_origin is not None:
                self._drag_origin = None
                self._window_origin = None
                from PyQt5.QtCore import QSettings
                QSettings('AdvancedTrailBraking', 'RotationCoach').setValue('miniHudPos', self.pos())
                return True
        return super().eventFilter(source, event)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.visibilityChanged.emit()

    def showEvent(self, event):
        super().showEvent(event)
        self.visibilityChanged.emit()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self.visibilityChanged.emit()
