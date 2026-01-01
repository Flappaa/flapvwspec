from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import threading

router = APIRouter()


class ConnectRequest(BaseModel):
    device: str
    baud: int = 115200


class _SerialManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = None
        self._device = None

    def connect(self, device: str, baud: int = 115200):
        from vlinker.serial_comm import SerialComm
        with self._lock:
            if self._conn is not None:
                raise RuntimeError('already connected')
            sc = SerialComm(device, baud)
            sc.open()
            self._conn = sc
            self._device = device
            return {'connected': True, 'device': device}

    def send_ascii_line(self, line: str):
        if self._conn is None:
            raise RuntimeError('not connected')
        return self._conn.send_ascii_line(line)

    def send_hex(self, hexstr: str):
        if self._conn is None:
            raise RuntimeError('not connected')
        return self._conn.send_hex(hexstr)

    def scan_ecus(self):
        if self._conn is None:
            raise RuntimeError('not connected')
        probes = [
            {'name': 'newline', 'type': 'ascii', 'payload': '\r'},
            {'name': 'ATI', 'type': 'ascii', 'payload': 'ATI'},
            {'name': 'AT Z', 'type': 'ascii', 'payload': 'AT Z'},
            {'name': 'ELM 0100', 'type': 'ascii', 'payload': '0100'},
            {'name': 'UDS TesterPresent', 'type': 'hex', 'payload': '023E00'},
        ]
        results = []
        for p in probes:
            try:
                if p['type'] == 'ascii':
                    resp = self._conn.send_ascii_line(p['payload'])
                else:
                    resp = self._conn.send_hex(p['payload'])
            except Exception:
                resp = b''
            results.append({'probe': p['name'], 'resp_hex': (resp.hex() if isinstance(resp, (bytes, bytearray)) else ''), 'resp_ascii': (resp.decode('latin-1', errors='replace') if isinstance(resp, (bytes, bytearray)) else str(resp))})
        return results

    def read_dtc(self, ecu: str):
        if self._conn is None:
            raise RuntimeError('not connected')
        # try UDS/UDS helper if exposed by the connection
        if hasattr(self._conn, 'read_dtc'):
            return self._conn.read_dtc(ecu)
        # fallback to ELM-style '03'
        resp = self._conn.send_ascii_line('03')
        try:
            from vlinker.protocols import parse_obd_03_response
            raw = resp
            parsed = parse_obd_03_response(raw)
            return parsed
        except Exception:
            return [resp.hex() if isinstance(resp, (bytes, bytearray)) else str(resp)]

    def clear_dtc(self, ecu: str):
        if self._conn is None:
            raise RuntimeError('not connected')
        if hasattr(self._conn, 'clear_dtc'):
            return self._conn.clear_dtc(ecu)
        resp = self._conn.send_ascii_line('04')
        # simple heuristic
        return {'resp_hex': (resp.hex() if isinstance(resp, (bytes, bytearray)) else ''), 'resp_ascii': (resp.decode('latin-1', errors='replace') if isinstance(resp, (bytes, bytearray)) else str(resp))}

    def read_measures(self, ecu: str, pids=None):
        if self._conn is None:
            raise RuntimeError('not connected')
        if pids is None or not pids:
            resp = self._conn.send_ascii_line('0100')
            return {'0100': (resp.hex() if isinstance(resp, (bytes, bytearray)) else str(resp))}
        out = {}
        for pid in pids:
            cmd = '01' + pid
            resp = self._conn.send_ascii_line(cmd)
            out[pid] = (resp.hex() if isinstance(resp, (bytes, bytearray)) else str(resp))
        return out

    def disconnect(self):
        with self._lock:
            if self._conn is None:
                return {'connected': False}
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._device = None
            return {'connected': False}

    def status(self):
        with self._lock:
            return {'connected': self._conn is not None, 'device': self._device}


_mgr = _SerialManager()


@router.post('/api/serial/connect')
def api_connect(req: ConnectRequest):
    try:
        return _mgr.connect(req.device, req.baud)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/api/serial/disconnect')
def api_disconnect():
    return _mgr.disconnect()


@router.get('/api/serial/status')
def api_status():
    return _mgr.status()


# Diagnostic endpoints: support simulator mode via query `use_simulator=true` or body flag


@router.get('/api/diag/discover')
def api_discover(use_simulator: bool = False):
    if use_simulator:
        return {'ecus': [
            {'id': 'ECU_ENGINE', 'name': 'Engine Control', 'address': '7E0'},
            {'id': 'ECU_ABS', 'name': 'ABS', 'address': '7E1'},
        ]}

    # If we already have a live connection, prefer using it to avoid opening the port twice
    status = _mgr.status()
    if status.get('connected'):
        try:
            res = _mgr.scan_ecus()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        if isinstance(res, (bytes, bytearray)):
            return {'ecus': [{'raw_hex': res.hex()}]}
        return {'ecus': res}

    # No live connection: try high-level diag helpers if available
    try:
        from vlinker import diag
    except Exception:
        diag = None

    if diag is not None and hasattr(diag, 'scan_ecus'):
        res = None
        try:
            try:
                res = diag.scan_ecus()
            except TypeError:
                device = _mgr.status().get('device')
                try:
                    res = diag.scan_ecus(device)
                except TypeError:
                    res = None
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        if res is not None:
            if isinstance(res, (bytes, bytearray)):
                return {'ecus': [{'raw_hex': res.hex()}]}
            return {'ecus': res}

    raise HTTPException(status_code=400, detail='not connected to device; connect first')


@router.get('/api/diag/read_dtcs')
def api_read_dtcs(ecu: str, use_simulator: bool = False):
    if use_simulator:
        return {'ecu': ecu, 'dtcs': [
            {'raw': '010203', 'code': 'DTC_010203', 'status': '0x10'},
            {'raw': 'AABBCC', 'code': 'DTC_AABBCC', 'status': '0x00'},
        ]}

    status = _mgr.status()
    if status.get('connected'):
        try:
            dtcs = _mgr.read_dtc(ecu)
            return {'ecu': ecu, 'dtcs': dtcs}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    try:
        from vlinker import diag
    except Exception:
        diag = None

    if diag is not None and hasattr(diag, 'read_dtc'):
        # diag.read_dtc may accept (ecu) or (device,) so try both variants
        try:
            dtcs = diag.read_dtc(ecu)
        except TypeError:
            try:
                device = _mgr.status().get('device')
                dtcs = diag.read_dtc(device)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {'ecu': ecu, 'dtcs': dtcs}

    raise HTTPException(status_code=400, detail='not connected; connect first')


@router.post('/api/diag/clear_dtcs')
def api_clear_dtcs(body: Dict[str, Any]):
    ecu = body.get('ecu')
    if not ecu:
        raise HTTPException(status_code=400, detail='ecu required')
    force = bool(body.get('force', False))
    if not force:
        raise HTTPException(status_code=403, detail='force=true required to clear DTCs')
    use_sim = bool(body.get('use_simulator', False))
    if use_sim:
        return {'ecu': ecu, 'cleared': True, 'result': 'simulated'}

    try:
        from vlinker import diag
    except Exception:
        diag = None

    if diag is not None and hasattr(diag, 'clear_dtc'):
        try:
            res = diag.clear_dtc(ecu)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        try:
            from vlinker.audit import audit_write
            audit_write('clear_dtc', {'ecu': ecu, 'result': str(res)})
        except Exception:
            pass
        return {'ecu': ecu, 'cleared': True, 'result': res}

    status = _mgr.status()
    if not status.get('connected'):
        raise HTTPException(status_code=400, detail='not connected; connect first')
    try:
        res = _mgr.clear_dtc(ecu)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        from vlinker.audit import audit_write
        audit_write('clear_dtc', {'ecu': ecu, 'result': str(res)})
    except Exception:
        pass
    return {'ecu': ecu, 'cleared': True, 'result': res}


@router.post('/api/diag/read_measures')
def api_read_measures(body: Dict[str, Any]):
    ecu = body.get('ecu')
    pids = body.get('pids') or []
    use_sim = bool(body.get('use_simulator', False))
    if not ecu:
        raise HTTPException(status_code=400, detail='ecu required')
    if use_sim:
        measures = {pid: {'value': 123.4, 'units': 'u'} for pid in pids} if pids else {
            'rpm': {'value': 800, 'units': 'rpm'},
            'temp': {'value': 72, 'units': 'C'},
        }
        return {'ecu': ecu, 'measures': measures}

    status = _mgr.status()
    if status.get('connected'):
        try:
            res = _mgr.read_measures(ecu, pids)
            return {'ecu': ecu, 'measures': res}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    try:
        from vlinker import diag
    except Exception:
        diag = None

    if diag is not None:
        read_fn = None
        for name in ('read_measure', 'read_measures', 'read_measuring_blocks'):
            if hasattr(diag, name):
                read_fn = getattr(diag, name)
                break
        if read_fn is not None:
            try:
                res = read_fn(ecu, pids) if pids else read_fn(ecu)
            except TypeError:
                # some implementations expect (device, pids)
                try:
                    device = _mgr.status().get('device')
                    res = read_fn(device, pids) if pids else read_fn(device)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            return {'ecu': ecu, 'measures': res}

    raise HTTPException(status_code=400, detail='not connected; connect first')
