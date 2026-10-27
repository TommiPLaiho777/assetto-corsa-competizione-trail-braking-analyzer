# 0.2.5.2 – Rapid-corner Mini HUD

The previous Mini HUD waited for a 2.6-second finalized event **and** a sustained straight-ish interval. That resulted in stale grades in technical corner sequences.

## Display logic (no changes to ACC reader, scoring math, or saved history)

- A **provisional** 1–5 technique grade and one short diagnosis are eligible to appear around **0.16–0.20 seconds after brake release**, rather than waiting for the complete exit analysis or a straight road. The early preview usually tops out at **4**, because a 5 still requires observed exit progress.
- One **optional in-place update** after approximately **1.22 seconds** of observed exit may refine that grade if the same short notice is still visible. Even an early `5 – Good exit so far` is **not** proof of a fully successful corner.
- A normal notice remains visible approximately **1.35 seconds**, measured from when first shown; short braking events or a rapid sequence of braking releases shorten this to **0.90 seconds**. The absolute time from release is capped at **1.95 seconds**.
- When a new braking event begins, any previous Mini HUD number and diagnosis disappear. A late finalized result **never reappears over a later corner**.
- On expiry the **text and numeral clear automatically** without closing the independently movable transparent Mini HUD; its minimize/close buttons stay available.
- Detailed GUI and JSONL history retain the real end-of-exit grade after the usual **2.6-second** observation or when a new brake interrupts it. The preview is not written as a final grade. No historical logs are rewritten.

## Limitations

There is **no GPS/track position or apex classifier** here. A brake release is only a timing proxy for the end of a braking event, not proof that the geometric corner has ended. Because the Mini HUD is shown rapidly, **do not look at it until your eyes have a safe moment**. An early 4 or 5 may change when the full three-second event is reviewed. Do not drive to the HUD number.

## Validation

Tests in the repository cover fast sequences, automatic expiry, next-brake cancellation, no late reappearing final score, and in-place revision. The change has **not yet been live-tested on the user's Windows/ACC machine**. Test in `run_windows.bat` demo first; run `run_preflight_no_game.bat` with ACC closed. Then in an unimportant ACC practice stint if comfortable. `main` remains untouched until the PR is reviewed.
