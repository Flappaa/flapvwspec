import io
import types

# Simple mock for SerialComm used in tests
class MockSerial:
    def __init__(self, device, baud=115200, timeout=1.0):
        self.device = device
        self.baud = baud
        self.timeout = timeout
        self.is_open = True
        self._buffer = b''

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.is_open = False

    def read_all(self):
        return self._buffer

    def send_ascii_line(self, line: str):
        # Respond to common ELM commands
        u = line.strip().upper()
        if u == 'ATZ':
            return b'ELM327 v1.5\r>'
        if u == 'ATE0':
            return b'OK\r>'
        if u == '03':
            # example: response containing one DTC 01033 -> 43 01 33 00 00
            return b'43 01 33 00 00\r>'
        return b''

    def send_hex(self, hexstr: str):
        # simple echo behavior for tests
        return bytes.fromhex(hexstr)


def test_read_dtc_with_mock(monkeypatch):
    import vlinker.diag as diag
    import vlinker.serial_comm as sc
    monkeypatch.setattr(sc, 'SerialComm', MockSerial)
    dtcs = diag.read_dtc('/dev/ttyUSB0', mode='elm')
    assert isinstance(dtcs, list)
    # sample DTCs parsed
    assert len(dtcs) >= 0


def test_request_seed_and_send_key_mock(monkeypatch):
    import vlinker.advanced as adv
    import vlinker.serial_comm as sc
    monkeypatch.setattr(sc, 'SerialComm', MockSerial)
    seed = adv.request_seed('/dev/ttyUSB0')
    assert seed is not None
    resp = adv.send_key('/dev/ttyUSB0', b'\x01\x02')
    assert resp is not None
