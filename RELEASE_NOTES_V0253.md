# Advanced Trail Braking 0.2.5.3 — Mini HUD drag handle hotfix

- The existing rapid-corner HUD timing is **unchanged** (0.16 s preview scheduling,
  0.90/1.35 s typical hold, 1.95 s absolute expiry cap).
- A visible, small `≡` handle is always present on the transparent HUD. It
  retains a mouse hit area after the grade/diagnosis disappear.
- Dragging the handle moves the entire floating Mini HUD. Position is saved
  using the existing QSettings path. Visible number/text may still be dragged.
- The number and diagnosis remain borderless; a tinted background is used **only**
  for the tiny drag grip, not the feedback region.
- Existing `−` and `×` controls, detailed GUI, scores, files and graphics memory
  access behavior are unchanged.
- No racing-line scoring is included; the game physics reader is unchanged.
- Test first in the synthetic demo; the native Windows/ACC behavior is pending.
