"""Mini HUD grab-handle regression; no game access or real display needed."""
import os
import unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PyQt5.QtCore import Qt, QEvent, QPoint, QPointF
    from PyQt5.QtGui import QMouseEvent
    from PyQt5.QtWidgets import QApplication
    from mini_hud import MiniHUD
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'PyQt5 unavailable in this environment')
class PersistentGrabHandleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['test', '-platform', 'offscreen'])

    def test_grab_handle_survives_message_expiry(self):
        w = MiniHUD()
        try:
            w.show()
            self.app.processEvents()
            w.clear_message()
            self.assertTrue(w.drag_handle.isVisible())
            self.assertTrue(w.drag_handle.isEnabled())
            self.assertEqual(w.number.text(), '')
            self.assertEqual(w.feedback.text(), '')
            self.assertEqual(w.min_button.text(), '−')
            self.assertEqual(w.close_button.text(), '×')
        finally:
            w.close()

    def test_grip_moves_idle_window(self):
        w = MiniHUD()
        try:
            w.show()
            self.app.processEvents()
            w.clear_message()
            grip = w.drag_handle
            start = w.pos()
            pos = QPointF(8, 8)
            first = QPointF(grip.mapToGlobal(QPoint(8, 8)))
            second = first + QPointF(42, 25)
            self.app.sendEvent(grip, QMouseEvent(QEvent.MouseButtonPress, pos, first, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
            self.app.sendEvent(grip, QMouseEvent(QEvent.MouseMove, pos, second, Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
            self.assertEqual(w.pos(), start + QPoint(42, 25))
            self.app.sendEvent(grip, QMouseEvent(QEvent.MouseButtonRelease, pos, second, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
            self.assertIsNone(w._drag_origin)
        finally:
            w.close()


if __name__ == '__main__':
    unittest.main()
