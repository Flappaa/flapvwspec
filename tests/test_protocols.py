import pytest
from vlinker.protocols import parse_obd_03_response


def test_parse_obd_03_empty():
    assert parse_obd_03_response(b'') == []


def test_parse_obd_03_sample_ascii():
    # Example ELM ASCII response: '43 01 33 00 00'
    resp = b'43 01 33 00 00\r>'
    dtcs = parse_obd_03_response(resp)
    assert isinstance(dtcs, list)


def test_parse_obd_03_binary():
    resp = bytes([0x43, 0x01, 0x33, 0x00, 0x00])
    dtcs = parse_obd_03_response(resp)
    assert isinstance(dtcs, list)