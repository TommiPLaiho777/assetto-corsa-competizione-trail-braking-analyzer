# 0.2.5.3 - Persistent Mini HUD drag grip

The proven 0.2.5.2 rapid-corner timings, assessment rules, telemetry reader, and
logging are unchanged. An unobtrusive `≡` drag grip now remains clickable at
the top-left of the fully transparent Mini HUD even after the score and comment
expire. Drag the grip with the left mouse button to reposition the HUD, or drag
visible score/comment text as before. The grip is the only control with a tiny
semi-opaque hit-test background; the score and feedback remain unboxed. The
position is still saved by Qt. `−` and `×` continue to work independently.

**Not included:** track position, apex detection or a racing-line grade. Those
need separately validated read-only ACC graphics telemetry and comparison
with matching laps. Do not label steering-only data as a missed apex.

No native Windows/ACC user test of this particular drag fix has yet occurred.
Test the grip in `run_windows.bat` demo before opening ACC, ideally while the
number/comment are empty after automatic expiry.

---

**0.2.5.1 QUICK HUD UPDATE:** The Mini HUD keeps exactly the same appearance, drag placement, independent minimize/close and message colors. The final-score observation is shortened from 3.0 to 2.6 seconds, and the steady straight-ish display gate is shortened from 0.48 to 0.24 seconds (steer/yaw/brake/speed safety thresholds unchanged). In the 68 privately supplied ACC braking events, offline recalculation with 2.6 seconds preserved all 68 previous 0.2.5 scores. This is empirical evidence only, not a guarantee for future corners. The same 0.2.4.1 scoring rules and same read-only ACC memory reader are retained. The HUD still waits for straight-ish driving and may be delayed on winding sections.

**0.2.5 UPDATE:** A transparent Mini HUD and optional always-on-top detailed window have been added. Scoring and ACC memory handling are unchanged. Full information in the 0.2.5 section below.

**HOTFIX 0.2.4.1 (retained):** New empirical raw logs exposed a serious 0.2.4 scoring bug: normal initial brake application was counted as repeated brake reapplications, unfairly reducing trail grades. The fix counts pressure rises only after the event's initial peak brake pressure. The ACC memory reader, game integration and existing data format remain unchanged. Old 0.2.4 raw logs can be replayed offline using `run_replay_offline.bat`; old history records are never overwritten. A better grade does not prove a faster corner.

# Advanced Trail Braking 0.2.5.1 — Faster Mini HUD (0.2.4.1 scoring hotfix retained)

**Windows Python source test build — not an EXE.** This revision is based on the user's
working 0.2.3, and the user reports that the **0.2.5 Mini HUD worked well in ACC live driving**. However, the shortened timing in **0.2.5.1 still needs a Windows/ACC smoke test**. Do not initially test it during an important race session.

## What's changed

- **New primary 0.2.4.1 grade (1–5)** appears **immediately after brake release**
  as provisional. It is revised after up to **2.6 seconds** of post-release
  observation. Old 0.2.2 grade stays separately visible as **Legacy**.
- Evaluates real brake-pressure taper *while steering and yaw are present*,
  sustained measured rotation, high brake/steer overlap, excessive yaw reversal,
  brake reapplications, neutral-pedal coasting and observed early exit progress.
- A 5 requires **multiple independent signals**: controlled release, stable yaw,
  low excessive high-brake/steer overlap, low coasting and some acceleration after
  release. These are **heuristics, not proof of the fastest corner**.
- **Straight-line braking or braking completed before turning: NOT GRADED** as
  trail braking. These techniques may be correct in many corners.
- Extends look-ahead from ~1.2 s to **2.6 s**, so it can detect some previously
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

## 0.2.5 — Mini HUD / optional always-on-top detailed window

The **independent Mini HUD** is a **borderless alpha-transparent text-only window**.
There is no boxed background and it displays just a bold single-digit grade
and a short color-coded diagnosis, plus small `−` minimize and `×` close
controls. It can be moved by dragging the number or phrase. The last position
is remembered per Windows user via QSettings. No flashing, sounds, or notifications.

- **Grade palette:** 5 green, 4 light green, 3 orange, 2 orange-red, 1 red.
  The brief diagnosis has its **own** color (green/good; orange/review;
  red/important problem); `–` means **not graded**, not a score of zero.
- **Timing:** the Mini HUD shows the **final** event only after approximately
  half a second of sustained low steering, low yaw and released brake at normal
  driving speed. It deliberately does not show provisional grades during a
  corner. A result may remain pending if the car never reaches those criteria.
  A delay is only an attention-reduction aid, not a determination of safety.
- **Detailed GUI:** normal Windows minimize button is kept. A checkbox toggles
  `Keep detailed GUI on top` **on demand**. The detailed window can be minimized
  or left visible independently of the Mini HUD. `Show/Restore/Hide Mini HUD`
  is available in that window, so Mini HUD `×` never stops telemetry analysis.
- **Overlay compatibility:** for an on-top window over ACC, ACC should be in
  *borderless windowed* or windowed display mode. Windows/DirectX exclusive
  fullscreen can cover desktop overlays; this is not a Python failure.
- **Racing line / apex:** *not implemented*. This app does **not** read track
  position, coordinates, or surface geometry. It will **not** claim “missed
  apex” from steering or yaw alone. Such feedback needs a separate validated
  track-position data source and repeated corner comparison.
- **Game safety:** `acc_memory.py`, coaching algorithms and event-log schemas
  remain **byte-for-byte unchanged** from 0.2.4.1. Only UI presentation and
  offline tests/documentation change. Live Windows overlay not yet verified.

For the first trial, close ACC, run `run_preflight_no_game.bat` and then
`run_windows.bat` (synthetic demo). Check separately that the Mini HUD `−`, `×`,
show/restore button, drag and detailed-window on-top checkbox work. Then start
ACC first, load onto the track, and only then use
`run_live_after_acc_loaded.bat` to test the read-only reader cautiously.
Do not interrupt unrelated Python or Rhino background processes.

### Publishing to existing GitHub Draft PR #1

After offline smoke validation, run `update_existing_pr.bat` in this folder.
It clones the existing `dev/advanced-trail-braking-v0.2.4.1` branch
into a new uniquely named working copy, stages only the 0.2.5 UI files
and its documentation/tests, makes one commit, and updates the same
[Draft PR #1](https://github.com/TommiPLaiho777/assetto-corsa-competizione-trail-braking-analyzer/pull/1).
Requires Git and your own GitHub credentials. **No force push, no main merge,
no edits to the ACC reader.** Existing working copies remain untouched.

## Cockpit-style position

The Mini HUD can be moved by dragging the number or diagnosis. Put it over a
low-distraction cockpit/instrument-panel area of the display, not where it blocks
the next braking reference or apex. Its position persists through QSettings.
The mini window has its own minimize and close controls; reopen from the full
GUI. The detailed GUI may stay minimized during driving.

## 0.2.5.2 – Rapid-corner glance HUD

The Mini HUD now displays a **short-lived provisional result** soon after brake
release (typically ~0.2 s), not 2.6+ seconds after the event. It may update
**in place** after early exit evidence, but the full coaching result and logs
remain authoritative. It clears in approximately 0.9–1.35 s (and no later
than 1.95 s after release), or immediately when another braking event starts.
No late final result pops up during a following corner. The Mini HUD frame,
alpha background, small minimize/close buttons, and optional always-on-top
detailed window are unchanged. See `RELEASE_NOTES_V0252.md` for detail.

*Important:* An early score is provisional and must not be mistaken for
proof of corner exit, apexs or fastest racing line. Watch the road, then
inspect the number only when attention permits. The earlier sections above
refer to the archived 0.2.5/0.2.5.1 presentation behavior.

## Optional text-only Line Coach research

See [`LINE_COACH_RESEARCH_FI.md`](LINE_COACH_RESEARCH_FI.md). This experimental
module reads ACC's graphics **read-only** and measures the car's distance from
a locally installed `fastlane.ai` AI reference. **It has not been validated
on the user's Windows ACC and is NOT wired into Mini HUD scoring or timing.**
No graphical racing-line display is added. No ACC game assets are redistributed.


## 0.3.1 – optional Nürburgring 24h corner names (experimental)

Adds only a brief corner label to the existing Mini HUD (example **BERGWERK**)
when the app can match repeated ACC read-only graphics coordinates to the
locally installed `fastlane.ai` and RaceIQ segment fractions. The original
0.2.5.2 rapid-corner timing, braking grades, ACC physics reader, and Mini HUD
transparent surface / drag grip are unchanged. If the named turn cannot be
validated at the instant of brake release, the score and normal short feedback
appear **without a corner name**. No apex or optimal-line claims are made.

To opt in after extracting to a NEW Windows folder:

1. `install_windows.bat` and `run_preflight_no_game.bat` with ACC closed.
2. `download_corner_metadata.bat`: obtains two small, external RaceIQ JSON files
   to the ignored local `data\track_metadata` folder; automatic network access
   occurs **only when running this script**, not during the game. Alternatively
   manually place `nordschleife.json` and `nordschleife-segments.json` there.
3. Drag your existing ACC Nürburgring 24h `fastlane.ai` onto
   `configure_fastlane.bat`. Only its absolute path is stored. The original
   game asset is never copied, edited or redistributed.
4. With ACC already on the Nürburgring 24h circuit, try
   `run_live_after_acc_loaded.bat`. The detailed window reports whether name
   alignment has enough evidence. Keep the working v0.2.5.3 folder untouched.
5. A named event can add an optional `corner` object to the history JSONL,
   including the turn number and **experimental** source attribution. It does
   not modify legacy, calibration or coaching scores.

The external metadata is maintained by RaceIQ and licensed separately under
its repository license (GNU GPL-3.0); it is NOT redistributed in this ZIP or
included in the GitHub PR. References:
- https://github.com/SpeedHQ/RaceIQ/blob/main/shared/data/tracks/meta/nordschleife.json
- https://github.com/SpeedHQ/RaceIQ/blob/main/shared/data/tracks/acc/nordschleife-segments.json

Known limits: RaceIQ's segments are third-party, not confirmed official ACC
turn ranges. Actual ACC graphics offsets, lap progress and reference alignment
have **not yet been validated** on the user's Windows ACC. Automatic gating is
only an initial check, not proof that each name is correct. A 90-second
`run_line_probe_live.bat` CSV from Windows is still required to validate and
calibrate name placement before considering the feature production-ready.
If imported files are absent/bad, ACC graphics cannot be read, or the position
registration differs, the feature fails closed and ordinary HUD stays working.
