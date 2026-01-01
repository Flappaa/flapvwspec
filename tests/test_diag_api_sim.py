from fastapi.testclient import TestClient
from vlinker.webapp.main_safe import app


def test_diag_simulator_endpoints():
    client = TestClient(app)

    r = client.get('/api/serial/status')
    assert r.status_code == 200

    r = client.get('/api/diag/discover?use_simulator=true')
    assert r.status_code == 200
    data = r.json()
    assert 'ecus' in data

    r = client.get('/api/diag/read_dtcs?use_simulator=true&ecu=ECU_ENGINE')
    assert r.status_code == 200
    assert 'dtcs' in r.json()

    r = client.post('/api/diag/read_measures', json={"use_simulator": True, "ecu": "ECU_ENGINE", "pids": ["0C","0D"]})
    assert r.status_code == 200
    assert 'measures' in r.json()
