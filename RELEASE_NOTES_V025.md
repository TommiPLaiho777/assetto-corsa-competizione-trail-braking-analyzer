# Advanced Trail Braking 0.2.5 — Mini HUD

This is a **UI-only** update to the user's v0.2.4.1 working prototype.
It offers a separate transparent overlay with one large colored number and one
short colored diagnosis, its own minimize and close controls, drag positioning,
plus a minimize-able detailed GUI with an optional on-top toggle.

The Mini HUD intentionally waits until after the braking event and a steady
low-brake / low-yaw / low-steer window before displaying the final feedback.
It never attempts to infer a missed apex without measured track position.

**Validation:** all available offline tests run. Qt visual tests run on
Windows or CI when PyQt5 is present. ACC live and overlay compatibility are
not established by offline tests. ACC physics code unchanged from 0.2.4.1.

Draft PR #1 is meant to stay open until Windows smoke and ACC live testing.
