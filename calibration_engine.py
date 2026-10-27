"""0.2.3 shadow-only trail-braking calibration.

This deliberately does not alter the production 0.2.2 grade. A score is a
coaching heuristic, NOT a proof of the optimal line, causation or time gained.
No file, process, Windows API, ACC shared memory or UI access in this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Optional, Sequence

import numpy as np

from advanced_engine import TelemetrySample

CALIBRATION_VERSION = '0.2.3-shadow1'


@dataclass(frozen=True)
class Calibration:
    score: Optional[int]
    label: str
    explanation: str
    confidence: str
    evidence: dict

    def as_log(self) -> dict:
        d = asdict(self)
        d['algorithm'] = CALIBRATION_VERSION
        return d


def _float(metrics: dict, key: str, default: float = 0.0) -> float:
    try:
        v = float(metrics.get(key, default))
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def extra_from_samples(samples: Sequence[TelemetrySample], release_index: int) -> dict:
    """Compute extra measures that *cannot* be recovered from archived 0.2.2 logs.

    Steering/yaw use absolute magnitudes; steer and yaw sign conventions are
    not asserted equal without verification in ACC. Yaw directional consistency
    is evidence only, not an assertion of an ideal slip/rotation target.
    """
    if not samples or release_index <= 1 or release_index > len(samples):
        return {}
    turns = list(samples[:release_index])
    selected = [s for s in turns if abs(s.steer) >= .075 and
                abs(s.yaw_rate) >= .025 and s.brake >= .05]
    # For real taper evidence, demand enough actual on-brake steering samples.
    taper = None
    direction_consistency = None
    high_brake_turn_seconds = 0.0
    if len(selected) >= 6:
        k = max(2, len(selected)//4)
        first = np.median([s.brake for s in selected[:k]])
        last = np.median([s.brake for s in selected[-k:]])
        taper = float(first - last)
        signs = np.sign([s.yaw_rate for s in selected])
        direction_consistency = float(max(np.mean(signs > 0), np.mean(signs < 0)))
    for a, b in zip(turns, turns[1:]):
        dt = b.time - a.time
        if 0 < dt < .25 and abs(a.steer) >= .12 and abs(a.yaw_rate) >= .025 and a.brake > .70:
            high_brake_turn_seconds += dt
    coast_window = max(0.0, samples[-1].time - turns[-1].time)
    # Provisional/short exit windows must NEVER claim a verified corner exit.
    return {
        'taper_during_turn_pct': (round(100*taper, 1) if taper is not None else None),
        'yaw_direction_consistency_pct': (round(100*direction_consistency, 1)
                                          if direction_consistency is not None else None),
        'high_brake_turn_s': round(high_brake_turn_seconds, 3),
        'post_release_observation_s': round(coast_window, 2),
        'turn_sample_count': len(selected),
    }


def calibrate_metrics(old_row: dict, extra: Optional[dict] = None) -> Calibration:
    """Grade separately using recorded 0.2.2 metrics, optionally augmented by raw signal.

    Historical 0.2.2 rows cannot certify controlled taper and are marked
    'limited'; this algorithm will never invent that evidence. Straight/entry
    braking are ungraded as *trail braking*, not labelled poor driving.
    """
    old_score = old_row.get('score')
    metrics = old_row.get('metrics') or {}
    extra = dict(extra or {})
    evidence = {'source': 'raw_event' if extra else 'archived_metrics_only',
                'legacy_score': old_score,
                'brake_steer_overlap_pct': _float(metrics,'brake_steer_overlap_pct'),
                'coast_after_release_s': _float(metrics,'coast_after_release_s'),
                'turn_samples_under_brake': int(_float(metrics,'turn_samples_under_brake')),
                'yaw_built_during_braking': bool(metrics.get('yaw_built_during_braking',False)),
                'observed_exit_progress': bool(metrics.get('observed_exit_progress',False)),
                'brake_reapplications': int(_float(metrics,'brake_reapplications'))}
    evidence.update(extra)
    confidence = 'moderate' if extra and extra.get('taper_during_turn_pct') is not None else 'limited'
    label = old_row.get('label','')
    if old_score is None:
        return Calibration(None, 'NOT SCORED / STRAIGHT OR INVALID',
                           'No valid trail-braking event; not a low driving grade.',
                           'not_applicable', evidence)
    # If the turn happens *after* brake release, there is no actual brake-assisted turn.
    if label == 'BRAKE BEFORE TURN' or evidence['turn_samples_under_brake'] < 3:
        return Calibration(None, 'ENTRY BRAKE / NO MEASURED TRAIL',
                           'Straight-entry braking may be correct; evaluate corner outcome separately.',
                           'moderate' if extra else 'limited', evidence)

    # Start from evidence of a measured turn under braking, not a generous 3.8/5 baseline.
    score = 3
    reasons = []
    yaw_built = evidence['yaw_built_during_braking']
    overlap = evidence['brake_steer_overlap_pct']
    coast = evidence['coast_after_release_s']
    exit_seen = evidence['observed_exit_progress']
    reapply = evidence['brake_reapplications']
    if yaw_built:
        if exit_seen:
            score += 1
        reasons.append('yaw increased during the braking phase')
    else:
        reasons.append('yaw build not demonstrated')
    # Only raw steering/brake trajectory can demonstrate a controlled taper.
    taper = extra.get('taper_during_turn_pct')
    consistent = extra.get('yaw_direction_consistency_pct')
    enough = extra.get('turn_sample_count', 0) >= 8
    controlled_taper = taper is not None and taper >= 10.0
    if overlap >= 20:
        score -= 1
        reasons.append('heavy braking overlaps steering')
    elif overlap >= 10:
        reasons.append('some heavy brake/steer overlap')
    if coast >= .6:
        score -= 1
        reasons.append('neutral-pedal coasting observed')
    if reapply >= 2:
        score -= 1
        reasons.append('multiple brake reapplications')
    if not yaw_built:
        score = min(score, 3)
    if not exit_seen:
        score = min(score, 3)
        reasons.append('no early exit-progress evidence')
    if extra:
        if controlled_taper and enough:
            score += 1
            reasons.append('measured brake taper during turning')
        elif taper is not None and taper < 3:
            reasons.append('little measured brake taper during turning')
        if consistent is not None and consistent < 75:
            score = min(score, 3)
            reasons.append('changing yaw direction; review corner context')
        # 5 only with multiple independent positive observations.
        can_five = (yaw_built and exit_seen and controlled_taper and enough and
                    (consistent is None or consistent >= 80) and overlap < 10 and
                    coast < .3 and reapply == 0)
        if can_five:
            score = 5
        else:
            score = min(score, 4)
    else:
        # Aggregate historical data lacks brake-taper evidence, so 5 isn't supported.
        score = min(score, 4)
        reasons.append('historical log lacks brake-taper samples')
    if overlap >= 20:
        score = min(score, 3)
    if not exit_seen or not yaw_built:
        score = min(score, 3)
    score = max(1, min(5,score))
    if score == 5:
        out_label = 'STRONG TRAIL (PROVISIONAL EXIT)'
    elif score == 4:
        out_label = 'PROMISING TRAIL'
    elif score == 3:
        out_label = 'TRAIL TO REVIEW'
    else:
        out_label = 'TRAIL TECHNIQUE WARNING'
    if extra and (taper is None or not enough):
        confidence = 'limited'
    explanation = '; '.join(reasons).capitalize() + '. Exit progress is not proof of a fast corner.'
    if not extra:
        explanation += ' Historic score based only on saved summary metrics.'
    return Calibration(score, out_label, explanation, confidence, evidence)


def calibrate_live(old_feedback, samples: Sequence[TelemetrySample], release_index: int) -> Calibration:
    """Called ONLY after original 0.2.2 final feedback, never during memory reading."""
    extra = extra_from_samples(samples, release_index)
    return calibrate_metrics(old_feedback.as_log(), extra=extra)
