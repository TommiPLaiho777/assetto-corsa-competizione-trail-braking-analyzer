"""Opt-in, evidence-gated corner *names* for ACC Nurburgring 24h.

External RaceIQ metadata is downloaded to a local, ignored directory by an
explicit user action. This module never grades the racing line or modifies ACC.
Names are suppressed unless independently checked graphics/fastlane position
samples agree over time. It is deliberately safe to run without metadata.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Optional

META_DIR = Path(__file__).resolve().parent / 'data' / 'track_metadata'
META_FILE = 'nordschleife.json'
SEGMENT_FILE = 'nordschleife-segments.json'
CONFIG_FILE = 'fastlane_path.txt'


def circular_delta(a: float, b: float) -> float:
    """Distance of lap fractions on a periodic [0, 1) domain."""
    return abs(((a - b + 0.5) % 1.0) - 0.5)


@dataclass(frozen=True)
class Turn:
    number: int
    display_name: str
    start: float
    end: float
    source_name: str


class CornerCatalog:
    def __init__(self, turns: list[Turn]):
        if len(turns) < 10:
            raise ValueError('Too few corner intervals')
        self.turns = tuple(sorted(turns, key=lambda t: t.start))

    @classmethod
    def from_data(cls, meta: dict, layout: dict) -> 'CornerCatalog':
        if meta.get('slug') != 'nordschleife' or not isinstance(meta.get('corners'), list):
            raise ValueError('Wrong or unsupported metadata layout')
        corners = {}
        for c in meta['corners']:
            if not isinstance(c, dict) or not isinstance(c.get('number'), int):
                raise ValueError('Bad corner name record')
            number = c['number']
            if number in corners or not 1 <= number <= 150:
                raise ValueError('Duplicate / invalid corner number')
            name = str(c.get('name') or '').strip()
            group = str(c.get('group') or '').strip()
            if len(name) > 70 or len(group) > 70:
                raise ValueError('Unexpected corner name length')
            corners[number] = (name, group)
        if len(corners) < 40:
            raise ValueError('Incomplete corner name file')
        if not isinstance(layout.get('segments'), list):
            raise ValueError('Missing segment boundaries')
        turns = []
        seen = set()
        for segment in layout['segments']:
            key = segment.get('key')
            if not isinstance(key, str) or not key.startswith('t') or not key[1:].isdigit():
                continue
            num = int(key[1:])
            if num in seen or num not in corners:
                raise ValueError('Unknown or duplicate turn segment')
            seen.add(num)
            a, b = float(segment['startFrac']), float(segment['endFrac'])
            if not all(map(math.isfinite, (a, b))) or not 0 <= a < b <= 1:
                raise ValueError('Invalid corner fraction interval')
            name, group = corners[num]
            # An unnamed turn has a usable group, but otherwise use a clear
            # turn number without inventing a geographic name.
            display = name or group or f'Turn {num}'
            turns.append(Turn(num, display, a, b, name))
        if len(turns) != len(corners):
            raise ValueError('Incomplete segment coverage')
        ordered = sorted(turns, key=lambda t: t.start)
        if any(x.end > y.start + 1e-7 for x, y in zip(ordered, ordered[1:])):
            raise ValueError('Overlapping corner regions')
        return cls(turns)

    @classmethod
    def load(cls, folder: Path = META_DIR) -> Optional['CornerCatalog']:
        a, b = folder / META_FILE, folder / SEGMENT_FILE
        if not a.is_file() or not b.is_file():
            return None
        return cls.from_data(json.loads(a.read_text('utf-8')),
                             json.loads(b.read_text('utf-8')))

    def at_fraction(self, fraction: float) -> Optional[Turn]:
        if not math.isfinite(fraction) or not 0 <= fraction <= 1.0:
            return None
        pos = fraction % 1.0
        return next((t for t in self.turns if t.start <= pos < t.end), None)


class CornerNameGate:
    """Position-gated corner labels with measured progress registration.

    RaceIQ's segment fractions refer to its extracted AI reference geometry.
    ACC's normalizedCarPosition can use a different lap-zero and even slightly
    different arc-length parameterisation. Requiring their *absolute* values to
    agree (as v0.3.1 did) wrongly suppressed all labels on some layouts.

    Instead validate that geometry and normalized progress advance consistently
    over a moving window, then look up names using the AI *reference* fraction.
    Unknown, inconsistent, stale or out-of-coverage telemetry is still unlabeled.
    """
    def __init__(self, catalog: CornerCatalog, reference, min_frames: int = 15):
        self.catalog = catalog
        self.reference = reference
        self.min_frames = min_frames
        self.samples = deque(maxlen=36)
        self._last = None
        self._last_time = None
        self.status = 'Awaiting live graphics frames / track alignment'

    def reset(self):
        self.samples.clear()
        self._last = None
        self._last_time = None
        self.status = 'Awaiting live graphics frames / track alignment'

    def _invalidate(self, status: str):
        self.samples.clear()
        self._last = None
        self._last_time = None
        self.status = status

    def observe(self, sample, at: float):
        if sample is None:
            # Duplicated/missed graphics frames are normal; allow short gaps.
            if self._last_time is not None and at - self._last_time > 1.0:
                self._invalidate('Graphics position unavailable (stale)')
            return
        self._last = None
        self._last_time = None
        progress = float(sample.normalized_position)
        if not math.isfinite(progress) or not 0 <= progress <= 1:
            self._invalidate('Invalid ACC lap progress')
            return
        offset = self.reference.deviation(*sample.xyz)
        if offset is None or offset.distance_m > 14 or offset.vertical_m > 6:
            self._invalidate('ACC position too far from AI reference')
            return
        total = float(self.reference.s[-1] - self.reference.s[0])
        if not math.isfinite(total) or total <= 0:
            self._invalidate('Invalid fastlane reference length')
            return
        ref_fraction = ((offset.s_m - float(self.reference.s[0])) / total) % 1.0
        if not math.isfinite(ref_fraction):
            self._invalidate('Invalid reference progress')
            return
        # A consistent constant origin difference is permitted. Protect
        # against mis-matched layouts, sudden position jumps and reversed motion
        # by checking how BOTH progress signals advance, not their zero point.
        origin_delta = ((progress - ref_fraction + .5) % 1.0) - .5
        self.samples.append((at, progress, ref_fraction, origin_delta))
        if len(self.samples) < self.min_frames:
            self.status = f'Collecting position frames ({len(self.samples)}/{self.min_frames})'
            return
        span = list(self.samples)[-self.min_frames:]
        first, last = span[0], span[-1]
        elapsed = last[0] - first[0]
        # Each frame should represent a progressing on-track movement; a
        # garage/stationary stream must not be mistaken for calibration.
        moved_acc = ((last[1] - first[1] + .5) % 1.0) - .5
        moved_ref = ((last[2] - first[2] + .5) % 1.0) - .5
        if elapsed > 2.0 or elapsed <= 0:
            self._invalidate('Graphics frame cadence discontinuity')
            return
        if moved_acc <= .00015 or moved_ref <= .00015:
            self.status = 'Waiting for forward movement'
            return
        origin0 = first[3]
        variations = [abs(((x[3]-origin0+.5)%1.0)-.5) for x in span]
        if max(variations) > .008 or abs(moved_acc - moved_ref) > .008:
            self._invalidate('Lap progress and AI path move inconsistently')
            return
        # These boundaries are specified in the independent RaceIQ AI-route
        # coordinate system. Never compare them to ACC's potentially shifted
        # normalizedCarPosition without registration.
        self._last = self.catalog.at_fraction(ref_fraction)
        self._last_time = at
        self.status = ('Reference aligned; ' + (self._last.display_name if self._last
                      else 'between corner regions'))

    def candidate(self, at: float):
        if self._last_time is None or at - self._last_time > .22:
            return None
        return self._last
