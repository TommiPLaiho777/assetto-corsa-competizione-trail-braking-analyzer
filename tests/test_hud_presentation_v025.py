"""Pure offline tests: no ACC, Qt or Windows calls."""
import unittest
from types import SimpleNamespace
from advanced_engine import TelemetrySample
from hud_presentation import SCORE_COLORS, describe, safe_straight


def coach(score, label, evidence=None):
    return SimpleNamespace(score=score, label=label, evidence=evidence or {})


def sample(speed=120, brake=0, steer=.01, yaw=.02):
    return TelemetrySample(0, 1, speed, brake, 0.3, steer, yaw)


class HudPresentationTests(unittest.TestCase):
    def test_score_colors_are_distinct(self):
        self.assertEqual(len(set(SCORE_COLORS.values())), 6)
        self.assertEqual(SCORE_COLORS[5], '#3EFF8F')
        self.assertTrue(SCORE_COLORS[1].startswith('#FF'))

    def test_success(self):
        m = describe(coach(5, 'CONTROLLED TRAIL + EXIT OBSERVED'))
        self.assertEqual(m.number, '5')
        self.assertIn('trail', m.text.lower())
        self.assertEqual(m.text_color, SCORE_COLORS[5])

    def test_no_unverified_apex_claim(self):
        for label in ('TRAIL TO REVIEW', 'COASTING TO REVIEW',
                      'STRAIGHT BRAKING / NO TRAIL', 'CONTROLLED TRAIL / EXIT NOT PROVEN'):
            self.assertNotIn('apex', describe(coach(3, label)).text.lower())

    def test_coasting_red_if_extreme(self):
        m=describe(coach(1,'COASTING TO REVIEW',{'coasting_after_release_s':2.1}))
        self.assertEqual(m.text_color, '#FF5265')
        self.assertIn('pedals', m.text)

    def test_straight_no_score(self):
        m=describe(coach(None,'STRAIGHT BRAKING / NO TRAIL'))
        self.assertEqual(m.number,'–')
        self.assertIn('no trail',m.text.lower())

    def test_unknown(self):
        m=describe(coach(4,'SOMETHING NEW'))
        self.assertIn('Review',m.text)

    def test_safe_straight(self):
        self.assertTrue(safe_straight(sample()))
        self.assertFalse(safe_straight(sample(steer=.15)))
        self.assertFalse(safe_straight(sample(yaw=.18)))
        self.assertFalse(safe_straight(sample(brake=.15)))
        self.assertFalse(safe_straight(sample(speed=15)))

    def test_explanation_independent_of_numeric_grade(self):
        m=describe(coach(3,'ROTATION UNSTABLE / CHECK'))
        self.assertEqual(m.number_color,SCORE_COLORS[3])
        self.assertEqual(m.text_color,'#FF5265')


if __name__=='__main__':
    unittest.main()
