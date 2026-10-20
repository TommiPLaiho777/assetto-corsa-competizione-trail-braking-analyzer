**HOTFIX 0.2.4.1:** New empirical raw logs exposed a serious 0.2.4 scoring bug: normal initial brake application was counted as repeated brake reapplications, unfairly reducing trail grades. The fix counts pressure rises only after the event's initial peak brake pressure. The ACC memory reader, game integration and existing data format remain unchanged. Old 0.2.4 raw logs can be replayed offline using `run_replay_offline.bat`; old history records are never overwritten. A better grade does not prove a faster corner.

# Advanced Trail Braking 0.2.4.1 — brake reapplication scoring hotfix

**Windows Python source test build — not an EXE.** This revision is based on the user's
working 0.2.3, which reportedly ran ACC without crashes. However, **0.2.4 itself has
not been live-verified on this machine**. Do not use on an important race session.

## What's changed

- **New primary 0.2.4.1 grade (1–5)** appears **immediately after brake release**
  as provisional. It is revised after up to **3.0 seconds** of post-release
  observation. Old 0.2.2 grade stays separately visible as **Legacy**.
- Evaluates real brake-pressure taper *while steering and yaw are present*,
  sustained measured rotation, high brake/steer overlap, excessive yaw reversal,
  brake reapplications, neutral-pedal coasting and observed early exit progress.
- A 5 requires **multiple independent signals**: controlled release, stable yaw,
  low excessive high-brake/steer overlap, low coasting and some acceleration after
  release. These are **heuristics, not proof of the fastest corner**.
- **Straight-line braking or braking completed before turning: NOT GRADED** as
  trail braking. These techniques may be correct in many corners.
- Extends look-ahead from ~1.2 s to **3 s**, so it can detect some previously
  hidden coasting. If another brake starts sooner, evidence is incomplete and
  grade 5 should not be awarded based solely on rotation.
- Low-speed/stopping events are excluded without claiming a collision/damage
  diagnosis. A damaged car should be repaired, not coached through damage.
- New `data/raw_braking_events.jsonl` stores only telemetry from each braking
  event, separately from `data/braking_history.jsonl`, to permit offline replay
  and future calibration **without driving again**. No screenshot autosaves.
- `score` in history remains the **original 0.2.2 grade**; `calibration` is
  **old 0.2.3 shadow**; `coaching` contains **new 0.2.4**. Data schemas do not mix.
- **The ACC shared memory reader (`acc_memory.py`) is byte-identical to 0.2.3.**
  It does not create named memory sections, uses read access only, and attaches
  only on explicit live mode with an ACC process guard. No game controls/inputs.

## Installation and careful Windows validation

1. **Leave 0.2.3 unchanged**. Close the older Trail Braking window and extract
   this ZIP into a **separate folder**. No reboot is required; do not stop other
   Python / Rhino automation jobs.
2. Run `install_windows.bat` (private `.venv` only; requires Windows Python 3.11
   or 3.12 x64). Installation may require internet for dependencies.
3. With **ACC closed**, run `run_preflight_no_game.bat`. All tests must pass.
4. With **ACC closed**, run `run_windows.bat` for a synthetic UI demonstration.
5. Only if both succeed and you accept the possibility of a game crash: open
   ACC normally, let a practice session finish loading, then run
   `run_live_after_acc_loaded.bat`. Remain in the pits initially and stop on
   any instability. The software does **not** launch ACC.

## Reviewing/archiving logs

- `data/braking_history.jsonl`: event overview, original+shadow+new grades.
- `data/raw_braking_events.jsonl`: replayable **actual brake/steer/yaw samples**;
  this may grow over time and is separate to keep the stats window responsive.
- `run_replay_offline.bat`: re-evaluate 0.2.4 events *offline* from raw data.
- `run_history_comparison.bat`: legacy 0.2.2 vs 0.2.3 shadow (archived metrics).
  **Past 0.2.3 logs do not contain raw time series, and cannot be evaluated
  reliably using 0.2.4 without inventing missing telemetry.**
- Personal reference driving logs and replay reports are intentionally excluded from the public repository.
  Supply local logs to the offline comparison tools when needed.
- 'Archive & New Stint' archives overview history; it archives the
  raw replay log under the same timestamp to preserve per-stint pairing.

## Limits and safety

Car/steering setup, yaw sign conventions, corner geometry, grip, conditions,
minimum speed, track position and true exit time are not known sufficiently to
certify the ideal line or prove yaw was caused by braking. Small observed speed
gains do not prove a faster corner. The feedback is a coaching suggestion only.

`python -m unittest discover -s tests -p "test_*.py"` runs the offline tests.
Windows-only memory tests are skipped when run outside Windows.
