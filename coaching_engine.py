"""0.2.4 measured turn-in/brake release and post-release coaching.

PURE OFFLINE MATH ONLY: no Windows API, game memory, filesystem or vehicle
controls. A grade is a cautious technique heuristic, NOT a racing-line or
lap-time judgement. Negative/positive steer and yaw sign conventions are not
assumed equal: only yaw's own temporal sign consistency is used.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Optional, Sequence
import math
import numpy as np
from advanced_engine import TelemetrySample, Feedback

COACH_VERSION = '0.2.4.1-coach1'

@dataclass(frozen=True)
class Coaching:
    score: Optional[int]
    label: str
    explanation: str
    confidence: str
    evidence: dict

    def as_log(self) -> dict:
        return {'algorithm': COACH_VERSION, **asdict(self)}


def _elapsed(mask: np.ndarray, times: np.ndarray) -> float:
    if len(times) < 2: return 0.0
    dt = np.diff(times)
    return float(np.sum(np.where(mask[:-1] & (dt > 0) & (dt < .25), dt, 0.0)))


def assess(samples: Sequence[TelemetrySample], release_index: int,
           phase: str = 'final', legacy: Optional[Feedback] = None) -> Coaching:
    """Return an explainable immediate / later grade from REAL event samples.

    If another brake starts before the observation period ends, 'exit' remains
    unverified and 5/5 is not awarded. No forceful claim about car damage.
    """
    p = list(samples)
    base = {'source': 'raw_event', 'phase': phase,
            'exit_verified': False, 'legacy_score': legacy.score if legacy else None}
    def result(score, label, why, confidence='limited', **evidence):
        return Coaching(score, label, why, confidence, {**base, **evidence})
    if (not p or release_index < 6 or release_index > len(p)
            or p[release_index-1].time - p[0].time < .24):
        return result(None, 'INSUFFICIENT EVENT', 'Not enough continuous braking data.')
    try:
        t = np.array([s.time for s in p], dtype=float)
        b = np.array([s.brake for s in p], dtype=float)
        th = np.array([s.throttle for s in p], dtype=float)
        st = np.array([abs(s.steer) for s in p], dtype=float)
        y = np.array([s.yaw_rate for s in p], dtype=float)
        v = np.array([s.speed_kph for s in p], dtype=float)
    except (ValueError, TypeError):
        return result(None, 'INVALID SIGNAL', 'Malformed telemetry sample.')
    if (not all(np.all(np.isfinite(x)) for x in (t,b,th,st,y,v))
            or np.any(np.diff(t) <= 0) or np.any(np.diff(t) > .25)):
        return result(None, 'UNRELIABLE TELEMETRY', 'Missing or non-monotonic timestamps/signals.')
    if np.min(v) < 18 or v[0] < 30:
        return result(None, 'LOW SPEED / INCIDENT EXCLUDED',
                      'Event reaches very low speed; not a meaningful corner-technique sample.',
                      'not_applicable')
    # No single telemetry signal can assert a collision or damaged steering.
    n = release_index
    turn = (st[:n] >= .075) & (np.abs(y[:n]) >= .025) & (b[:n] >= .05)
    turn_time = _elapsed(turn, t[:n])
    post_turn = bool(np.any((st[n:] >= .09) & (np.abs(y[n:]) >= .04)))
    if turn_time < .12 or np.count_nonzero(turn) < 5:
        kind = ('BRAKE BEFORE TURN / NO MEASURED TRAIL' if post_turn
                else 'STRAIGHT BRAKING / NO TRAIL')
        return result(None, kind,
                      'Not a graded trail event; straight-line braking may be the correct technique.',
                      'not_applicable', turn_during_brake_s=round(turn_time,2))
    # Actual brake taper during contemporaneous yaw + turn-in, avoiding
    # per-event steering renormalization and sampled-snapshot claims.
    idx = np.flatnonzero(turn)
    k = max(2, len(idx)//4)
    brake_drop = float(np.median(b[idx[:k]]) - np.median(b[idx[-k:]]))
    step = np.diff(b[idx])
    # Neutral changes (<2 percentage points) are allowed; reversals are not.
    smooth_fraction = float(np.mean(step <= .02)) if len(step) else 0.0
    controlled_taper = (brake_drop >= .12 and smooth_fraction >= .74 and
                        turn_time >= .26 and len(idx) >= 8)
    high = turn & (b[:n] > .70) & (st[:n] > .12)
    heavy_s = _elapsed(high,t[:n])
    high_pct = float(np.mean(high[turn])) if np.any(turn) else 0.0
    yy = y[:n][turn]
    sign = float(max(np.mean(yy > .025), np.mean(yy < -.025))) if len(yy) else 0.
    stable_yaw = bool(sign >= .87)
    yaw_median = float(np.median(np.abs(yy))) if len(yy) else 0.
    # Avoid rewarding an out-of-control spin as "great rotation".
    # Heuristic spike guard, not a universal physical yaw target.
    spin_warning = bool(np.percentile(np.abs(yy),95) > 1.45)
    # Contemporaneous controlled release: decreasing brake in samples where
    # steering and yaw are already present. This is not causal proof.
    taper_duration = 0.0
    for i in range(n-1):
        dt = t[i+1]-t[i]
        if (0 < dt < .25 and turn[i] and turn[i+1]
                and b[i] - b[i+1] >= .008 and st[i+1] >= .075):
            taper_duration += dt
    # Count *reapplications* only AFTER the initial peak brake force.
    # The original 0.2.4 code counted the initial pedal press as repeated
    # braking and systematically lowered real driving grades.
    peak_brake_i = int(np.argmax(b[:n]))
    reapply = int(np.sum(np.diff(b[peak_brake_i:n]) > .085))

    post_s = max(0.0, float(t[-1] - t[n-1]))
    coasting = 0.0
    if len(p)>n:
        coast_mask = (b[n:] < .04)&(th[n:] < .05)&(st[n:] >= .075)
        coasting = _elapsed(coast_mask,t[n:])
    throttle_window = (th[n:] > .25) if len(p)>n else np.array([],dtype=bool)
    on_throttle = _elapsed(throttle_window,t[n:]) if len(p)>n else 0.
    # Require speed to actually increase AFTER the brake is released. This is
    # only evidence of local acceleration, not exit quality or lap time gain.
    speed_gain = float(v[-1] - np.min(v[n:])) if len(p)>n else 0.
    exit_progress = (phase=='final' and post_s>=1.2 and
                     on_throttle >= .18 and speed_gain >= 3.0)
    interrupted = bool(phase=='final' and post_s < 2.8 and len(p)>n and b[-1]>.12)
    evidence = {
        'turn_during_brake_s':round(turn_time,2),
        'brake_taper_pct':round(100*brake_drop,1),
        'taper_during_turn_s':round(taper_duration,2),
        'taper_smooth_pct':round(100*smooth_fraction,1),
        'controlled_taper':bool(controlled_taper),
        'heavy_brake_turn_s':round(heavy_s,2),
        'heavy_brake_turn_pct':round(high_pct*100,1),
        'yaw_direction_consistency_pct':round(sign*100,1),
        'median_abs_yaw_deg_s':round(math.degrees(yaw_median),1),
        'post_release_observed_s':round(post_s,2),
        'coasting_after_release_s':round(coasting,2),
        'throttle_observed_s':round(on_throttle,2),
        'speed_gain_after_release_kph':round(speed_gain,1),
        'exit_verified':bool(exit_progress),
        'exit_interrupted':interrupted,
        'brake_reapplications':reapply,
        'turn_sample_count':int(len(idx)),
    }
    reasons=[]
    score=3
    if controlled_taper and taper_duration>=.08 and stable_yaw:
        score=4
        reasons.append('measured gradual brake release while the car turns')
    elif brake_drop < .04:
        reasons.append('little brake taper while turning')
    else:
        reasons.append('brake release or yaw response needs review')
    if heavy_s>=.18 or high_pct>=.24:
        score-=1
        reasons.append('high brake pressure persists during significant steering')
    elif heavy_s>=.09:
        reasons.append('some high-brake turning overlap')
    if not stable_yaw or spin_warning:
        score=min(score,2)
        reasons.append('yaw is unstable or unusually high')
    if reapply >=2:
        score-=1
        reasons.append('multiple brake reapplications')
    if coasting>=1.7:
        score-=2
        reasons.append('extended neutral-pedal coasting while turning')
    elif coasting>=.75:
        score-=1
        reasons.append('neutral-pedal coasting while turning')
    # A perfect score requires independent, time-resolved evidence. Do not
    # force an arbitrary histogram or mislabel "fastest exit".
    perfect = (phase=='final' and exit_progress and controlled_taper and
               taper_duration>=.12 and turn_time>=.35 and stable_yaw and
               sign>=.92 and not spin_warning and heavy_s<.08 and
               high_pct<.10 and coasting<.35 and reapply==0)
    if perfect:
        score=5
        reasons.append('early acceleration after release observed')
    else:
        score=min(score,4)
    score=max(1,min(5,score))
    if phase=='provisional':
        reasons.append('exit still being observed')
    elif not exit_progress:
        reasons.append('exit quality not verified by available telemetry')
    evidence['exit_verified'] = bool(exit_progress)
    if coasting>=.75:
        label='COASTING TO REVIEW'
    elif heavy_s>=.18 or high_pct>=.24:
        label='HIGH BRAKE WHILE TURNING'
    elif not stable_yaw or spin_warning:
        label='ROTATION UNSTABLE / CHECK'
    elif perfect:
        label='CONTROLLED TRAIL + EXIT OBSERVED'
    elif controlled_taper:
        label='CONTROLLED TRAIL / EXIT NOT PROVEN'
    else:
        label='TRAIL TO REVIEW'
    confidence=('provisional' if phase=='provisional' else
                'moderate' if exit_progress and post_s>=2 else 'limited')
    return result(score, label, '; '.join(reasons[:4]).capitalize()+'.',
                  confidence, **evidence)
