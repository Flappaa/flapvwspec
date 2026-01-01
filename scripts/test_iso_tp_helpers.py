#!/usr/bin/env python3
"""Unit tests for ISO-TP helper parsing functions using simulator frames."""
from vlinker.simulator import make_iso_tp_frames, reassemble_iso_tp_frames
from vlinker.iso_tp import _parse_flow_control


def test_sf_ff_cf_reassembly():
    payload = b'X' * 40
    frames = make_iso_tp_frames(payload, can_mtu=8)
    out = reassemble_iso_tp_frames(frames)
    assert out == payload
    print('iso-tp reassembly OK')


def test_parse_fc():
    # build FC: 0x30 | fs (0) ; BS=4 ; stMin=10
    fc = bytes([0x30, 0x04, 0x0A])
    parsed = _parse_flow_control(fc)
    assert parsed is not None
    fs, bs, st, consumed = parsed
    assert fs == 0 and bs == 4 and st == 0x0A
    print('parse_fc OK')


if __name__ == '__main__':
    test_sf_ff_cf_reassembly()
    test_parse_fc()
    print('ISO_TP_HELPERS_TESTS_OK')
