# Advanced Trail Braking 0.3.1 — Opt-in Nürburgring corner names

- Add external RaceIQ name/segment downloader (no JSON files redistributed).
- Add fail-closed corner name resolver using read-only graphics coordinates, race-progress + user's own fastlane.ai.
- Show experimentally aligned name in separate small text label in the existing Mini HUD; preserve grade, message, 0.2.5.2 quick timing, drag controls and native minimize/close.
- Record the name and source in optional corner history metadata only when aligned.
- Score algorithm, ACC physics reader and timing module unchanged.
- Live validation pending on Windows. Keep PR #1 draft until tested.
