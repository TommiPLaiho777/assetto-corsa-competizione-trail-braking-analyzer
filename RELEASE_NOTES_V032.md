# 0.3.2 – Modular Pedal Overlap Light

- Adds a small unboxed blinking dot **beside the Mini HUD score/feedback**.
- **RED pulse** when throttle >2% and brake >2% overlap continuously for >=0.15 seconds during a braking event. The red warning continues briefly after the overlap ends.
- **GREEN pulse** after a brake-to-throttle transition with no sustained overlap above that threshold. "Green" is not a guarantee of optimal technique; brief overlaps are tolerated.
- Each pulse lasts less than a second; off means no current flash, not "bad telemetry" or "clean driving".
- Driver can turn the light off with `Pedal overlap light (experimental)` in the detailed window.
- The light shares `MiniHUD`'s `Qt.WA_TranslucentBackground` window and moves with the `≡` grab handle. No second DirectX overlay/window or opaque box.
- 0.3.1.2 alpha HUD, corner names and rapid feedback timing are retained. The corner name's user-requested **white, bold 16-pt font** is preserved.
- Pure logic module: `pedal_overlap.py`; view module: `overlap_indicator.py`.
- New local `data/pedal_overlap_history.jsonl` for completed brake-to-throttle transitions; saved independently of coaching grades. Archive Stint archives this log too.
- Based on the user-supplied `pedals.py` concept, but **NEVER runs or imports it**. The original `pedals.py` creates/opens ACC's named memory through a potentially unsafe mmap constructor; this is deliberately excluded.
- Reuses each validated sample returned by the EXISTING `acc_memory.py` without opening additional mappings. `acc_memory.py`, `coaching_engine.py`, `advanced_engine.py`, `hud_rhythm.py`, `acc_graphics_probe.py` are byte-identical to 0.3.1.2.
- The original tool suppresses downshift gas blips by reading gear. Current telemetry `TelemetrySample` exposes no gear, so the merged module **cannot yet confirm a downshift blip**. Gear-change false alarms may occur. The pure module supports an optional gear argument for future use, but the safe ACC reader is intentionally unchanged. Treat red as a data signal, not certain driver error.
- The underlying coach's numeric 1–5 grade is unaffected; this is an **independent pedal timing diagnostic**.

## Safe installation

### Patch existing working 0.3.1.2
Close the Advanced Trail Braking application. Back up your existing `main.py` and `mini_hud.py`, then copy these four files into the program's **same directory**:

- `pedal_overlap.py` (new)
- `overlap_indicator.py` (new)
- `main.py` (replace)
- `mini_hud.py` (replace; includes existing white corner-name text change)

Optional: copy `pedal_light_preview.py` and `run_pedal_light_preview.bat` for an isolated preview. Existing virtual environment and all metadata files stay in place. Never copy the original `pedals.py` into this app.

### Full source package
Unzip to a separate directory and run `install_windows.bat`, then with ACC **closed** run `run_preflight_no_game.bat` and `run_pedal_light_preview.bat`. Only afterward, once ACC is loaded onto track in a practice session, run `run_live_after_acc_loaded.bat`. Exit if there is any instability. Use borderless/windowed rendering for overlay visibility.

The window alpha and drag grip must be verified in Windows; Qt was not installed in the build/test environment, so no real Windows rendering was verified here.

No GitHub files were pushed, merged, or published.
