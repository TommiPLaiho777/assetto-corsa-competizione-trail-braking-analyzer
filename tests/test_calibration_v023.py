"""0.2.3 calibration regression tests – all OFFLINE, no UI or ACC needed."""
import json
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from advanced_engine import analyze, EventTracker
from calibration_engine import calibrate_live, calibrate_metrics, extra_from_samples, CALIBRATION_VERSION
from calibration_report import compare_rows, produce
from tests.test_advanced_engine import make_event


class CalibrationV023Tests(unittest.TestCase):
    def test_clean_event_can_get_five_only_with_raw_evidence(self):
        samples, n = make_event('clean')
        original = analyze(samples,n)
        self.assertEqual(calibrate_metrics(original.as_log()).score,4)
        improved = calibrate_live(original,samples,n)
        self.assertEqual(improved.score,5)
        self.assertEqual(improved.confidence,'moderate')
        self.assertGreaterEqual(improved.evidence['taper_during_turn_pct'],10)

    def test_late_overlap_not_high_grading(self):
        samples,n = make_event('late')
        original = analyze(samples,n)
        improved = calibrate_live(original,samples,n)
        self.assertLessEqual(improved.score,3)
        self.assertGreater(improved.evidence['brake_steer_overlap_pct'],20)

    def test_no_grade_for_straight(self):
        samples,n = make_event('straight')
        improved = calibrate_live(analyze(samples,n),samples,n)
        self.assertIsNone(improved.score)
        self.assertEqual(improved.confidence,'not_applicable')

    def test_braking_before_turn_not_bad_trail(self):
        samples,n=make_event('early')
        improved=calibrate_live(analyze(samples,n),samples,n)
        self.assertIsNone(improved.score)
        self.assertEqual(improved.label,'ENTRY BRAKE / NO MEASURED TRAIL')

    def test_missing_exit_no_high_grade(self):
        samples,n=make_event('clean')
        samples=[replace(s,throttle=0.0) for s in samples]
        improved=calibrate_live(analyze(samples,n),samples,n)
        self.assertLessEqual(improved.score,3)

    def test_full_coasting_reduces_grade(self):
        samples,n=make_event('clean',coast=True)
        improved=calibrate_live(analyze(samples,n),samples,n)
        self.assertLessEqual(improved.score,3)

    def test_multiple_reapplications_reduce_grade(self):
        samples,n=make_event('clean')
        old=analyze(samples,n).as_log()
        old['metrics']['brake_reapplications']=3
        improved=calibrate_metrics(old)
        self.assertLessEqual(improved.score,3)

    def test_unsupported_historical_five_refused(self):
        samples,n=make_event('clean')
        row=analyze(samples,n).as_log()
        self.assertEqual(row['score'],5)
        shadow=calibrate_metrics(row)
        self.assertLessEqual(shadow.score,4)
        self.assertEqual(shadow.confidence,'limited')
        self.assertEqual(row['score'],5)

    def test_shadow_retains_legacy_grade(self):
        samples,n=make_event('clean')
        old=analyze(samples,n)
        shadow=calibrate_live(old,samples,n)
        log=old.as_log()
        log['calibration']=shadow.as_log()
        self.assertEqual(log['score'],old.score)
        self.assertEqual(log['calibration']['algorithm'],CALIBRATION_VERSION)

    def test_completion_samples_are_available_without_changing_feedback(self):
        samples,n=make_event('clean')
        tracker=EventTracker(post_seconds=1.2)
        received=[]
        last_event=None
        for s in samples:
            updates=tracker.update(s)
            received.extend(updates)
            if any(u.phase=='final' for u in updates):
                last_event=tracker.last_completed_event
        self.assertIsNotNone(last_event)
        event,idx=last_event
        self.assertEqual(len(event),n+60)
        self.assertGreaterEqual(idx, n-3)
        self.assertLessEqual(idx, n+2) # release threshold may be met in final brake frames
        self.assertTrue(any(u.phase=='provisional' for u in received))
        self.assertTrue(any(u.phase=='final' for u in received))

    def test_incomplete_raw_samples_limited_evidence(self):
        samples,n=make_event('clean')
        samples=samples[:n+1]
        extra=extra_from_samples(samples,n)
        self.assertIn('taper_during_turn_pct',extra)
        shadow=calibrate_live(analyze(samples,n),samples,n)
        self.assertLessEqual(shadow.score,3)

    def test_archive_comparison_does_not_overwrite_input(self):
        samples,n=make_event('clean')
        original=analyze(samples,n).as_log()
        original['timestamp']='demo-timestamp'
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'source.jsonl'
            src.write_text(json.dumps(original)+'\n',encoding='utf-8')
            content=src.read_bytes()
            out=Path(td)/'output'
            items=produce(src,out)
            self.assertEqual(len(items),1)
            self.assertEqual(src.read_bytes(),content)
            self.assertTrue((out/'comparison.csv').is_file())
            self.assertTrue((out/'summary.md').is_file())
            self.assertEqual(items[0]['original_v022'],5)
            self.assertEqual(items[0]['shadow_v023'],4)

    def test_no_acc_memory_access_in_calibrator(self):
        source=(ROOT/'calibration_engine.py').read_text(encoding='utf8')
        self.assertNotIn('OpenFileMapping',source)
        self.assertNotIn('MapViewOfFile',source)
        self.assertNotIn('mmap.',source)
        self.assertNotIn('CreateFileMapping',source)

if __name__ == '__main__':
    unittest.main()
