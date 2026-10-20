## 0.2.5.1 follow-up
Mini HUD delivery latency reduced (post-release 2.6 s, continuous straight-ish gate 0.24 s); code-scoring heuristic/ACC memory mapping unchanged. 68 private user traces were replay-checked, but not committed. Live Windows validation remains necessary.

# Development branch: Advanced Trail Braking 0.2.4.1

This branch updates the original ACC trail braking analyzer to the v0.2.4.1 source-only test build.

## Scope
- Read-only ACC telemetry reader; uses `OpenFileMappingW` with FILE_MAP_READ and does not create a memory mapping.
- Two-stage scoring: immediate provisional grade and up to 3s exit review.
- Corrected brake-reapplication logic, counting only rises after initial peak pressure.
- Does not grade straight-line braking as unsuccessful trail braking.
- Separately records raw event telemetry for offline replay.
- Adds Windows/Linux GitHub Actions offline regression testing; live ACC compatibility requires human-controlled testing.

## Caution
- Do **not** merge until reviewed and Windows/ACC live-tested.
- Earlier builds caused crashes while loading a track. Keep the read-only ACC reader isolated; avoid changes to memory mapping until Windows regression tests pass.
- Archived driving-history JSONL and telemetry traces are **not** published for privacy reasons.
- If the original repository has old build artifacts, this branch does not delete their prior Git history.
