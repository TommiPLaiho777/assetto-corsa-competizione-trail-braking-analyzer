"""Pedal overlap coach: pure-Python, game-agnostic logic.

Ported from user's pedals.py state machine, deliberately WITHOUT that file's
unsafe named-mapping creation call. Feed this monitor validated samples
already read through the application's guarded read-only ACCSharedMemory.

A pulse shows sustained gas+brake overlap (red), or clean brake->throttle
transition (green). It is NOT a racing-line or speed grade.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Optional

GAS_THRESHOLD = 0.02
BRAKE_THRESHOLD = 0.02
BRAKING_START = 0.05
THROTTLE_RETURN = 0.10
# A 2%/2%, 150ms overlap is recorded as a micro-transition, NOT a warning.
# A warning needs meaningful concurrent pressure and sustained duration.
MICRO_AFTER_S = 0.15
RED_AFTER_S = 0.24   # strong: both pedals >= 20%
STRONG_BOTH_THRESHOLD = 0.20
MEDIUM_BOTH_THRESHOLD = 0.05
MEDIUM_RED_AFTER_S = 0.36
LIGHT_RED_AFTER_S = 0.60
SAMPLE_GAP_RESET_S = 0.75
DOWNSHIFT_BLIP_SUPPRESSION_S = 0.60
RED_HOLD_S = 0.85
GREEN_HOLD_S = 0.70
FLASH_PERIOD_S = 0.26
FLASH_ON_PART = 0.69


@dataclass(frozen=True)
class PedalEvent:
    success: bool
    duration_sec: float
    peak_gas_percent: float
    peak_brake_percent: float
    started_at: float
    ended_at: float
    micro_overlap: bool = False
    severity: str = 'clean'  # clean, micro, significant


@dataclass(frozen=True)
class PedalDisplay:
    color: str | None = None     # red, green, or None
    lit: bool = False
    completed: Optional[PedalEvent] = None


class PedalOverlapMonitor:
    """One state machine per live app; no UI, timers, disk, or ACC handles.

    Input gas/brake are fractions 0..1; now is telemetry monotonic time.
    gear is optional: if a future validated reader supplies it, prevent
    known downshift throttle blips from creating false overlap warnings.
    When gear is absent, the module does *not* pretend to detect blips.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self._last_at = None
        self._gear = None
        self._blip_until = 0.0
        self._phase = 'idle'
        self._start = None
        self._overlap_start = None
        self._max_overlap = 0.0
        self._overlap_total = 0.0
        self._strong_since = None
        self._medium_since = None
        self._significant = False
        self._peak_gas = 0.0
        self._peak_brake = 0.0
        self._pulse = None
        self._pulse_started = float('-inf')
        self._pulse_until = float('-inf')

    def _flash(self, color: str, now: float, duration: float):
        if color != self._pulse or now >= self._pulse_until:
            self._pulse_started = now
        self._pulse = color
        self._pulse_until = now + duration

    def _appearance(self, now, event=None):
        if self._pulse is None or now >= self._pulse_until:
            self._pulse = None
            return PedalDisplay(completed=event)
        phase = ((now - self._pulse_started) % FLASH_PERIOD_S) / FLASH_PERIOD_S
        return PedalDisplay(self._pulse, phase < FLASH_ON_PART, event)

    def display(self, now: float) -> PedalDisplay:
        """Render a current blink even when the gear-aware filter buffers input."""
        return self._appearance(now)

    def _close_overlap(self, now):
        self._strong_since = None
        self._medium_since = None
        if self._overlap_start is not None:
            duration = max(0., now - self._overlap_start)
            self._max_overlap = max(self._max_overlap, duration)
            self._overlap_total += duration
            self._overlap_start = None

    def update(self, gas: float, brake: float, now: float,
               gear: Optional[int] = None) -> PedalDisplay:
        values = (gas, brake, now)
        if not all(isfinite(x) for x in values) or not (0 <= gas <= 1.05 and 0 <= brake <= 1.05):
            self.reset()
            return PedalDisplay()
        if self._last_at is not None and (now <= self._last_at or now - self._last_at > SAMPLE_GAP_RESET_S):
            self.reset()
        self._last_at = now

        # Optional matching of the original pedal tool's downshift blip filter.
        if gear is not None:
            if self._gear is not None and gear != self._gear:
                self._blip_until = now + DOWNSHIFT_BLIP_SUPPRESSION_S
            self._gear = gear
        filtered_gas = 0. if now < self._blip_until else gas

        if self._phase == 'idle' and brake > BRAKING_START:
            self._phase = 'braking'
            self._start = now
            self._max_overlap = 0.
            self._overlap_total = 0.
            self._strong_since = None
            self._medium_since = None
            self._significant = False
            self._peak_gas = 0.
            self._peak_brake = 0.
            self._pulse = None   # clear previous green at start of next braking
            self._overlap_start = None

        if self._phase != 'braking':
            return self._appearance(now)

        if filtered_gas > GAS_THRESHOLD and brake > BRAKE_THRESHOLD:
            if self._overlap_start is None:
                self._overlap_start = now
            overlap_duration = now - self._overlap_start
            self._max_overlap = max(self._max_overlap, overlap_duration)
            self._peak_gas = max(self._peak_gas, gas)
            self._peak_brake = max(self._peak_brake, brake)
            # Continuous simultaneous pressure, not separately observed peaks.
            if filtered_gas >= STRONG_BOTH_THRESHOLD and brake >= STRONG_BOTH_THRESHOLD:
                if self._strong_since is None:
                    self._strong_since = now
            else:
                self._strong_since = None
            if filtered_gas >= MEDIUM_BOTH_THRESHOLD and brake >= MEDIUM_BOTH_THRESHOLD:
                if self._medium_since is None:
                    self._medium_since = now
            else:
                self._medium_since = None
            if ((self._strong_since is not None and now - self._strong_since >= RED_AFTER_S)
                or (self._medium_since is not None and now - self._medium_since >= MEDIUM_RED_AFTER_S)
                or overlap_duration >= LIGHT_RED_AFTER_S):
                self._significant = True
            if self._significant:
                self._flash('red', now, RED_HOLD_S)
        else:
            self._close_overlap(now)

        completed = None
        # Finish only when the brake is released and actual throttle returns.
        if brake < BRAKE_THRESHOLD and filtered_gas > THROTTLE_RETURN:
            self._close_overlap(now)
            failed = self._significant
            micro = not failed and self._max_overlap >= MICRO_AFTER_S
            completed = PedalEvent(not failed, round(self._max_overlap, 3),
                                   round(self._peak_gas * 100, 1),
                                   round(self._peak_brake * 100, 1),
                                   self._start, now, micro,
                                   'significant' if failed else ('micro' if micro else 'clean'))
            self._phase = 'idle'
            self._overlap_start = None
            # Micro overlaps are recorded, but are not rewarded as a clean
            # green transition and do not trigger a red warning either.
            if failed:
                self._flash('red', now, RED_HOLD_S)
            elif not micro:
                self._flash('green', now, GREEN_HOLD_S)
            else:
                self._pulse = None
                self._pulse_until = float('-inf')
        return self._appearance(now, completed)
