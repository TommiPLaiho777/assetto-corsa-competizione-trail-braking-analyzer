"""Offline deterministic rapid-corner scheduling; no Qt/ACC required."""
import unittest
from hud_presentation import HUDMessage
from hud_rhythm import (HUDRhythm, PREVIEW_DELAY_S, NORMAL_HOLD_S,
                        FAST_HOLD_S, MAX_FROM_RELEASE_S)


def msg(score, words='Feedback'):
    return HUDMessage(score, words, '#fff', '#fff')


class HUDRhythmTests(unittest.TestCase):
    def test_short_delay_and_auto_expiry_on_straight(self):
        h=HUDRhythm()
        h.new_release(msg(3), at=10.0, braking_duration=2.0)
        self.assertEqual(h.tick(10.1).kind, 'none')
        self.assertEqual(h.tick(10.2).kind, 'show')
        self.assertEqual(h.tick(11.2).kind, 'none')
        self.assertEqual(h.tick(11.57).kind, 'clear')
        self.assertEqual(h.tick(17.0).kind, 'none')
        self.assertLess(NORMAL_HOLD_S+PREVIEW_DELAY_S, 2.0)

    def test_rapid_releases_shorter_lifetime(self):
        h=HUDRhythm()
        h.new_release(msg(3), at=10.0, braking_duration=2.0)
        h.tick(10.2)
        self.assertEqual(h.tick(10.6, braking_active=True).kind, 'clear')
        h.new_release(msg(4), at=12.6, braking_duration=1.9)
        self.assertEqual(h.tick(12.8).kind, 'show')
        self.assertEqual(h.tick(13.8).kind, 'clear')
        self.assertLess(FAST_HOLD_S, NORMAL_HOLD_S)

    def test_next_braking_suppresses_old_notice(self):
        h=HUDRhythm()
        h.new_release(msg(4), at=0)
        h.tick(0.2)
        self.assertEqual(h.tick(.45, braking_active=True).kind, 'clear')
        self.assertEqual(h.revise(msg(5), 1.5).kind, 'none')
        self.assertEqual(h.tick(2.0).kind, 'none')

    def test_expired_message_is_not_resurrected_by_final(self):
        h=HUDRhythm()
        h.new_release(msg(3), at=0.0)
        h.tick(.20)
        self.assertEqual(h.tick(1.6).kind, 'clear')
        self.assertEqual(h.revise(msg(5, 'Final'), at=2.6).kind, 'none')
        self.assertEqual(h.tick(2.65).kind, 'none')

    def test_early_revision_in_place_without_second_popup(self):
        h=HUDRhythm()
        h.new_release(msg(4, 'Exit under review'), at=100.0)
        self.assertEqual(h.tick(100.2).kind, 'show')
        update=h.revise(msg(5, 'Early exit looks good'), at=101.25)
        self.assertEqual(update.kind, 'show')
        self.assertEqual(update.message.grade, 5)
        # Small grace window, bounded by an absolute post-release cap.
        self.assertEqual(h.tick(101.6).kind, 'none')
        self.assertEqual(h.tick(102.0).kind, 'clear')
        self.assertLess(MAX_FROM_RELEASE_S, 2.0)

    def test_revise_pending_replaces_same_card(self):
        h=HUDRhythm()
        h.new_release(msg(3), at=40.0)
        self.assertEqual(h.revise(msg(4), 40.08).kind, 'none')
        out=h.tick(40.18)
        self.assertEqual(out.kind,'show')
        self.assertEqual(out.message.grade,4)

    def test_idle_without_event_never_shows_placeholder(self):
        h=HUDRhythm()
        self.assertEqual(h.tick(1000000).kind, 'none')
        self.assertEqual(h.reset().kind, 'none')

    def test_timer_uses_time_values_not_real_sleep(self):
        h=HUDRhythm()
        h.new_release(msg(3), at=1.0)
        self.assertEqual(h.tick(1.0+PREVIEW_DELAY_S+.01).kind, 'show')
        self.assertEqual(h.reset().kind, 'clear')


if __name__=='__main__': unittest.main()
