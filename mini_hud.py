"""Detached, frameless alpha-layer Qt HUD with its own minimize/close buttons.

Does not poll telemetry or access ACC: it only receives finalized messages.
Users can drag the text or a persistent small grip after the short feedback clears.
The numeral/feedback remain fully unboxed on the transparent alpha window.
"""
from __future__ import annotations

from PyQt5.QtCore import QEvent, QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (QApplication, QGraphicsDropShadowEffect, QHBoxLayout,
                             QLabel, QToolButton, QVBoxLayout, QWidget)

from hud_presentation import HUDMessage
from overlap_indicator import PedalOverlapIndicator


class MiniHUD(QWidget):
    visibilityChanged = pyqtSignal()

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setObjectName('MiniHUD')
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowTitle('Advanced Trail Braking – Mini HUD')
        self.setMinimumSize(388, 155)
        self.resize(490, 165)
        self._drag_origin = None
        self._window_origin = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 1, 10, 8)
        root.setSpacing(0)
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        # Windows may treat fully transparent blank pixels as mouse-transparent.
        # The brief feedback disappears between corners, so give the user a
        # small *permanently hit-testable* grip for moving the HUD while idle.
        self.drag_handle = self._control('≡', 'Drag Mini HUD from here')
        self.drag_handle.setObjectName('MiniDragHandle')
        self.drag_handle.setFixedSize(36, 30)
        self.drag_handle.setCursor(Qt.OpenHandCursor)
        controls.addWidget(self.drag_handle)
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
        self.corner_name = QLabel('')
        self.corner_name.setObjectName('MiniCornerName')
        self.corner_name.setFont(QFont('Segoe UI', 13, QFont.DemiBold))
        self.corner_name.setStyleSheet('background: transparent; border: none; color: #E5F0F8;')
        self.corner_name.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.corner_name.setVisible(False)
        right = QVBoxLayout()
        right.setSpacing(0)
        right.setContentsMargins(0, 0, 0, 0)
        right.addWidget(self.corner_name)
        right.addWidget(self.feedback, stretch=1)
        line.addWidget(self.number)
        line.addLayout(right, stretch=1)
        # Pedal overlap light lives on THIS alpha-enabled window, not an
        # independent opaque window or a second ACC connection.
        self.overlap_indicator = PedalOverlapIndicator()
        line.addWidget(self.overlap_indicator)
        root.addLayout(line, stretch=1)

        for item in (self.number, self.feedback, self.corner_name):
            item.setStyleSheet('background: transparent; border: none;')
            shadow = QGraphicsDropShadowEffect(item)
            shadow.setBlurRadius(8)
            shadow.setOffset(2, 2)
            shadow.setColor(QColor(0, 0, 0, 245))
            item.setGraphicsEffect(shadow)
            item.installEventFilter(self)
        # Install the grip filter LAST. Qt can synchronously deliver events
        # while constructing a widget; eventFilter needs all these
        # attributes to exist before inspecting mouse events.
        self.drag_handle.installEventFilter(self)
        self.overlap_indicator.installEventFilter(self)
        # All HUD content paints on Qt's transparent surface. Never use the
        # global app theme's opaque QWidget background on this top-level.
        self.setStyleSheet('''
            QWidget#MiniHUD { background: transparent; border: none; }
            QLabel { background: transparent; border: none; }
            QToolButton { background: transparent; border: none;
                color: rgba(233,240,246,205); font-size: 21px;
                font-weight: 700; padding: 0px; }
            QToolButton:hover { color: white; }
            QToolButton#MiniDragHandle {
                background: rgba(28, 43, 58, 205);
                border: none;
                border-radius: 7px;
                color: rgba(233, 240, 246, 220);
                font-size: 23px;
            }
            QToolButton#MiniDragHandle:hover {
                background: rgba(45, 65, 83, 235);
                color: white;
            }
        ''')
        # Preserve the user's proven white, slightly larger corner-name style.
        self.corner_name.setFont(QFont('Segoe UI', 16, QFont.Bold))
        self.corner_name.setStyleSheet('background: transparent; border: none; color: #FFFFFF;')
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
        self.corner_name.setText(msg.corner_name.upper() if msg.corner_name else '')
        self.corner_name.setVisible(bool(msg.corner_name))
        self.number.setText(msg.number)
        self.number.setStyleSheet('background: transparent; border: none; color: ' + msg.number_color + ';')
        self.feedback.setText(msg.text)
        self.feedback.setStyleSheet('background: transparent; border: none; color: ' + msg.text_color + ';')

    def set_pedal_light(self, color=None, lit=False):
        """Pure UI update. Never changes the existing quick grading message."""
        self.overlap_indicator.set_light(color, lit)

    def clear_message(self):
        """Keep the HUD window draggable/closable, but clear idle feedback."""
        self.number.clear()
        self.feedback.clear()
        self.corner_name.clear()
        self.corner_name.setVisible(False)

    def eventFilter(self, source, event):
        # The grip is reachable even when the text has expired. Dragging the
        # numeral/diagnosis still works whenever Windows hit-tests those pixels.
        if source in (getattr(self, 'number', None),
                      getattr(self, 'feedback', None),
                      getattr(self, 'corner_name', None),
                      getattr(self, 'drag_handle', None),
                      getattr(self, 'overlap_indicator', None)):
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_origin = event.globalPos()
                self._window_origin = self.pos()
                if source is self.drag_handle:
                    self.drag_handle.setCursor(Qt.ClosedHandCursor)
                return True
            if event.type() == QEvent.MouseMove and self._drag_origin is not None:
                self.move(self._window_origin + event.globalPos() - self._drag_origin)
                return True
            if event.type() == QEvent.MouseButtonRelease and self._drag_origin is not None:
                self._drag_origin = None
                self._window_origin = None
                if source is self.drag_handle:
                    self.drag_handle.setCursor(Qt.OpenHandCursor)
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
