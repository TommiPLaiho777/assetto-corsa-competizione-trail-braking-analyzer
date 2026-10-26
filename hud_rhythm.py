"""Offline-only, deterministic Mini HUD timing for quick sequential corners.

The score is calculated elsewhere and remains explicitly provisional until the
normal post-release analysis. This module neither reads ACC nor grades driving.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from hud_presentation import HUDMessage

# Polling is nominally 25 Hz: a preview appears about 0.16-0.20 s after release.
PREVIEW_DELAY_S = 0.16
NORMAL_HOLD_S = 1.35
FAST_HOLD_S = 0.90
RAPID_RELEASE_GAP_S = 4.0
SHORT_BRAKING_S = 1.0
# A single in-place upgrade from exit evidence may receive a small reading window.
MIN_UPDATED_READING_S = 0.48
# Never leave a card on-screen for an entire straight.
MAX_FROM_RELEASE_S = 1.95


@dataclass(frozen=True)
class HUDCommand:
    kind: str  # 'show', 'clear', or 'none'
    message: Optional[HUDMessage] = None


NONE = HUDCommand('none')
CLEAR = HUDCommand('clear')


class HUDRhythm:
    """Single-slot, newest-event-wins HUD schedule; no delayed stale popups.

    Call `new_release()` for the preliminary post-release grade; `revise()`
    for post-release evidence; and `tick()` for each live sample. All `time`
    arguments use the monotonic clock shared by telemetry samples.

    A final result is never allowed to resurrect a hidden/expired notice.
    The full detail window and history always keep their own final result.
    """
    def __init__(self):
        self._pending: Optional[HUDMessage] = None
        self._active: Optional[HUDMessage] = None
        self._release_at: Optional[float] = None
        self._expires_at: Optional[float] = None
        self._last_release_at: Optional[float] = None
        self._hold_s = NORMAL_HOLD_S
        self._blocked = False

    def reset(self) -> HUDCommand:
        had = self._pending is not None or self._active is not None
        self._pending = None
        self._active = None
        self._release_at = None
        self._expires_at = None
        self._last_release_at = None
        self._blocked = False
        return CLEAR if had else NONE

    def new_release(self, message: HUDMessage, at: float,
                    braking_duration: float = 0.0) -> None:
        fast_rhythm = (self._last_release_at is not None and
                       0 < at - self._last_release_at < RAPID_RELEASE_GAP_S)
        short_event = 0 < braking_duration < SHORT_BRAKING_S
        self._hold_s = FAST_HOLD_S if fast_rhythm or short_event else NORMAL_HOLD_S
        self._last_release_at = at
        self._release_at = at
        self._expires_at = None
        self._pending = message
        self._active = None
        self._blocked = False

    def revise(self, message: HUDMessage, at: float) -> HUDCommand:
        """Update one already displayed result; never show a long-late final."""
        if self._blocked or self._release_at is None:
            return NONE
        if at < self._release_at or at >= self._release_at + MAX_FROM_RELEASE_S:
            return NONE
        if self._pending is not None:
            self._pending = message
            return NONE
        if self._active is not None and self._expires_at is not None and at < self._expires_at:
            self._active = message
            self._expires_at = min(self._release_at + MAX_FROM_RELEASE_S,
                                   max(self._expires_at, at + MIN_UPDATED_READING_S))
            return HUDCommand('show', message)
        return NONE

    def tick(self, at: float, braking_active: bool = False) -> HUDCommand:
        if braking_active:
            visible = self._active is not None
            self._active = None
            self._pending = None
            self._expires_at = None
            self._blocked = True
            return CLEAR if visible else NONE
        if self._pending is not None and self._release_at is not None:
            if at >= self._release_at + PREVIEW_DELAY_S:
                msg = self._pending
                self._pending = None
                self._active = msg
                self._expires_at = min(self._release_at + MAX_FROM_RELEASE_S,
                                       at + self._hold_s)
                return HUDCommand('show', msg)
        if self._active is not None and self._expires_at is not None and at >= self._expires_at:
            self._active = None
            self._expires_at = None
            self._blocked = True
            return CLEAR
        return NONE
