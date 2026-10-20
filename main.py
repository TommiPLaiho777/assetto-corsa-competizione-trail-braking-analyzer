"""Advanced Trail Braking – live ACC coaching dashboard (Windows)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow,
                             QMessageBox, QPushButton, QVBoxLayout, QWidget)
import pyqtgraph as pg

from acc_memory import ACCSharedMemory, acc_process_running
from demo_source import DemoSource
from advanced_engine import EventTracker, Feedback
from calibration_engine import calibrate_live
from coaching_engine import assess
from raw_event_store import encode_event
from stats_ui import BrakingStatsWindow

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY = os.path.join(DATA_DIR, "braking_history.jsonl")
IMAGES = os.path.join(BASE_DIR, "images")


class TrailBrakingApp(QMainWindow):
    def __init__(self, mode: str = "demo"):
        super().__init__()
        self.mode = mode
        self.setWindowTitle(f"Advanced Trail Braking 0.2.4.1 | {mode.upper()} rotation coach")
        # Safety hotfix: do not force an overlay above the DirectX game.
        # Use normal desktop/windowed layout during initial validation.
        self.resize(550, 680)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.status = QLabel("SAFE DEMO – synthetic data only" if mode == "demo"
                             else "LIVE EXPERIMENTAL – waiting for ACC physics data")
        self.status.setStyleSheet("color: #dee6ee; background: #263746; padding: 7px;")
        layout.addWidget(self.status)
        self.rating = QLabel("– / 5")
        self.rating.setAlignment(Qt.AlignCenter)
        self.rating.setStyleSheet("font-size: 36px; font-weight: 700; color: #f1c40f;")
        layout.addWidget(self.rating)
        self.diagnosis = QLabel("ADVANCED: Brake + Steering + Measured Yaw")
        self.diagnosis.setAlignment(Qt.AlignCenter)
        self.diagnosis.setStyleSheet("font-weight: 700; font-size: 15px; color: white;")
        layout.addWidget(self.diagnosis)
        self.detail = QLabel("Advanced grade: measured braking, turn-in and rotation. Exit observation follows.")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("color: #cbd6de; padding: 6px;")
        layout.addWidget(self.detail)

        # Primary 0.2.4 coaching: immediate preliminary grade, refined after exit.
        # Legacy 0.2.2 and 0.2.3 shadow are logged separately for comparison.
        self.coaching_status = QLabel("ADVANCED 0.2.4.1: waiting for first braking event")
        self.coaching_status.setWordWrap(True)
        self.coaching_status.setStyleSheet("background: #253b49; color: #bfe5fb; padding: 9px;")
        layout.addWidget(self.coaching_status)
        self.legacy_status = QLabel("Legacy 0.2.2: no event yet")
        self.legacy_status.setStyleSheet("color: #9dafbd; padding: 5px;")
        layout.addWidget(self.legacy_status)

        self.path_plot = pg.PlotWidget(background="#080d12")
        self.path_plot.setLabel("bottom", "Absolute steering input", units="%")
        self.path_plot.setLabel("left", "Brake pedal", units="%")
        self.path_plot.setXRange(0, 100, padding=0)
        self.path_plot.setYRange(0, 100, padding=0)
        self.path_plot.setMouseEnabled(x=False, y=False)
        self.path_plot.showGrid(x=True, y=True, alpha=.20)
        self.path_trace = self.path_plot.plot(pen=pg.mkPen("#35d19b", width=2.5))
        layout.addWidget(self.path_plot, stretch=2)

        self.yaw_plot = pg.PlotWidget(background="#080d12")
        self.yaw_plot.setLabel("bottom", "Event time", units="s")
        self.yaw_plot.setLabel("left", "Measured yaw rate", units="deg/s")
        self.yaw_plot.setMouseEnabled(x=False, y=False)
        self.yaw_plot.showGrid(x=True, y=True, alpha=.20)
        self.yaw_trace = self.yaw_plot.plot(pen=pg.mkPen("#52a8f2", width=2.5))
        layout.addWidget(self.yaw_plot, stretch=1)

        row = QHBoxLayout()
        self.btn_stats = QPushButton("Event Statistics")
        self.btn_stats.clicked.connect(self.show_stats)
        self.btn_reset = QPushButton("Archive & New Stint")
        self.btn_reset.clicked.connect(self.archive_stint)
        row.addWidget(self.btn_stats)
        row.addWidget(self.btn_reset)
        layout.addLayout(row)

        # Only explicit --live can instantiate a Windows mapping reader.
        self.acc = (ACCSharedMemory(process_guard=acc_process_running)
                    if self.mode == "live" else DemoSource())
        self._offline_since = None
        self.tracker = EventTracker(post_seconds=3.0)
        self.stats = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)
        self._last_draw = 0.0
        self.timer.start(40)  # 25Hz, reducing UI work during ACC tests.

    def on_tick(self):
        sample = self.acc.read()
        if sample is None:
            if self.mode == "live":
                if self._offline_since is None:
                    self._offline_since = time.monotonic()
                elif time.monotonic() - self._offline_since > 3.0:
                    # Never blend event histories across lost ACC sessions.
                    self.tracker.reset()
                self.status.setText(self.acc.connect_error or "Waiting for ACC physics frame…")
            return
        self._offline_since = None
        prefix = "SYNTHETIC DEMO" if self.mode == "demo" else "ACC LIVE (EXPERIMENTAL)"
        self.status.setText(f"{prefix} | {sample.speed_kph:.0f} km/h | "
                            f"Brake {sample.brake * 100:.0f}% | "
                            f"Yaw {np.degrees(sample.yaw_rate):+.1f}°/s")
        updates = self.tracker.update(sample)
        for feedback in updates:
            # 0.2.2 immediate feedback and live ACC reader are unchanged.
            # New math runs AFTER the reader/tracker have produced an event.
            completed = (self.tracker.last_completed_event if feedback.phase == "final"
                         else (tuple(self.tracker.samples), self.tracker.release_index))
            coach = None
            if completed is not None:
                try:
                    coach = assess(*completed, phase=feedback.phase, legacy=feedback)
                except (ValueError, TypeError, OverflowError, FloatingPointError) as exc:
                    self.coaching_status.setText(f"Coaching unavailable: {exc}")
            self.show_feedback(feedback, coach)
            if feedback.phase == "final":
                calibration = None
                if completed is not None:
                    try:
                        calibration = calibrate_live(feedback, *completed)
                    except (ValueError, TypeError, OverflowError, FloatingPointError):
                        # Preserve main coach result even if older shadow fails.
                        pass
                self.save_event(feedback, calibration, coach, completed)
        # Live plots are throttled independently of telemetry capture.
        now = time.monotonic()
        if now - self._last_draw >= 0.12:
            self.draw_live_event()
            self._last_draw = now

    def draw_live_event(self):
        points = self.tracker.samples
        if not points:
            return  # Keep completed event visible during idle; do not erase instant feedback.
        x = np.fromiter((abs(s.steer) * 100 for s in points), float)
        y = np.fromiter((s.brake * 100 for s in points), float)
        yaw = np.fromiter((np.degrees(s.yaw_rate) for s in points), float)
        t = np.fromiter((s.time - points[0].time for s in points), float)
        # A genuine percentage axis, not per-corner re-normalization to 100%.
        # Auto-extend the *display range* if large steering is observed.
        self.path_plot.setXRange(0, max(35., float(np.ceil(max(x) / 10.) * 10.)), padding=0)
        self.path_trace.setData(x, y)
        self.yaw_trace.setData(t, yaw)

    def show_feedback(self, feedback: Feedback, coaching=None):
        old_grade = "–" if feedback.score is None else str(feedback.score)
        self.legacy_status.setText(
            f"Legacy 0.2.2: {old_grade}/5 | {feedback.label} (comparison only)")
        grade = "–" if coaching is None or coaching.score is None else str(coaching.score)
        prefix = "IMMEDIATE / PROVISIONAL" if feedback.phase == "provisional" else "POST-RELEASE REVIEW"
        self.rating.setText(f"{grade} / 5  ·  {prefix}")
        self.diagnosis.setText(coaching.label if coaching else "ANALYSIS UNAVAILABLE")
        if coaching is None:
            self.detail.setText("Telemetry event received, but coaching calculation failed.")
            return
        e = coaching.evidence
        detail = (f"Turning on brake: {e.get('turn_during_brake_s', 0):.2f}s | "
                  f"Brake taper: {e.get('brake_taper_pct', 0):.0f}% | "
                  f"Coast: {e.get('coasting_after_release_s', 0):.2f}s\n"
                  f"{coaching.explanation}")
        self.detail.setText(detail)
        self.coaching_status.setText(
            f"ADVANCED 0.2.4.1 | Evidence: {coaching.confidence} | "
            f"{'Exit progress observed' if e.get('exit_verified') else 'Exit not yet verified'}\n"
            "A coaching estimate, not proof of the fastest line.")
        color = ("#b8c2cc" if coaching.score is None else
                 "#37d58e" if coaching.score >= 5 else
                 "#f1c40f" if coaching.score >= 3 else "#e76e62")
        self.rating.setStyleSheet(f"font-size: 29px; font-weight: 700; color: {color};")

    def save_event(self, feedback: Feedback, calibration=None, coaching=None, completed=None):
        destination = os.path.join(BASE_DIR, "demo_data") if self.mode == "demo" else DATA_DIR
        history = os.path.join(destination, "braking_history.jsonl")
        os.makedirs(destination, exist_ok=True)
        name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        entry = feedback.as_log()
        # Compatibility: legacy and 0.2.3 scores are NEVER replaced.
        if calibration is not None:
            entry["calibration"] = calibration.as_log()
        if coaching is not None:
            entry["coaching"] = coaching.as_log()
        entry["timestamp"] = name
        try:
            with open(history, "a", encoding="utf-8") as fp:
                fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            self.status.setText(f"Could not save event: {exc}")
        # Capture actual time series separately for future OFFLINE re-grading.
        # No screenshots, no writes to game memory, no data from other apps.
        if completed is not None:
            try:
                event_samples, release_idx = completed
                raw = encode_event(name, event_samples, release_idx)
                raw_file = os.path.join(destination, "raw_braking_events.jsonl")
                with open(raw_file, "a", encoding="utf-8") as fp:
                    fp.write(json.dumps(raw, ensure_ascii=False) + "\n")
            except (OSError, ValueError, TypeError) as exc:
                self.status.setText(f"Could not save offline replay trace: {exc}")
        if self.stats is not None and self.stats.isVisible():
            self.stats.load_and_plot_data()

    def archive_stint(self):
        if QMessageBox.question(self, "New Stint", "Archive the existing log and start a new stint?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            target = os.path.join(BASE_DIR, "demo_data") if self.mode == "demo" else DATA_DIR
            history = os.path.join(target, "braking_history.jsonl")
            os.makedirs(target, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if os.path.exists(history):
                os.replace(history, os.path.join(target, f"braking_history_{stamp}.jsonl"))
            raw = os.path.join(target, "raw_braking_events.jsonl")
            if os.path.exists(raw):
                os.replace(raw, os.path.join(target, f"raw_braking_events_{stamp}.jsonl"))
            self.tracker.reset()
            self.rating.setText("– / 5")
            self.diagnosis.setText("NEW STINT")
            self.detail.setText("Previous event log archived safely in data/.")
            self.coaching_status.setText("ADVANCED 0.2.4.1: waiting for completed event")
            self.legacy_status.setText("Legacy 0.2.2: no event yet")
            self.path_trace.setData([], [])
            self.yaw_trace.setData([], [])
            if self.stats is not None:
                self.stats.load_and_plot_data()
        except OSError as exc:
            QMessageBox.warning(self, "Archive failed", str(exc))

    def closeEvent(self, event):
        self.timer.stop()
        self.acc.close()
        super().closeEvent(event)

    def show_stats(self):
        if self.stats is None:
            source = (os.path.join(BASE_DIR, "demo_data", "braking_history.jsonl")
                      if self.mode == "demo" else HISTORY)
            self.stats = BrakingStatsWindow(history_file=source)
        self.stats.load_and_plot_data()
        self.stats.show()
        self.stats.raise_()


def main():
    parser = argparse.ArgumentParser(description="Advanced Trail Braking v0.2.4")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="Synthetic UI demo; never opens ACC memory")
    mode.add_argument("--live", action="store_true", help="Experimental read-only ACC integration")
    args = parser.parse_args()
    chosen_mode = "live" if args.live else "demo"  # fail-safe default
    app = QApplication(sys.argv[:1])
    app.setStyleSheet("QWidget { background: #17232c; color: white; } "
                      "QPushButton { background: #334d62; padding: 9px; border-radius: 5px; } "
                      "QPushButton:hover { background: #466985; }")
    window = TrailBrakingApp(mode=chosen_mode)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
