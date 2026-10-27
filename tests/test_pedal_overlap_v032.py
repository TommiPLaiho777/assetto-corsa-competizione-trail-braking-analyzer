"""Pedal light integration regressions: no ACC, Windows or Qt needed."""
import math
import unittest
from pathlib import Path
from pedal_overlap import PedalOverlapMonitor


class PedalOverlapLogicTests(unittest.TestCase):
    @staticmethod
    def drive(m, points):
        return [m.update(g,b,t) for g,b,t in points]

    def test_clean_transition_flashes_green_and_expires(self):
        m = PedalOverlapMonitor()
        seq = [(0,0.7,1.0),(0,0.4,1.1),(0,0.02,1.2),(.5,.0,1.3)]
        result = self.drive(m,seq)[-1]
        self.assertTrue(result.completed.success)
        self.assertEqual(result.color,'green')
        self.assertTrue(result.lit)
        self.assertIsNone(m.update(.6,0,2.2).color)

    def test_sustained_pedals_are_red_and_record_duration(self):
        m = PedalOverlapMonitor()
        seq = [(.7,.8,1.0),(.7,.8,1.1),(.6,.7,1.2),(.4,.4,1.3),(.1,.02,1.4),(.5,0,1.5)]
        r = self.drive(m, seq)
        self.assertEqual(r[3].color,'red')
        self.assertFalse(r[-1].completed.success)
        self.assertGreaterEqual(r[-1].completed.duration_sec,.3)
        self.assertEqual(r[-1].color,'red')

    def test_subthreshold_overlap_does_not_fail(self):
        m=PedalOverlapMonitor()
        self.drive(m,[(.5,.5,1.0),(.5,.5,1.08),(0,.5,1.12)])
        x=m.update(.4,0,1.30)
        self.assertTrue(x.completed.success)
        self.assertEqual(x.color,'green')

    def test_short_blip_does_not_flash_red(self):
        m=PedalOverlapMonitor()
        a = m.update(.8,.8,1)
        b = m.update(0,.7,1.04)
        self.assertIsNone(a.color)
        self.assertIsNone(b.color)

    def test_idle_throttle_without_braking_no_green(self):
        m=PedalOverlapMonitor()
        for i in range(30):
            x=m.update(0.8,0,1+i*.04)
            self.assertIsNone(x.color)
            self.assertIsNone(x.completed)

    def test_valid_zero_inputs_no_spurious_flash(self):
        m=PedalOverlapMonitor()
        for i in range(25):
            self.assertIsNone(m.update(0,0,1+i*.04).color)

    def test_missing_frames_fail_closed(self):
        m=PedalOverlapMonitor()
        m.update(.6,.7,1)
        m.update(.6,.7,1.2)
        x=m.update(.7,0,2.5)
        self.assertIsNone(x.completed)
        self.assertIsNone(x.color)

    def test_nonfinite_fail_closed(self):
        m=PedalOverlapMonitor()
        m.update(.7,.8,1)
        bad=m.update(float('nan'),.8,1.1)
        self.assertEqual(bad.color,None)
        self.assertIsNone(bad.completed)

    def test_optional_gear_filter_from_original_tool(self):
        m=PedalOverlapMonitor()
        m.update(0,.7,1.0,gear=3)
        m.update(.8,.7,1.1,gear=2)
        m.update(.8,.7,1.3,gear=2)
        m.update(0,.7,1.5,gear=2)
        x=m.update(.4,0,1.75,gear=2)
        self.assertTrue(x.completed.success)
        self.assertEqual(x.color,'green')

    def test_next_braking_clears_previous_green(self):
        m=PedalOverlapMonitor()
        m.update(0,.7,1.0)
        m.update(.8,0,1.1)
        x=m.update(0,.7,1.2)
        self.assertIsNone(x.color)

    def test_read_only_core_is_unmodified(self):
        source=Path(__file__).parents[1]
        for file in ('pedal_overlap.py','overlap_indicator.py'):
            text=(source/file).read_text(encoding='utf-8')
            self.assertNotIn('mmap(',text)
            self.assertNotIn('CreateFileMapping',text)
            self.assertNotIn('MapViewOfFile',text)


try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    from mini_hud import MiniHUD
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT,'Qt not installed (Windows live UI smoke required)')
class PedalLightAlphaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        cls.app=QApplication.instance() or QApplication(['test','-platform','offscreen'])

    def test_alpha_never_removed_when_pulsing(self):
        hud=MiniHUD()
        try:
            self.assertTrue(hud.testAttribute(Qt.WA_TranslucentBackground))
            hud.set_pedal_light('red',True)
            self.assertEqual(hud.overlap_indicator.text(),'●')
            self.assertIn('background: transparent',hud.overlap_indicator.styleSheet())
            hud.set_pedal_light('green',True)
            self.assertEqual(hud.overlap_indicator.text(),'●')
            hud.clear_message()
            self.assertEqual(hud.overlap_indicator.text(),'●')
            self.assertTrue(hud.testAttribute(Qt.WA_TranslucentBackground))
            hud.set_pedal_light(None,False)
            self.assertEqual(hud.overlap_indicator.text(),'')
            self.assertEqual(hud.corner_name.font().pointSize(),16)
        finally:
            hud.close()

if __name__ == '__main__': unittest.main()
