import pytest
import time
from vlinker import iso_tp


class FakeSerialStress:
    def __init__(self, device=None, baud=115200, timeout=3.0):
        self.sent = []
        self.to_read = []
        self.opened = False

    def open(self):
        self.opened = True

    def close(self):
        self.opened = False

    def send_bytes(self, b: bytes):
        self.sent.append(bytes(b))
        pci = b[0]
        if (pci >> 4) == 1:
            # queue multiple CTS frames then a final single-frame response
            for _ in range(3):
                self.to_read.append(bytes([0x30, 0x02, 0x01]))
            self.to_read.append(bytes([0x03]) + b'OK!')

    def read_all(self):
        if self.to_read:
            return self.to_read.pop(0)
        time.sleep(0.001)
        return b''


def test_iso_tp_stress():
    orig = iso_tp.SerialComm
    try:
        iso_tp.SerialComm = FakeSerialStress
        payload = 'AA' * 30
        resp = iso_tp.send_iso_tp('fake', payload)
        assert isinstance(resp, (bytes, bytearray))
        assert b'OK!' in resp
    finally:
        iso_tp.SerialComm = orig
