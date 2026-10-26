"""Advanced Trail Braking – live ACC coaching dashboard (Windows)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from dataclasses import replace
from pathlib import Path

import numpy as np
from PyQt5.QtCore import Qt, QTimer, QSettings
from PyQt5.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLabel, QMainWindow,
                             QMessageBox, QPushButton, QVBoxLayout, QWidget)
import pyqtgraph as pg

from acc_memory import ACCSharedMemory, acc_process_running
from demo_source import DemoSource
from advanced_engine import EventTracker, Feedback
from calibration_engine import calibrate_live
from coaching_engine import assess
from raw_event_store import encode_event
from stats_ui import BrakingStatsWindow
from mini_hud import MiniHUD
from hud_presentation import describe, POST_RELEASE_OBSERVATION_S
from hud_rhythm import HUDRhythm, HUDCommand
from corner_names import CornerCatalog, CornerNameGate, META_DIR, CONFIG_FILE
from acc_graphics_probe import GraphicsReader
from line_reference import FastlaneReference

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY = os.path.join(DATA_DIR, "braking_history.jsonl")
IMAGES = os.path.join(BASE_DIR, "images")


class TrailBrakingApp(QMainWindow):
    def __init__(self, mode: str = "demo"):
        super().__init__()
        self.mode = mode
        self.setWindowTitle(f"Advanced Trail Braking 0.3.1 | {mode.upper()} rotation coach")
        # Safety hotfix: do not force an overlay above the DirectX game.
        # Use normal desktop/windowed layout during initial validation.
        self.resize(550, 680)
        # Native Windows title bar: its normal minimize control is retained.
        # Detailed GUI stays on top ONLY when the user explicitly requests it.
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint |
                            Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.settings = QSettings('AdvancedTrailBraking', 'RotationCoach')
        self._hud_flow = HUDRhythm()
        self._early_exit_checked = False
        self.mini_hud = MiniHUD()  # independent top-level window, not a child
        self.mini_hud.visibilityChanged.connect(self._update_hud_button)
        central = QWidget()
        central.setObjectName('MainCentral')
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        window_controls = QHBoxLayout()
        self.btn_hud = QPushButton('Hide Mini HUD')
        self.btn_hud.setToolTip('Show, restore, or hide the independent transparent Mini HUD')
        self.btn_hud.clicked.connect(self.toggle_hud)
        window_controls.addWidget(self.btn_hud)
        self.btn_minimize_details = QPushButton('− Minimize details')
        self.btn_minimize_details.clicked.connect(self.showMinimized)
        window_controls.addWidget(self.btn_minimize_details)
        layout.addLayout(window_controls)
        self.check_on_top = QCheckBox('Keep detailed GUI on top')
        self.check_on_top.setToolTip('The main analysis window floats on top only while checked. Use ACC borderless/windowed mode for overlays.')
        self.check_on_top.setChecked(self.settings.value('detailsAlwaysOnTop', False, type=bool))
        self.check_on_top.toggled.connect(self.set_details_on_top)
        layout.addWidget(self.check_on_top)

        self.status = QLabel("SAFE DEMO – synthetic data only" if mode == "demo"
                             else "LIVE EXPERIMENTAL – waiting for ACC physics data")
        self.status.setStyleSheet("color: #dee6ee; background: #263746; padding: 7px;")
        layout.addWidget(self.status)
        self.corner_status = QLabel('Corner names: not configured (optional)')
        self.corner_status.setWordWrap(True)
        self.corner_status.setStyleSheet('color: #b0ccdf; padding: 3px;')
        layout.addWidget(self.corner_status)
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
        self._corner_reader = None
        self._corner_gate = None
        self._event_corner = None
        self._last_corner_status_at = 0.
        # This is OPTIONAL; no change to the working score, HUD rhythm, or
        # physics reader. No internet access during live driving.
        if self.mode == 'live':
            try:
                catalog = CornerCatalog.load()
                path_file = META_DIR / CONFIG_FILE
                if catalog is not None and path_file.is_file():
                    original_ai = Path(path_file.read_text(encoding='utf-8').strip())
                    reference = FastlaneReference.load_v8(original_ai)
                    if len(reference.xyz) != 5046:
                        raise ValueError('Not the validated Nurburgring 24h AI route')
                    self._corner_gate = CornerNameGate(catalog, reference)
                    self._corner_reader = GraphicsReader(acc_process_running)
                    self.corner_status.setText('Corner names: waiting for verified live alignment')
                else:
                    self.corner_status.setText('Corner names OFF: run download_corner_metadata.bat and configure_fastlane.bat')
            except (OSError, ValueError, TypeError) as exc:
                self.corner_status.setText(f'Corner names OFF: {exc}')
        else:
            self.corner_status.setText('Corner names: demo never attaches ACC graphics')
        self._offline_since = None
        self.tracker = EventTracker(post_seconds=POST_RELEASE_OBSERVATION_S)
        self.stats = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)
        self._last_draw = 0.0
        self.timer.start(40)  # 25Hz, reducing UI work during ACC tests.
        if self.check_on_top.isChecked():
            self.set_details_on_top(True)
        # No need to expose the full analysis panel during driving.
        self.mini_hud.clear_message()
        self.mini_hud.show()

    def _update_hud_button(self):
        if not self.mini_hud.isVisible():
            self.btn_hud.setText('Show Mini HUD')
        elif self.mini_hud.isMinimized():
            self.btn_hud.setText('Restore Mini HUD')
        else:
            self.btn_hud.setText('Hide Mini HUD')

    def toggle_hud(self):
        if not self.mini_hud.isVisible() or self.mini_hud.isMinimized():
            self.mini_hud.showNormal()
        else:
            self.mini_hud.hide()
        self._update_hud_button()

    def set_details_on_top(self, enabled: bool):
        self.settings.setValue('detailsAlwaysOnTop', bool(enabled))
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(enabled))
        # On Windows Qt needs to re-show after switching native window flags.
        self.show()
        if enabled:
            self.raise_()

    def _with_event_corner(self, message):
        # Captured at the release, not queried 2.6 seconds later.
        if self._event_corner is None:
            return message
        return replace(message, corner_name=self._event_corner.display_name)

    def _read_corner_position(self):
        if self._corner_gate is None or self._corner_reader is None:
            return
        now = time.monotonic()
        try:
            graphics = self._corner_reader.read()
            self._corner_gate.observe(graphics, now)
        except (OSError, ValueError, TypeError, OverflowError):
            self._corner_gate.reset()
        if now - self._last_corner_status_at > 1.5:
            self._last_corner_status_at = now
            self.corner_status.setText('Corner names: ' + self._corner_gate.status)

    def _apply_hud_command(self, command: HUDCommand):
        if command.kind == 'show' and command.message is not None:
            self.mini_hud.set_message(command.message)
        elif command.kind == 'clear':
            self.mini_hud.clear_message()

    def _maybe_revise_early_exit(self, sample):
        """Optional one-time refresh using measured 1.2s of exit telemetry.

        It remains an EARLY estimate, not the authoritative completed result.
        No scoring formula or raw event log is changed.
        """
        if self._early_exit_checked or self.tracker.state != 'exit':
            return
        if sample.time - self.tracker.release_time < 1.22:
            return
        self._early_exit_checked = True
        try:
            early = assess(tuple(self.tracker.samples), self.tracker.release_index,
                           phase='final')
            early_text = describe(early)
            if early.score == 5:
                # Short-lived, partial-exit evidence is not a final proof.
                from hud_presentation import HUDMessage
                early_text = HUDMessage(early_text.grade, 'Good exit so far',
                                        early_text.number_color, early_text.text_color)
            self._apply_hud_command(self._hud_flow.revise(self._with_event_corner(early_text), sample.time))
        except (ValueError, TypeError, OverflowError, FloatingPointError):
            pass

    def on_tick(self):
        sample = self.acc.read()
        if sample is None:
            if self.mode == "live":
                if self._offline_since is None:
                    self._offline_since = time.monotonic()
                elif time.monotonic() - self._offline_since > 3.0:
                    # Never blend event histories across lost ACC sessions.
                    self.tracker.reset()
                    self._apply_hud_command(self._hud_flow.reset())
                    self._early_exit_checked = False
                    if self._corner_gate is not None:
                        self._corner_gate.reset()
                    self._event_corner = None
                self.status.setText(self.acc.connect_error or "Waiting for ACC physics frame…")
            # A lost telemetry feed must not leave old feedback on screen.
            self._apply_hud_command(self._hud_flow.tick(time.monotonic()))
            return
        self._offline_since = None
        self._read_corner_position()
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
            if feedback.phase == "provisional":
                elapsed = (completed[0][-1].time - completed[0][0].time
                           if completed is not None and completed[0] else 0.0)
                self._event_corner = (self._corner_gate.candidate(time.monotonic())
                                      if self._corner_gate is not None else None)
                self._hud_flow.new_release(self._with_event_corner(describe(coach)), sample.time, elapsed)
                self._early_exit_checked = False
            if feedback.phase == "final":
                calibration = None
                # The detailed window/history gets the authoritative final
                # result. The glance HUD may UPDATE an existing notice, but
                # must never pop up a stale late result after the next corner.
                self._apply_hud_command(self._hud_flow.revise(self._with_event_corner(describe(coach)), sample.time))
                calibration = None
                if completed is not None:
                    try:
                        calibration = calibrate_live(feedback, *completed)
                    except (ValueError, TypeError, OverflowError, FloatingPointError):
                        # Preserve main coach result even if older shadow fails.
                        pass
                self.save_event(feedback, calibration, coach, completed)
        # Newest event wins. Never wait for a fully straight vehicle; a new
        # brake automatically hides the previous corner's short feedback.
        self._maybe_revise_early_exit(sample)
        self._apply_hud_command(self._hud_flow.tick(
            sample.time, braking_active=(self.tracker.state == 'braking')))
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
        if self._event_corner is not None:
            entry['corner'] = {'name': self._event_corner.display_name,
                               'turn_number': self._event_corner.number,
                               'source': 'RaceIQ experimental ACC segments',
                               'alignment': 'candidate; Windows validation pending'}
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
            self._apply_hud_command(self._hud_flow.reset())
            self._early_exit_checked = False
            self._event_corner = None
            if self._corner_gate is not None:
                self._corner_gate.reset()
            self.mini_hud.clear_message()
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
        if self._corner_reader is not None:
            self._corner_reader.close()
        self.mini_hud.close()
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
    parser = argparse.ArgumentParser(description="Advanced Trail Braking v0.3.1")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="Synthetic UI demo; never opens ACC memory")
    mode.add_argument("--live", action="store_true", help="Experimental read-only ACC integration")
    args = parser.parse_args()
    chosen_mode = "live" if args.live else "demo"  # fail-safe default
    app = QApplication(sys.argv[:1])
    # Scope dark fills to the analysis window. The Mini HUD must remain alpha.
    app.setStyleSheet("QWidget#MainCentral { background: #17232c; color: white; } "
                      "QMainWindow { background: #17232c; color: white; } "
                      "QPushButton { background: #334d62; color: white; padding: 9px; border-radius: 5px; } "
                      "QPushButton:hover { background: #466985; } "
                      "QCheckBox { color: white; }")
    window = TrailBrakingApp(mode=chosen_mode)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
