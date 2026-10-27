# 0.3.1.1 – Mini HUD initialization fix

- Fix AttributeError during Qt HUD creation: the drag-handle event filter was enabled before number/feedback/corner_name were constructed.
- Install that event filter only after all referenced widgets exist; also guard early lifecycle events.
- No changes to HUD timing, corner evaluation, read-only memory readers, or scoring.
- Windows/ACC live verification still required.

## Applying to existing 0.3.1 installation

Exit only the Advanced Trail Braking Python app (ACC may stay open). Replace mini_hud.py in the installed 0.3.1 program folder with the corrected mini_hud.py from this package. Keep your existing .venv, data and metadata. Restart run_windows.bat first, then live if the demo works.
