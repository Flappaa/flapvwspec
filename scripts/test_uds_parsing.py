#!/usr/bin/env python3
"""Smoke tests for UDS parsing helpers.

Run with the project's virtualenv activated.
"""
from vlinker.uds import parse_dtc_bytes, decode_did_value


def test_parse():
    # construct synthetic response: two DTCs with status bytes
    # DTC1: 0x01 0x02 0x03, status 0x10
    # DTC2: 0xAA 0xBB 0xCC, no status
    resp = bytes([0x01, 0x02, 0x03, 0x10, 0xAA, 0xBB, 0xCC])
    parsed = parse_dtc_bytes(resp)
    assert len(parsed) == 2
    assert parsed[0]['raw'] == '010203'
    assert parsed[0]['status'] == '0x10'
    assert parsed[1]['raw'] == 'AABBCC'
    print('parse_dtc_bytes OK')


def test_decode_did():
    did = 0xF190
    data = b'VEHICLEVIN12345'
    res = decode_did_value(did, data)
    assert res['did'] == '0xF190'
    assert 'ascii' in res
    print('decode_did_value OK')


if __name__ == '__main__':
    test_parse()
    test_decode_did()
    print('UDS_PARSING_TESTS_OK')
