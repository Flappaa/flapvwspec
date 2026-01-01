import json
import os
import time
from pathlib import Path

_lock = None


def _audit_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    p = root / 'logs'
    p.mkdir(parents=True, exist_ok=True)
    return p / 'audit.log'


def audit_write(action: str, details: dict):
    """Append an audit entry with timestamp and action to the audit log."""
    try:
        entry = {'ts': time.time(), 'action': action, 'details': details}
        p = _audit_path()
        with p.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        # best-effort; do not raise to avoid blocking operations
        pass
