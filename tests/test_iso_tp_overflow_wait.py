import pytest
import time

from vlinker import iso_tp


class FakeSerial:
    def __init__(self, responses):
        self.writes = []
        # responses is a list of bytes objects to return on read_all()
        self._responses = list(responses)

    def open(self):
        pass

    def send_bytes(self, b: bytes):
        self.writes.append(b)

    def read_all(self):
        if not self._responses:
            return b''
        return self._responses.pop(0)


def test_overflow_raises():
    # FC with flow_status == 2 (overflow/abort)
    # FC PCI byte: 0x30 | flow_status (2) -> 0x32
    fc = bytes([0x32, 0x00, 0x00])
    fake = FakeSerial([fc])

    # Monkeypatch SerialComm used in module
    iso_tp.SerialComm = lambda device, baud, timeout: fake

    with pytest.raises(RuntimeError, match="overflow"):
        iso_tp.send_iso_tp('/dev/null', '0102030405060708090A0B0C0D0E0F')


def test_initial_wait_exceeds_retries():
    # initial FC = WAIT (0x31) repeatedly -> should raise after retries
    fc_wait = bytes([0x31, 0x00, 0x00])
    # return the FC repeatedly so the sender keeps seeing WAIT
    fake = FakeSerial([fc_wait, fc_wait, fc_wait, fc_wait, fc_wait, fc_wait])
    iso_tp.SerialComm = lambda device, baud, timeout: fake

    with pytest.raises(RuntimeError, match="WAIT exceeded retries"):
        iso_tp.send_iso_tp('/dev/null', '0' * 30)
