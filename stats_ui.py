"""Current stint stats; keeps legacy 1–5 history separate from advanced grades."""
import json
import os
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
import pyqtgraph as pg


class BrakingStatsWindow(QMainWindow):
    def __init__(self, history_file):
        super().__init__()
        self.history_file = history_file
        self.setWindowTitle("Advanced Trail Braking – Stint diagnostics")
        self.resize(620, 450)
        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        self.summary_label = QLabel("Reading…")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("background: #283d4b; color: white; padding: 12px;")
        layout.addWidget(self.summary_label)
        self.plot = pg.PlotWidget(background="#0c1117")
        self.plot.setLabel("bottom", "Advanced corner event number")
        self.plot.setLabel("left", "Heuristic grade (1–5)")
        self.plot.setYRange(0, 5.4)
        self.plot.showGrid(x=False, y=True, alpha=.25)
        layout.addWidget(self.plot)
        self.load_and_plot_data()

    def load_and_plot_data(self):
        self.plot.clear()
        if not os.path.exists(self.history_file):
            self.summary_label.setText("No events recorded yet. Start ACC and drive a few corners.")
            return
        rows = []
        try:
            with open(self.history_file, encoding="utf-8") as fp:
                for line in fp:
                    try:
                        row = json.loads(line)
                        if isinstance(row, dict):
                            rows.append(row)
                    except (ValueError, TypeError):
                        continue
        except OSError as exc:
            self.summary_label.setText(f"Cannot read log: {exc}")
            return
        advanced = [r for r in rows if r.get("mode") == "advanced" and r.get("phase") == "final"]
        graded = [r for r in advanced if isinstance(r.get('score'), int)]
        ungraded = len(advanced) - len(graded)
        legacy = sum(1 for r in rows if r.get("mode") != "advanced")
        original_points = [(i + 1, r['score']) for i, r in enumerate(advanced)
                           if isinstance(r.get('score'), int)]
        if original_points:
            x,y=map(np.array,zip(*original_points))
            for mask,color in ((y==5,'#31cc8a'),
                               ((y>=3)&(y<5),'#f1c40f'),
                               (y<3,'#e76a60')):
                if np.any(mask):
                    self.plot.addItem(pg.BarGraphItem(x=x[mask],height=y[mask],
                                                      width=.65,brush=pg.mkBrush(color)))
        coached_points = [(i + 1, r['coaching']['score'])
                          for i,r in enumerate(advanced)
                          if isinstance(r.get('coaching'),dict) and
                          isinstance(r['coaching'].get('score'),int)]
        if coached_points:
            x,y=map(np.array,zip(*coached_points))
            self.plot.plot(x,y,pen=None,symbol='o',symbolSize=10,
                           symbolBrush='#59b7ee',symbolPen=None)
        old_avg = f'{np.mean([r["score"] for r in graded]):.2f}' if graded else 'n/a'
        new_avg = (f'{np.mean([y for _,y in coached_points]):.2f}'
                   if coached_points else 'n/a')
        coasts = sum((r.get('coaching') or {}).get('label') == 'COASTING TO REVIEW'
                     for r in advanced)
        overlaps = sum((r.get('coaching') or {}).get('label') == 'HIGH BRAKE WHILE TURNING'
                       for r in advanced)
        self.summary_label.setText(
            f"0.2.4 advanced: {len(coached_points)} scored | Average: {new_avg}/5 (blue dots)\n"
            f"Legacy 0.2.2: {len(graded)} scored | Average: {old_avg}/5 (colored bars)\n"
            f"Legacy ungraded: {ungraded} | 0.2.4 coasting reviews: {coasts} | "
            f"high-brake turns: {overlaps}\n"
            f"Older non-advanced records: {legacy}\n"
            "A grade does not certify the fastest braking point or ideal racing line.")
