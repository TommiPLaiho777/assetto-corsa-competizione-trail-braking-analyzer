"""Small alpha-preserving pedal overlap light embedded beside the Mini HUD."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QLabel


class PedalOverlapIndicator(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('MiniPedalOverlapLight')
        self.setFixedWidth(39)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont('Segoe UI Symbol', 31, QFont.Black))
        self.setToolTip('Pedal overlap: red = sustained gas+brake; green = clean brake-to-throttle')
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(10)
        glow.setColor(QColor(0, 0, 0, 220))
        glow.setOffset(1, 1)
        self.setGraphicsEffect(glow)
        self.set_light(None, False)

    def set_light(self, color: str | None, lit: bool = False):
        if color not in (None, 'red', 'green'):
            raise ValueError('Unsupported pedal light color')
        self.setText('●' if color and lit else '')
        foreground = '#FF465B' if color == 'red' else '#34F58A'
        # No rectangle, fill, outline or widget opacity; the top-level HUD's
        # WA_TranslucentBackground remains fully effective.
        self.setStyleSheet(f'background: transparent; border: none; color: {foreground};')
