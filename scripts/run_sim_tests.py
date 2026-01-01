#!/usr/bin/env python3
"""Run simple simulation tests for ISO-TP helper in the repo.

This script uses `vlinker.simulator` to create frames and verify
reassembly. Run from the project root with the venv activated.
"""
from vlinker.simulator import make_iso_tp_frames, reassemble_iso_tp_frames


def hexify(frames):
    return [f"{i:02x}" for f in [b"".join([bytes([c]) for c in fr]) for fr in frames]]


def run():
    tests = [b"hello", b"0123456789ABCDEF0123456789", b"x" * 100]
    for t in tests:
        frames = make_iso_tp_frames(t, can_mtu=8)
        out = reassemble_iso_tp_frames(frames)
        ok = out == t
        print(f"payload_len={len(t)} frames={len(frames)} ok={ok}")
        if not ok:
            print('  expected:', t)
            print('  got     :', out)
            raise SystemExit(2)
    print('SIM_TESTS_OK')


if __name__ == '__main__':
    run()
