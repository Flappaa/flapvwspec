# Release v0.1.0

Please publish the release `v0.1.0` (tag already pushed) with the notes below.

## Summary
Initial release — CI, tests, web simulator, ISO‑TP hardening, and UDS helpers.

## Release notes
- Added FastAPI web simulator and simulator endpoints `/api/sim/*`.
- Implemented ISO‑TP sender/receiver with robust Flow Control handling and WAIT support.
- Added UDS helpers and safe diagnostic API endpoints (`/api/diag/*`).
- Safety: destructive operations are gated (e.g. `CLEAR=true` required for clears).
- CI workflow and test suite added; 18 tests passing locally.

## How to publish
1. In the GitHub UI, go to the repository's **Issues** and create a new issue titled `Publish v0.1.0`.
2. Paste this file's contents into the issue body and tag/assign as needed.

---
Automated note: tag `v0.1.0` already exists at https://github.com/Flappaa/flapvwspec/releases/tag/v0.1.0
