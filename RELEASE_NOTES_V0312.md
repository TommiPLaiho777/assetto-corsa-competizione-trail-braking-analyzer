# Advanced Trail Braking 0.3.1.2 - Corner-name detection fix

- Fixes over-strict absolute lap fraction equality which suppressed names whenever ACC normalized progress and the fastlane AI-reference use distinct start positions.
- Now validates consistent *movement* of two progress signals and uses the reference route progress to identify external RaceIQ segments. Fastlane geometry must be within 14 m horizontally and 6 m vertically; inconsistent/off-track/stale data still suppresses names.
- Adds `diagnose_corner_names.bat` to check that both JSON files, `fastlane_path.txt`, and the original fastlane.ai path are present and readable. This diagnostic never attaches to ACC.
- Does NOT touch the physics shared memory reader, steering/braking scoring, Mini HUD feedback rhythm, or HUD rendering.
- This remains an experimental source attribution until a Windows live position trace confirms turn correctness. No claim of perfect match to ACC's green dynamic racing aid.
