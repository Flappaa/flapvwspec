#!/usr/bin/env python3
from fastapi.testclient import TestClient
from vlinker.webapp.main_safe import app


def run():
    client = TestClient(app)

    r = client.get("/api/serial/status")
    print('serial/status ->', r.status_code, r.json())

    r = client.get("/api/diag/discover?use_simulator=true")
    print('discover(sim) ->', r.status_code, r.json())

    r = client.get("/api/diag/read_dtcs?use_simulator=true&ecu=ECU_ENGINE")
    print('read_dtcs(sim) ->', r.status_code, r.json())

    r = client.post("/api/diag/read_measures", json={"use_simulator": True, "ecu": "ECU_ENGINE", "pids": ["0C","0D"]})
    print('read_measures(sim) ->', r.status_code, r.json())


if __name__ == '__main__':
    run()
