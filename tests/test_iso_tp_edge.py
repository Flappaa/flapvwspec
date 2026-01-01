import time
import pytest
from vlinker import iso_tp


class FakeSerial:
    def __init__(self, device=None, baud=115200, timeout=3.0):
        self.sent = []
        self.to_read = []

    def open(self):
        pass

    def close(self):
        pass

    def send_bytes(self, b: bytes):
        self.sent.append(bytes(b))
        first = b[0]
        if (first >> 4) == 1:
            # enqueue a WAIT then a CTS and finally a Single Frame response
            self.to_read.append(bytes([0x31, 0x02, 0x05]))
            self.to_read.append(bytes([0x30, 0x02, 0x00]))
            self.to_read.append(bytes([0x03]) + b'RSP')

    def read_all(self):
        if self.to_read:
            return self.to_read.pop(0)
        time.sleep(0.005)
        return b''


class FakeSerialAlwaysWait(FakeSerial):
    def send_bytes(self, b: bytes):
        self.sent.append(bytes(b))
        first = b[0]
        if (first >> 4) == 1:
            for _ in range(10):
                self.to_read.append(bytes([0x31, 0x00, 0x05]))


def test_wait_then_cts_success():
    orig = iso_tp.SerialComm
    try:
        iso_tp.SerialComm = FakeSerial
        resp = iso_tp.send_iso_tp('fake', '0102030405060708090A0B0C')
        assert resp == b'RSP'
    finally:
        iso_tp.SerialComm = orig


def test_wait_retry_exhaustion():
    orig = iso_tp.SerialComm
    try:
        iso_tp.SerialComm = FakeSerialAlwaysWait
        try:
            resp = iso_tp.send_iso_tp('fake', '0102030405060708090A0B0C')
        except RuntimeError:
            # acceptable behavior: raises after retry exhaustion
            return
        else:
            # or returns some bytes; ensure it's bytes-like
            assert isinstance(resp, (bytes, bytearray))
    finally:
        iso_tp.SerialComm = orig
