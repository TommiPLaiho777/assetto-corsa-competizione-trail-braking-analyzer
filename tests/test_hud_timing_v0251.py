"""Pure HUD timing regression checks; safe on non-Windows CI."""
import ast
from pathlib import Path
import unittest
from hud_presentation import (POST_RELEASE_OBSERVATION_S, STEADY_STRAIGHT_S,
                              safe_straight)
from advanced_engine import TelemetrySample


class TestHudTiming(unittest.TestCase):
    def test_responds_a_little_faster_but_preserves_observation(self):
        self.assertAlmostEqual(POST_RELEASE_OBSERVATION_S, 2.6)
        self.assertAlmostEqual(STEADY_STRAIGHT_S, 0.24)
        self.assertGreaterEqual(POST_RELEASE_OBSERVATION_S, 1.2)
        self.assertGreater(STEADY_STRAIGHT_S, 0.0)

    def test_gate_still_rejects_cornering(self):
        s = TelemetrySample(1, 1, 90, .0, .4, .1, .19)
        self.assertFalse(safe_straight(s))
        s2 = TelemetrySample(1, 2, 90, .0, .4, .03, .04)
        self.assertTrue(safe_straight(s2))

    def test_main_uses_named_thresholds_for_both_paths(self):
        code = (Path(__file__).parent.parent / 'main.py').read_text('utf-8')
        ast.parse(code)
        self.assertIn('EventTracker(post_seconds=POST_RELEASE_OBSERVATION_S)', code)
        self.assertIn('sample.time - self._straight_since >= STEADY_STRAIGHT_S', code)
        self.assertIn('self._pending_hud = describe(coach)', code)
        self.assertNotIn('self.mini_hud.set_message(describe(coach))', code)

if __name__ == '__main__':
    unittest.main()
