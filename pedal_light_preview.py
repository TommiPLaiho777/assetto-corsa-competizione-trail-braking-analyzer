"""Offline alpha HUD demo of the pedal light; NEVER reads ACC shared memory."""
from __future__ import annotations

import sys
import time

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from hud_presentation import HUDMessage
from mini_hud import MiniHUD
from pedal_overlap import PedalOverlapMonitor


def pedal_values(seconds):
    """Alternate overlapping and clean brake-to-gas transitions."""
    phase = seconds % 9.
    if phase < 1.0:
        return .0, .8
    if phase < 1.55:
        return .7, .65  # deliberately sustained overlap -> red
    if phase < 3.1:
        return .75, .0
    if phase < 4.3:
        return .0, .8
    if phase < 5.4:
        return .65, .0  # clean release -> green
    return .75, .0


def main():
    app = QApplication(sys.argv)
    hud = MiniHUD()
    hud.setWindowTitle('Pedal Overlap – OFFLINE PREVIEW (no ACC access)')
    hud.set_message(HUDMessage(4, 'Pedal light preview', '#A8EE74', '#FFB347', 'OFFLINE DEMO'))
    hud.show()
    monitor = PedalOverlapMonitor()
    start = time.monotonic()
    timer = QTimer(hud)

    def draw():
        now = time.monotonic()
        gas, brake = pedal_values(now - start)
        reading = monitor.update(gas, brake, now)
        hud.set_pedal_light(reading.color, reading.lit)

    timer.timeout.connect(draw)
    timer.start(40)
    return app.exec_()


if __name__ == '__main__':
    raise SystemExit(main())
