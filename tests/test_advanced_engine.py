"""Synthetic offline regression tests, no ACC or PyQt required."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from acc_memory import ACCSharedMemory
from advanced_engine import EventTracker, TelemetrySample, analyze


def make_event(kind="clean", coast=False):
    seq = []
    dt = .02
    for i in range(110):
        p = i / 109
        b = (min(.98, .5 + p * 2.5) if p < .25 else max(.0, .98 * (1 - (p-.25)/.75)))
        if kind == "late":
            b = 1. if p < .78 else max(0., (1 - p)/.22)
        if kind == "straight":
            steer = 0.
            yaw = 0.
        elif kind == "early":
            steer = .0 if p < .95 else .02
            yaw = .0
        else:
            steer = min(.26, max(0., (p - .12) * .38))
            yaw = max(0., (p - .15)) * .30
        seq.append(TelemetrySample(i*dt, i+1, 180 - 75*p, b, 0., steer, yaw))
    release_index = len(seq)
    for k in range(60):
        p = k / 59
        st = .26 if kind != "straight" else 0.
        yw = .20 if kind != "straight" else 0.
        if kind == "early":
            st, yw = .22, .15
        throttle = .0 if coast else .40
        seq.append(TelemetrySample((110+k)*dt, 111+k, 105 + 15*p, 0., throttle, st, yw))
    return seq, release_index


def test_straight_not_grading():
    s, n = make_event("straight")
    r = analyze(s, n)
    assert r.score is None and r.label == "STRAIGHT BRAKING"


def test_late_brake_overlap_worse_than_controlled_release():
    s1, n1 = make_event("clean")
    s2, n2 = make_event("late")
    a = analyze(s1, n1)
    b = analyze(s2, n2)
    assert a.score is not None and b.score is not None
    assert a.metrics["brake_steer_overlap_pct"] < b.metrics["brake_steer_overlap_pct"]
    assert a.score >= b.score, (a, b)


def test_coast_reduces_grade():
    clean, n = make_event("clean", coast=False)
    coast, _ = make_event("clean", coast=True)
    a = analyze(clean, n)
    b = analyze(coast, n)
    assert b.label == "COASTING AFTER RELEASE"
    assert b.metrics["coast_after_release_s"] > .8
    assert b.score <= a.score


def test_early_release_is_not_automatically_failure():
    s, n = make_event("early")
    r = analyze(s, n)
    assert r.label == "BRAKE BEFORE TURN"
    assert 1 <= r.score <= 5


def test_short_event_skipped():
    s, n = make_event("clean")
    r = analyze(s[:4], 4)
    assert r.score is None


def test_missing_yaw_refuses_to_grade():
    s, n = make_event("clean")
    from dataclasses import replace
    s[70] = replace(s[70], yaw_rate=float("nan"))
    r = analyze(s, n)
    assert r.score is None and r.label == "YAW DATA MISSING"


def test_state_machine_two_stage_feedback():
    tracker = EventTracker(post_seconds=1.2)
    s, n = make_event("clean")
    result = []
    for frame in s:
        result.extend(tracker.update(frame))
    assert any(r.phase == "provisional" for r in result), result
    assert any(r.phase == "final" for r in result), result


def test_reader_offsets():
    buf = bytearray(320)
    struct.pack_into('<i', buf, 0, 42)
    for offset, value in [(4,.24), (8,.65), (24,-.20), (28,127.3),
                          (72,1122.), (76,1060.), (56,.02), (60,.03),
                          (252, 1.0), (300, .19)]:
        struct.pack_into('<f', buf, offset, value)
    sample = ACCSharedMemory.decode(bytes(buf), 4.2)
    assert sample.packet == 42
    assert abs(sample.yaw_rate - .19) < 1e-5
    assert abs(sample.steer + .2) < 1e-5
    assert abs(sample.brake - .65) < 1e-5
    assert abs(sample.front_load - 2182) < 1e-5
    assert sample.abs_active > 0


def test_reader_rejects_short_and_bad():
    assert ACCSharedMemory.decode(bytes(100), 0) is None
    buf = bytearray(320)
    struct.pack_into('<f', buf, 28, float('nan'))
    assert ACCSharedMemory.decode(bytes(buf), 0) is None


def test_provisional_grade_cannot_claim_proven_exit():
    s, n = make_event("clean")
    r = analyze(s[:n], n, phase="provisional")
    assert r.score <= 4
    assert not r.metrics["observed_exit_progress"]
