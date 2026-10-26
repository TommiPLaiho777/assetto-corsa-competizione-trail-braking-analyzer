# Line Coach text research — optional add-on, not a released HUD feature

- Adds read-only `Local\\acpmf_graphics` probe; no write/create mapping calls.
- Extracts ACC v8 fastlane geometry from the user's **own local game asset**;
  no copyrighted ACC track data distributed.
- Computes XZ-line segment deviations with a Y-height gate and identifies
  the player's coordinates using `playerCarID` matched against `carID[]`.
- Emits only conservative text and a private CSV for offline validation.
- **Not integrated into Mini HUD yet**; HUD timing, existing scoring, and
  physics reader remain unchanged.
- Validate actual graphics layout and track coordinates on the user's Windows
  ACC before activating any line quality/coaching judgments.
