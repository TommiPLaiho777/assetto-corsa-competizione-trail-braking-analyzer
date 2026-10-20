"""Make pytest-style legacy tests available through standard unittest preflight."""
import unittest
from tests import test_advanced_engine as t


class ExistingAdvancedScoringTests(unittest.TestCase):
    def test_straight_not_grading(self): t.test_straight_not_grading()
    def test_late_brake_overlap_worse(self): t.test_late_brake_overlap_worse_than_controlled_release()
    def test_coast_reduces_grade(self): t.test_coast_reduces_grade()
    def test_early_release_not_automatic_failure(self): t.test_early_release_is_not_automatically_failure()
    def test_short_event(self): t.test_short_event_skipped()
    def test_nan_yaw_rejected(self): t.test_missing_yaw_refuses_to_grade()
    def test_two_stage_feedback(self): t.test_state_machine_two_stage_feedback()
    def test_reader_offsets(self): t.test_reader_offsets()
    def test_bad_reader_packets(self): t.test_reader_rejects_short_and_bad()
    def test_provisional_exit_not_proven(self): t.test_provisional_grade_cannot_claim_proven_exit()
