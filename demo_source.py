"""Synthetic telemetry for UI-only smoke tests. Does not access the game."""
from __future__ import annotations
import math
import time
from advanced_engine import TelemetrySample


class DemoSource:
    connect_error = ''
    def __init__(self):
        self.started = time.monotonic()
        self.last_frame = -1

    def read(self):
        now = time.monotonic()
        frame = int((now - self.started) * 25)
        if frame == self.last_frame:
            return None
        self.last_frame = frame
        phase = (frame % 180) / 25.0
        if phase < 0.8:
            brake, steer, yaw, throttle = .95, .015, .005, 0.
            speed = 210 - phase * 30
        elif phase < 2.4:
            u = (phase - .8) / 1.6
            brake = max(0., .95 * (1-u))
            steer = .05 + .23 * u
            yaw = .025 + .22 * u
            throttle = 0.
            speed = 186 - u*75
        elif phase < 3.7:
            brake, steer, yaw, throttle = 0., .28, .22, .40
            speed = 112 + (phase-2.4)*12
        else:
            brake, steer, yaw, throttle = 0., 0., 0., .85
            speed = 140
        return TelemetrySample(now, frame+1, speed, brake, throttle, steer, yaw)

    def close(self):
        pass
