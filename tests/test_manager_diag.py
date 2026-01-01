from fastapi.testclient import TestClient
from vlinker.webapp.main_safe import app


class FakeConn:
    def __init__(self):
        self.sent = []

    def send_bytes(self, b: bytes):
        self.sent.append(bytes(b))
        if b.startswith(b'ATI') or b.startswith(b'AT'):
            self._next = b'ELM327 v2.3\r\r>'
        else:
            self._next = b'OK'

    def read_all(self):
        v = getattr(self, '_next', b'')
        self._next = b''
        return v

    def open(self):
        pass

    def close(self):
        pass

    def send_ascii_line(self, s: str):
        self.sent.append(s.encode())
        ss = s.strip().upper()
        if ss == 'ATI':
            self._next = b'ELM327 v2.3\r\r>'
        else:
            self._next = b'OK\r\n>'
        return {'sent': s}

    def send_hex(self, hx: str):
        try:
            b = bytes.fromhex(hx)
        except Exception:
            b = hx.encode()
        self.sent.append(b)
        self._next = b'RESP'
        return {'sent_hex': hx}


def attach_fake_mgr(fake_conn):
    from vlinker.webapp import diag_api
    mgr = diag_api._mgr
    mgr._conn = fake_conn
    mgr._device = '/dev/fake'
    return mgr


def test_manager_endpoints():
    client = TestClient(app)
    fake = FakeConn()
    attach_fake_mgr(fake)

    r = client.get('/api/serial/status')
    assert r.status_code == 200
    assert r.json().get('connected') is True

    r = client.get('/api/diag/discover?use_simulator=false')
    assert r.status_code == 200
    assert 'ecus' in r.json()

    r = client.get('/api/diag/read_dtcs?use_simulator=false&ecu=ECU_ENGINE')
    assert r.status_code == 200
    assert 'dtcs' in r.json()

    r = client.post('/api/diag/read_measures', json={"use_simulator": False, "ecu": "ECU_ENGINE", "pids": ["0C","0D"]})
    assert r.status_code == 200
    assert 'measures' in r.json()
