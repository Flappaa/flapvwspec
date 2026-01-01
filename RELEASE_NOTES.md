# v0.1.0

Initial release — CI, tests, web simulator, ISO‑TP hardening, and UDS helpers.

## Summary
- Added FastAPI web simulator and simulator endpoints `/api/sim/*`.
- Implemented ISO‑TP sender/receiver with robust Flow Control handling and WAIT support.
- Added UDS helpers and safe diagnostic API endpoints (`/api/diag/*`).
- Safety: destructive operations are gated (e.g. `CLEAR=true` required for clears).
- CI workflow and test suite added; 18 tests passing locally.

## Details
- Simulator endpoints:
  - `/api/sim/frames` — generate ISO‑TP frames for a payload.
  - `/api/sim/reassemble` — reassemble frames to payload.
  - `/api/sim/run-tests` — run lightweight simulator self-tests.
- ISO‑TP improvements:
  - Buffer‑scanning FC parser, stMin conversion, WAIT retry handling, and FC consumption.
  - New tests for OVERFLOW and WAIT behavior.
- Web UI: FastAPI app with safe serial manager and simulator views.

## Tests & CI
- Local: `pytest -q` → `18 passed`.
- GitHub Actions CI workflow added at `.github/workflows/ci.yml`.

## Hardware
- Non‑destructive smoke tests executed against vLinker at `/dev/ttyUSB0` (discovery, DTC read, measures).

## How to publish
1. In the GitHub UI, go to the repository's **Releases** → **Draft a new release**.
2. Select tag `v0.1.0` (already pushed) or create it from the UI.
3. Paste these notes as the release body and publish.

---
If you want me to create the release via API I can retry with a valid PAT that has `Releases: Read & write` and `Contents: Read & write` for the repository.
