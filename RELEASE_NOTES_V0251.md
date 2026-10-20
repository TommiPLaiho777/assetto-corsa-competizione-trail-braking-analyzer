# Advanced Trail Braking v0.2.5.1 — Quicker Mini HUD presentation

The on-track driver reported that the 0.2.5 transparent Mini HUD looked and worked well, but feedback arrived slightly late after the corner. This maintenance revision shortens the event's post-release observation from 3.0 s to 2.6 s and the continuous approximately-straight presentation gate from 0.48 s to 0.24 s.

**No changes to** the actual scoring heuristics, diagnostic colors/text, Mini HUD visuals, ACC reader, read-only mapping, detailed GUI, logfile formats, or user-controlled HUD placement. A score is still withheld from the HUD while steering/yaw/brake conditions indicate continued cornering. The user can drag the HUD into a high, cockpit-style position; no forced automatic repositioning.

**Validation:** Regraded all 68 raw user braking events privately; all 68 grades matched the previously recorded 0.2.5 final coaching grades with 2.6 s. These raw driving logs are NOT in the repository or release package. Shortening the observation window can still affect future unobserved cases, especially longer coasting events. Run offline preflight and a short Windows/ACC live test before routine driving.

Draft PR #1 should be kept unmerged until CI, Windows overlay, and ACC live checks pass.
