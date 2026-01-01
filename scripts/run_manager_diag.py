#!/usr/bin/env python3
from fastapi.testclient import TestClient
from vlinker.webapp.main_safe import app

import time

class FakeConn:
    def __init__(self):
        self.sent = []
    def send_bytes(self, b: bytes):
        self.sent.append(bytes(b))
        # simple echo-like behavior for probes
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
        # simulate sending an ASCII AT-style command followed by response
        self.sent.append(s.encode())
        ss = s.strip().upper()
        if ss == 'ATI':
            self._next = b'ELM327 v2.3\r\r>'
        else:
            self._next = b'OK\r\n>'
        return {'sent': s}

    def send_hex(self, hx: str):
        # simulate sending hex payload and provide a fake response
        try:
            b = bytes.fromhex(hx)
        except Exception:
            b = hx.encode()
        self.sent.append(b)
        self._next = b'RESP'
        return {'sent_hex': hx}


def attach_fake_mgr(fake_conn):
    # import the module and attach a fake manager connection if present
    from vlinker.webapp import diag_api
    mgr = diag_api._mgr
    mgr._conn = fake_conn
    mgr._device = '/dev/fake'
    return mgr


def run():
    client = TestClient(app)
    fake = FakeConn()
    mgr = attach_fake_mgr(fake)

    # status should show connected via manager
    r = client.get('/api/serial/status')
    print('status', r.status_code, r.json())

    # call discover (uses manager if connected)
    r = client.get('/api/diag/discover?use_simulator=false')
    print('discover', r.status_code, r.json())

    # read dtcs via manager (non-destructive)
    r = client.get('/api/diag/read_dtcs?use_simulator=false&ecu=ECU_ENGINE')
    print('read_dtcs', r.status_code, r.json())

    # read measures via manager
    r = client.post('/api/diag/read_measures', json={"use_simulator": False, "ecu": "ECU_ENGINE", "pids": ["0C","0D"]})
    print('read_measures', r.status_code, r.json())


if __name__ == '__main__':
    run()
