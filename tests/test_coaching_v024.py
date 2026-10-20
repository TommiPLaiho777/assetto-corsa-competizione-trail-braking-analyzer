"""Regression tests for read-only 0.2.4 rotation coaching; no ACC necessary."""
import hashlib
import sys
import unittest
from dataclasses import replace
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from advanced_engine import EventTracker, analyze
from coaching_engine import assess, COACH_VERSION
from tests.test_advanced_engine import make_event


def extended(kind='clean',coast=False):
    seq,n=make_event(kind,coast)
    # Extend to ~3.5 seconds after release for the Nürburgring exit review.
    for i in range(60,190):
        s=seq[-1]
        seq.append(replace(s,time=i*.02 + n*.02,packet=s.packet+1,
                           speed_kph=s.speed_kph + (0 if coast else .3),
                           throttle=0. if coast else .4))
    return seq,n


class CoachingV024Tests(unittest.TestCase):
    def test_good_release_and_exit_has_evidence_for_five(self):
        s,n=extended()
        x=assess(s,n,'final',analyze(s,n))
        self.assertEqual(x.score,5,x)
        self.assertTrue(x.evidence['exit_verified'])
        self.assertTrue(x.evidence['controlled_taper'])
        self.assertEqual(x.as_log()['algorithm'],COACH_VERSION)
        import json
        self.assertIsInstance(json.dumps(x.as_log()),str)

    def test_initial_pedal_ramp_not_counted_as_reapplications(self):
        s,n=extended()
        result=assess(s,n,'final')
        self.assertEqual(result.evidence['brake_reapplications'],0)

    def test_actual_reapplication_after_peak_detected(self):
        s,n=extended()
        peak=max(range(n),key=lambda i:s[i].brake)
        # Add a new rise AFTER peak; do not alter the global maximum.
        j=next(i for i in range(peak+4,n-2) if .1<s[i].brake<.55)
        raised=min(s[peak].brake-.01,s[j-1].brake+.11)
        s[j]=replace(s[j],brake=raised)
        result=assess(s,n,'final')
        self.assertGreaterEqual(result.evidence['brake_reapplications'],1)

    def test_immediate_is_instant_but_never_claims_exit(self):
        s,n=extended()
        immediate=assess(s[:n],n,'provisional')
        self.assertIsNotNone(immediate.score)
        self.assertLessEqual(immediate.score,4)
        self.assertFalse(immediate.evidence['exit_verified'])

    def test_unobserved_exit_cannot_get_five(self):
        s,n=make_event()
        x=assess(s,n,'final')
        self.assertLessEqual(x.score,4)

    def test_coast_detected_over_three_seconds_and_penalized(self):
        s,n=extended(coast=True)
        x=assess(s,n,'final')
        self.assertGreater(x.evidence['coasting_after_release_s'],2.0)
        self.assertLessEqual(x.score,2)
        self.assertEqual(x.label,'COASTING TO REVIEW')

    def test_too_late_brake_high_overlap_lower_than_good(self):
        good,ng=extended()
        bad,nb=extended('late')
        a=assess(good,ng,'final'); b=assess(bad,nb,'final')
        self.assertGreater(b.evidence['heavy_brake_turn_s'],a.evidence['heavy_brake_turn_s'])
        self.assertLess(b.score,a.score)

    def test_straight_brake_not_failure(self):
        s,n=extended('straight')
        x=assess(s,n,'final')
        self.assertIsNone(x.score)
        self.assertIn('STRAIGHT',x.label)
        self.assertEqual(x.confidence,'not_applicable')

    def test_brake_before_turn_not_failure(self):
        s,n=extended('early')
        x=assess(s,n,'final')
        self.assertIsNone(x.score)
        self.assertIn('NO MEASURED TRAIL',x.label)

    def test_unstable_yaw_caps_grade(self):
        s,n=extended()
        s=[replace(frame,yaw_rate=-frame.yaw_rate if 48<=i<=75 else frame.yaw_rate)
           for i,frame in enumerate(s)]
        x=assess(s,n,'final')
        self.assertLessEqual(x.score,2)

    def test_spin_not_awarded_good_grade(self):
        s,n=extended()
        s=[replace(frame,yaw_rate=1.65 if 45<=i<=95 else frame.yaw_rate)
           for i,frame in enumerate(s)]
        x=assess(s,n,'final')
        self.assertLessEqual(x.score,2)

    def test_incident_like_stop_is_excluded_without_damage_claim(self):
        s,n=extended()
        s[-1]=replace(s[-1],speed_kph=0.)
        x=assess(s,n,'final')
        self.assertIsNone(x.score)
        self.assertIn('EXCLUDED',x.label)
        self.assertNotIn('definite',x.explanation.lower())

    def test_invalid_timestamps_rejected(self):
        s,n=extended()
        s[10]=replace(s[10],time=s[9].time)
        x=assess(s,n,'final')
        self.assertIsNone(x.score)
        self.assertEqual(x.label,'UNRELIABLE TELEMETRY')

    def test_yaw_growth_without_brake_taper_doesnt_get_five(self):
        s,n=extended()
        s=[replace(frame,brake=.40) if i<n and .1<frame.brake<.9 else frame
           for i,frame in enumerate(s)]
        x=assess(s,n,'final')
        self.assertLessEqual(x.score,4)

    def test_tracker_delays_final_not_immediate(self):
        s,n=extended()
        tracker=EventTracker(post_seconds=3.)
        event_phases=[]
        for v in s:
            for z in tracker.update(v): event_phases.append((z.phase,v.time))
        prov=[x for x in event_phases if x[0]=='provisional']
        finals=[x for x in event_phases if x[0]=='final']
        self.assertEqual(len(prov),1)
        self.assertEqual(len(finals),1)
        self.assertGreaterEqual(finals[0][1]-prov[0][1],3.)

    def test_older_history_remains_unmodified_by_assessor(self):
        s,n=extended()
        old=analyze(s,n).as_log().copy()
        raw=dict(old)
        newer=assess(s,n,'final')
        self.assertEqual(old,raw)
        self.assertIn('score',newer.as_log())

    def test_scoring_contains_no_shared_memory_calls(self):
        code=(ROOT/'coaching_engine.py').read_text()
        for key in ('mmap.mmap(', 'CreateFileMappingW(', 'OpenFileMappingW(', 'MapViewOfFile('):
            self.assertNotIn(key,code)

    def test_acc_reader_byte_identical_to_v023(self):
        # SHA256 of shipped 0.2.3 reader, deliberately unchanged in 0.2.4.
        actual=hashlib.sha256((ROOT/'acc_memory.py').read_bytes()).hexdigest()
        self.assertEqual(actual, '6b4034c0732b735b84198691d669fcf5b7d1a97d2d76ee7c87b68ef306981927')

if __name__=='__main__': unittest.main()

class RawTraceTests(unittest.TestCase):
    def test_replay_preserves_grade_for_full_event(self):
        from raw_event_store import encode_event,decode_event
        import json
        s,n=extended()
        trace=encode_event('test-event',s,n)
        restored,ni=decode_event(json.loads(json.dumps(trace)))
        self.assertEqual(ni,n)
        self.assertEqual(assess(restored,ni,'final').score,assess(s,n,'final').score)

    def test_invalid_trace_rejected(self):
        from raw_event_store import decode_event
        with self.assertRaises(ValueError):decode_event({'schema':1,'fields':[],'samples':[[1,2]]})
