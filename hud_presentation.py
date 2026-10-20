"""Pure, offline-only Mini HUD decisions.

No game memory access or input. This is a technique heuristic, not a racing
line / apex detector. Display only after a stable straight-ish interval.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# Only post-release observation and display gate are shortened. These do NOT
# change the mathematical scoring criteria or the ACC mapping reader.
# Both must be nonzero: a final score needs actual exit evidence, and the
# driver should have time to stabilize steering before seeing a new result.
POST_RELEASE_OBSERVATION_S = 2.6
STEADY_STRAIGHT_S = 0.24

SCORE_COLORS = {
    5: '#3EFF8F',  # green: successful
    4: '#A8EE74',  # yellow-green: good
    3: '#FFB347',  # orange: developing
    2: '#FF824D',  # orange-red: poor
    1: '#FF5265',  # red: unsuccessful
    None: '#B9C4D1',
}
GOOD = '#3EFF8F'
CAUTION = '#FFB347'
POOR = '#FF5265'
NEUTRAL = '#BEC9D6'


@dataclass(frozen=True)
class HUDMessage:
    grade: Optional[int]
    text: str
    number_color: str
    text_color: str

    @property
    def number(self) -> str:
        return '–' if self.grade is None else str(self.grade)


def describe(coaching) -> HUDMessage:
    """Convert a *final* coaching result into a glanceable, honest phrase.

    No 'missed apex' until actual track coordinates have been implemented and
    validated. A straight-line brake event may be technically correct.
    """
    if coaching is None:
        return HUDMessage(None, 'Analysis unavailable', SCORE_COLORS[None], NEUTRAL)
    score = coaching.score if coaching.score in SCORE_COLORS else None
    label = str(coaching.label or '').upper()
    evidence = coaching.evidence or {}
    if 'HIGH BRAKE' in label:
        phrase, color = 'Brake too heavy at turn-in', POOR if score is not None and score <= 2 else CAUTION
    elif 'ROTATION UNSTABLE' in label:
        phrase, color = 'Rotation unstable', POOR
    elif 'COASTING' in label:
        secs = float(evidence.get('coasting_after_release_s', 0) or 0)
        phrase, color = 'Too long off pedals', POOR if secs >= 1.7 else CAUTION
    elif 'CONTROLLED TRAIL + EXIT' in label:
        phrase, color = 'Controlled trail & exit', GOOD
    elif 'CONTROLLED TRAIL' in label:
        phrase, color = 'Good trail, exit unverified', CAUTION
    elif 'BRAKE BEFORE TURN' in label:
        phrase, color = 'Brake before turn — no trail', CAUTION
    elif 'STRAIGHT BRAKING' in label:
        phrase, color = 'Straight braking — no trail', CAUTION
    elif 'TRAIL TO REVIEW' in label:
        phrase, color = 'Refine brake release', CAUTION
    elif 'LOW SPEED' in label:
        phrase, color = 'Low speed — not graded', NEUTRAL
    elif 'UNRELIABLE' in label or 'INVALID' in label or 'INSUFFICIENT' in label:
        phrase, color = 'Insufficient telemetry', NEUTRAL
    else:
        # Conservative fallback for any future or unrecognized diagnosis.
        phrase, color = 'Review braking technique', CAUTION if score else NEUTRAL
    return HUDMessage(score, phrase, SCORE_COLORS[score], color)


def safe_straight(sample) -> bool:
    """Coarse display-delay gate, NOT an assertion of driving safety.

    We check steering, yaw, brake and speed to avoid encouraging glances during
    an active corner. Meant only for post-event text display, not for scoring.
    """
    return (sample.speed_kph >= 35.0 and sample.brake < 0.045 and
            abs(sample.steer) <= 0.075 and abs(sample.yaw_rate) <= 0.12)
