"""Heuristic, explainable ACC trail-braking feedback based on actual yaw.

This is *not* an optimal racing-line model and cannot establish that braking
caused rotation. It intentionally makes no universal brake-vs-steer ideal curve.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional
import numpy as np


@dataclass(frozen=True)
class TelemetrySample:
    time: float
    packet: int
    speed_kph: float
    brake: float           # 0..1
    throttle: float        # 0..1
    steer: float           # -1..1 ACC steering input
    yaw_rate: float        # localAngularVel[1], rad/s
    abs_active: float = 0.0
    front_load: float = 0.0
    front_slip: float = 0.0


@dataclass(frozen=True)
class Feedback:
    phase: str
    score: Optional[int]
    label: str
    explanation: str
    metrics: dict

    def as_log(self) -> dict:
        return {"version": 2, "mode": "advanced", "phase": self.phase,
                "score": self.score, "label": self.label,
                "explanation": self.explanation, "metrics": self.metrics}


def analyze(samples: list[TelemetrySample], release_index: int,
            phase: str = "final") -> Feedback:
    """Evaluate a completed braking event plus optional post-release samples.

    A numerical grade is a *training heuristic*, not a ground-truth metric.
    Deliberately refuse to grade straight braking without a measured turn.
    """
    if not samples or release_index < 5 or release_index > len(samples):
        return Feedback(phase, None, "INSUFFICIENT DATA", "Brake event too short to assess.", {})
    brake_samples = samples[:release_index]
    if brake_samples[-1].time - brake_samples[0].time < .20 or max(x.brake for x in brake_samples) < .18:
        return Feedback(phase, None, "INSUFFICIENT DATA", "Brief brake tap; not graded.", {})
    times = np.fromiter((x.time for x in samples), float)
    brake = np.fromiter((x.brake for x in samples), float)
    throttle = np.fromiter((x.throttle for x in samples), float)
    steer = np.fromiter((abs(x.steer) for x in samples), float)
    yaw = np.fromiter((abs(x.yaw_rate) for x in samples), float)
    speed = np.fromiter((x.speed_kph for x in samples), float)
    abs_used = np.fromiter((x.abs_active > .05 for x in samples), bool)
    if not np.all(np.isfinite(yaw)):
        return Feedback(phase, None, "YAW DATA MISSING", "Cannot score rotation without valid yaw rate.", {})
    if max(speed) < 30.:
        return Feedback(phase, None, "INSUFFICIENT DATA", "Below minimum driving speed.", {})
    n = release_index
    in_turn = (steer[:n] >= .075) & (yaw[:n] >= .025)
    later_turn = np.any((steer[n:] >= .09) & (yaw[n:] >= .05))
    any_turn = np.sum(in_turn) >= 3 or later_turn
    duration = float(times[n - 1] - times[0])
    metrics = {
        "duration_s": round(duration, 2),
        "start_speed_kph": round(float(speed[0]), 1),
        "release_speed_kph": round(float(speed[n - 1]), 1),
        "peak_brake_pct": round(float(max(brake[:n]) * 100), 1),
        "peak_yaw_deg_s": round(float(np.degrees(max(yaw))), 1),
        "brake_steer_overlap_pct": 0., "coast_after_release_s": 0.,
        "abs_samples_pct": round(float(100. * np.mean(abs_used[:n])), 1),
    }
    if not any_turn:
        label = "STRAIGHT BRAKING" if phase == "final" else "WAITING FOR TURN"
        return Feedback(phase, None, label,
                        "No measurable corner rotation: straight-line braking is not graded as trail braking.", metrics)

    # Measured overlap: >70% brake simultaneous with >12% steering.
    # Ratio evaluated only over frames involving measurable turn-in before release.
    turn_frames = (steer[:n] >= .075) & (yaw[:n] >= .025)
    heavy_overlap = float(np.mean((brake[:n][turn_frames] > .70) &
                                  (steer[:n][turn_frames] > .12))) if np.any(turn_frames) else 0.
    metrics["brake_steer_overlap_pct"] = round(heavy_overlap * 100, 1)
    # Lifting the brake is not automatically 'good' if the car then coasts while still turning.
    coast = 0.
    for j in range(n, len(samples) - 1):
        dt = min(.2, max(0., times[j + 1] - times[j]))
        if brake[j] < .04 and throttle[j] < .05 and steer[j] > .075:
            coast += dt
    metrics["coast_after_release_s"] = round(coast, 2)
    # A 5/5 should require at least *some* observed exit progress; a yaw rise
    # during steering alone must not be rewarded as a proven successful corner.
    exit_progress = bool(phase == "final" and len(samples) > n + 4 and
                         np.any(throttle[n:] > .25) and
                         float(speed[-1] - speed[n]) >= 2.0)
    metrics["observed_exit_progress"] = exit_progress

    peak_idx = int(np.argmax(brake[:n]))
    trail_idx = np.arange(peak_idx, n)
    turn_while_braking = int(np.sum((steer[trail_idx] > .085) &
                                     (yaw[trail_idx] > .035) & (brake[trail_idx] > .05)))
    early_release = turn_while_braking < 3 and later_turn

    # Yaw build measured from a *consistent* turn phase rather than a normalized ellipse.
    turn_yaw = yaw[:n][turn_frames]
    yaw_built = bool(len(turn_yaw) >= 6 and
                     float(np.median(turn_yaw[-max(3, len(turn_yaw)//4):])) >
                     float(np.median(turn_yaw[:max(3, len(turn_yaw)//4)])) + .025)
    # Pedal reapplications after peak; ignore minute noise (<8 percentage points).
    reapply = int(np.sum(np.diff(brake[peak_idx:n]) > .08))
    metrics["yaw_built_during_braking"] = yaw_built
    metrics["brake_reapplications"] = reapply
    metrics["turn_samples_under_brake"] = turn_while_braking

    # Simple and deliberately modest training heuristic. Does not infer optimum speed.
    value = 3.8
    if yaw_built:
        value += .6
    if turn_while_braking >= 3 and heavy_overlap < .12:
        value += .4
    value -= min(1.9, 2.6 * max(0., heavy_overlap - .10))
    value -= min(.5, .25 * reapply)
    if early_release:
        value -= .6
    if phase == "final" and coast > .6:
        value -= min(1.4, (coast - .6) * 1.1 + .4)
    grade = max(1, min(5, int(math.floor(value + .5))))
    if not exit_progress:
        grade = min(4, grade)

    if phase == "final" and coast > .6:
        label = "COASTING AFTER RELEASE"
        why = f"{coast:.1f}s of neutral pedal while turning; review entry speed, line and rotation."
    elif heavy_overlap > .20:
        label = "HIGH BRAKE + STEER"
        why = "Strong braking overlaps with cornering. Test an earlier straight-line braking point."
    elif early_release:
        label = "BRAKE BEFORE TURN"
        why = "Brake released before measurable turn-in. This can be correct; compare exit speed."
    elif yaw_built:
        label = "ROTATION BUILDING"
        why = "Measured yaw rises during release. Confirm stability and corner-exit speed."
    else:
        label = "ROTATION TO REVIEW"
        why = "Turning detected, but no clear yaw build during the measured brake phase."
    if phase == "provisional":
        why += " (Provisional: checking exit)"
    return Feedback(phase, grade, label, why, metrics)


class EventTracker:
    """Event state machine. Results are returned immediately upon brake release
    and updated ~1.2 s later once coast/exit evidence has been collected."""

    def __init__(self, post_seconds: float = 1.2):
        self.state = "idle"
        self.samples: list[TelemetrySample] = []
        self.release_index = 0
        self.release_time = 0.
        self.release_count = 0
        self.post_seconds = post_seconds
        self.last_event_time = -1e9
        self.max_samples = 3000
        # Read-only copy of just-finished event for independent shadow scoring.
        self.last_completed_event = None

    def reset(self):
        self.state = "idle"
        self.samples = []
        self.release_index = 0
        self.release_count = 0

    def update(self, sample: TelemetrySample) -> list[Feedback]:
        result: list[Feedback] = []
        self.last_completed_event = None
        if self.state == "idle":
            if sample.speed_kph > 30 and sample.brake > .06 and sample.time - self.last_event_time >= .15:
                self.samples = [sample]
                self.state = "braking"
                self.release_count = 0
        elif self.state == "braking":
            if len(self.samples) >= self.max_samples:
                self.reset()
                return [Feedback("final", None, "EVENT TOO LONG", "Event capture limit reached.", {})]
            self.samples.append(sample)
            self.release_count = self.release_count + 1 if sample.brake < .025 else 0
            if self.release_count >= 2:
                self.release_index = len(self.samples)
                self.release_time = sample.time
                self.state = "exit"
                result.append(analyze(self.samples, self.release_index, "provisional"))
        elif self.state == "exit":
            if len(self.samples) < self.max_samples:
                self.samples.append(sample)
            if sample.time - self.release_time >= self.post_seconds or sample.brake > .12:
                result.append(analyze(self.samples, self.release_index, "final"))
                self.last_completed_event = (tuple(self.samples), self.release_index)
                self.last_event_time = sample.time
                self.reset()
                # A new brake press can start a new event immediately.
                if sample.brake > .12 and sample.speed_kph > 30:
                    self.samples = [sample]
                    self.state = "braking"
        return result
