# vlinker-cli

Lightweight VCDS-like CLI + web UI for VGate vLinker (Kali-friendly).

**Quick Start**
- Create a Python virtualenv and activate:

```bash
python -m venv .venv
source .venv/bin/activate
```

- Install runtime deps:

```bash
pip install -r requirements.txt
```

- Run the web UI (FastAPI / Uvicorn):

```bash
uvicorn vlinker.webapp.main_safe:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 in a browser. The UI supports simulator mode.

**Running against hardware**
- Connect your vLinker adapter (example: `/dev/ttyUSB0`). Use the API or UI to `Connect`.
- Non-destructive smoke test:

```bash
. .venv/bin/activate
bash scripts/hw_smoke.sh
```

Set `CLEAR=true` to enable DTC clear (destructive) only when you are sure.

**Tests & Development**
- Install dev deps:

```bash
pip install -r requirements-dev.txt
```
- Run tests:

```bash
pytest -q
```

Included tests cover simulator endpoints, ISO‑TP helpers, and manager/diag API behavior.

**CI**
- A GitHub Actions workflow is provided at `.github/workflows/ci.yml` to run tests on push/PR.

**Useful scripts**
- `scripts/hw_smoke.sh` — non-destructive hardware smoke test
- `scripts/run_diag_api_sim.py` — quick simulator API exerciser
- `scripts/run_iso_tp_edge.py`, `scripts/run_iso_tp_stress.py` — iso-tp tests

**Next steps / recommendations**
- Add coverage reporting and include `requirements-dev.txt` in CI.
- Harden ISO‑TP handling further (OVERFLOW, stMin edge cases) and expand stress variants.

If you want, I can commit these changes and push a branch, or add coverage and CI badges.
vLinker CLI prototype

Small prototype to detect a VGate vLinker USB device on Linux and provide simple commands.

Commands
- `list` : list /dev/serial/by-id and raw tty devices
- `info <path>` : show resolved path for a by-id link
- `detect` : print the most likely device path (by-id preferred)

Next steps: add `pyserial` based communication, implement CAN/UDS/KWP frames, and a CLI/GUI for diagnostics.

Getting started
--------------

1. Install dependencies (recommended inside a virtualenv):

```bash
python3 -m pip install -r requirements.txt
```

2. Install udev rule and link CLI (from repo root):

```bash
sudo ./scripts/install.sh
```

Usage examples
--------------

- List devices:

```bash
python3 vlinker_cli.py list
```

- Scan ECUs and read DTCs (ELM/OBD mode):

```bash
python3 vlinker_cli.py diag scan /dev/ttyUSB0 --mode elm
python3 vlinker_cli.py diag read-dtc /dev/ttyUSB0
```

- Attach an slcan interface (requires slcand in PATH and sudo):

```bash
python3 vlinker_cli.py can attach-slcan /dev/ttyUSB0 --iface can0 --bitrate 500000
```

Advanced features
-----------------

This prototype includes:
- Serial communication helpers (`vlinker/serial_comm.py`)
- Diagnostic helpers for ELM-like adapters and basic OBD/UDS flows (`vlinker/diag.py`)
- Protocol parsing helpers (`vlinker/protocols.py`)
- VW long-coding helpers (`vlinker/vw_helpers.py`)
- Advanced UDS scaffolding and seed/key orchestration (`vlinker/advanced.py`, `vlinker/ecu_profiles.py`)

Safety and testing notes
------------------------

- This tool is a prototype and may send commands that can modify vehicle state. Always test on a non-critical vehicle and ensure you have a backup and knowledge of the procedures.
- Coding/adaptation and security access flows require vehicle-specific knowledge and testing. The provided ECU profiles are placeholders and must be replaced with verified algorithms before use in production.

Safe coding notes
-----------------

- The CLI supports a `--dry-run` mode for coding writes which prepares the UDS payload and prints it without sending it to the vehicle. Use this to verify the payload before applying changes.
- To actually perform a coding write you must pass `--force` explicitly to avoid accidental writes.
- Example (dry-run):

```bash
cat coding.bin | python3 vlinker_cli.py adv coding /dev/ttyUSB0 --hex F190 --dry-run
```

Example (apply with explicit force):

```bash
cat coding.bin | python3 vlinker_cli.py adv coding /dev/ttyUSB0 --hex F190 --force
```

Packaging
---------

To build a single-file executable (requires `pyinstaller`):

```bash
./scripts/build.sh
```

If you have questions or want me to prioritize a specific VW/Audi model/year for coding/security algorithms, tell me which vehicle and I will focus next.

