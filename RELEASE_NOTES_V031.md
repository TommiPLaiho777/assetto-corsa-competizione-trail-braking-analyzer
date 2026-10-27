# 0.3.1 — Experimental corner names for ACC Nürburgring 24h

- Optional independent RaceIQ **metadata download** for 60 numbered turns and their lap-fraction boundaries. Not distributed in the source ZIP.
- Local original `fastlane.ai` registration required for geometric/normalized-progress cross-check.
- Mini HUD may show a brief separate corner-name label on the SAME short feedback event. No longer display or changed timing.
- Event history receives an optional experimentally attributed `corner` object; the existing grades and raw replay logs remain untouched.
- Fails closed: missing metadata, absent/implausible graphics, mismatching progress or stale readings suppress name only.
- New independent memory reader is read-only; it is NOT the game-critical ACC physics reader.
- Windows/ACC live corner placement not yet verified: do not use as authoritative until a 90-second `line_probe_*.csv` measurement has been evaluated.
- ACC original data and third-party JSON not included in application ZIP or GitHub source commit.
