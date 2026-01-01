Quick install (recommended: use a virtual environment)

Create and activate a venv, then install in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

If you prefer `pipx`:

```bash
pipx install --editable .
```

Interactive profile builder

```bash
# From project root after installation
vlinker-profile-interactive /path/to/capture.log
# or via main CLI
vlinker profile interactive /path/to/capture.log
```

Run without installing

```bash
./bin/vlinker-profile-interactive /path/to/capture.log
```

If you want the main CLI without installing, run:

```bash
PYTHONPATH=/home/benny/vlinker-cli python3 vlinker_cli.py profile interactive /path/to/capture.log
```
