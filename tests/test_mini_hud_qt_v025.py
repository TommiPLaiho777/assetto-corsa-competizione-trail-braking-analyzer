"""Offscreen smoke check for transparent/window behavior; safely skip if Qt missing."""
import os
import unittest

# Don't create native windows or connect to ACC in CI.
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    from mini_hud import MiniHUD
    HAS_QT=True
except ImportError:
    HAS_QT=False


@unittest.skipUnless(HAS_QT, 'PyQt5 not available')
class MiniHudQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication(['test', '-platform', 'offscreen'])

    def test_alpha_layer_frameless_and_always_on_top(self):
        w=MiniHUD()
        try:
            self.assertTrue(bool(w.testAttribute(Qt.WA_TranslucentBackground)))
            self.assertTrue(bool(w.windowFlags() & Qt.FramelessWindowHint))
            self.assertTrue(bool(w.windowFlags() & Qt.WindowStaysOnTopHint))
            self.assertEqual(w.min_button.text(), '−')
            self.assertEqual(w.close_button.text(), '×')
        finally:
            w.close()

    def test_auto_expiry_clears_only_text_not_close_controls(self):
        from hud_presentation import HUDMessage
        w=MiniHUD()
        try:
            w.set_message(HUDMessage(4, 'Review', '#fff', '#fff'))
            w.clear_message()
            self.assertEqual(w.number.text(), '')
            self.assertEqual(w.feedback.text(), '')
            self.assertEqual(w.min_button.text(), '−')
            self.assertEqual(w.close_button.text(), '×')
        finally:
            w.close()

    def test_minimize_and_close_independent(self):
        w=MiniHUD()
        try:
            w.show()
            self.app.processEvents()
            w.min_button.click()
            self.app.processEvents()
            self.assertTrue(w.isMinimized())
            w.showNormal()
            self.app.processEvents()
            w.close_button.click()
            self.app.processEvents()
            self.assertFalse(w.isVisible())
        finally:
            w.close()


if __name__=='__main__':
    unittest.main()
