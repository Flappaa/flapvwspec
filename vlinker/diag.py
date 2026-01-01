import os
import time
import binascii
from typing import List, Dict, Any, Optional

from .logger import get_logger
from .serial_comm import SerialComm

logger = get_logger(__name__)


def _find_device() -> Optional[str]:
    # priority: env VLINKER_DEVICE, /dev/ttyUSB0, first /dev/ttyUSB*
    dev = os.environ.get('VLINKER_DEVICE')
    if dev and os.path.exists(dev):
        return dev
    guess = '/dev/ttyUSB0'
    if os.path.exists(guess):
        return guess
    # fallback to any ttyUSB
    for p in sorted(os.listdir('/dev') if os.path.isdir('/dev') else []):
        if p.startswith('ttyUSB'):
            path = os.path.join('/dev', p)
            return path
    return None


def _hexdump(b: bytes) -> str:
    return binascii.hexlify(b).decode('ascii')


def scan_ecus(device: Optional[str] = None, baud: int = 115200, timeout: float = 1.0) -> List[Dict[str, Any]]:
    """Try a set of safe probes on the serial adapter and return any responses found.

    This is intentionally conservative: it sends benign adapter queries (ELM/AT style)
    and functional UDS TesterPresent single-frame requests where appropriate.
    """
    dev = device or _find_device()
    if not dev:
        raise RuntimeError('no serial device found; set VLINKER_DEVICE or connect vLinker')

    probes = [
        {'name': 'newline', 'type': 'ascii', 'payload': '\r'},
        {'name': 'ATI', 'type': 'ascii', 'payload': 'ATI'},
        {'name': 'AT Z', 'type': 'ascii', 'payload': 'AT Z'},
        {'name': 'ELM 0100', 'type': 'ascii', 'payload': '0100'},
        # UDS functional TesterPresent (single-frame 0x3E 0x00): encoded as hex bytes
        {'name': 'UDS TesterPresent', 'type': 'hex', 'payload': '023E00'},
    ]

    results = []
    sc = SerialComm(dev, baud=baud, timeout=timeout)
    try:
        sc.open()
        for p in probes:
            try:
                if p['type'] == 'ascii':
                    resp = sc.send_ascii_line(p['payload'])
                else:
                    resp = sc.send_hex(p['payload'])
            except Exception as e:
                logger.debug('probe %s failed: %s', p['name'], e)
                resp = b''
            results.append({'probe': p['name'], 'resp_hex': _hexdump(resp), 'resp_ascii': resp.decode('latin-1', errors='replace')})
            # small pause
            time.sleep(0.05)
    finally:
        sc.close()

    return results


def read_dtc(ecu: str, device: Optional[str] = None, baud: int = 115200, timeout: float = 2.0) -> List[str]:
    """Attempt to read DTCs by issuing a standard OBD-II/ELM '03' request.

    `ecu` is ignored for ELM-style adapters; for bus-specific transports this may be
    treated as an address in future implementations.
    """
    dev = device or _find_device()
    if not dev:
        raise RuntimeError('no serial device found')
    sc = SerialComm(dev, baud=baud, timeout=timeout)
    try:
        sc.open()
        # Try UDS first if available (many modern ECUs speak UDS)
        try:
            from .uds import read_dtc_uds
            dev = device or _find_device()
            if dev:
                udresp = read_dtc_uds(dev, baud=baud, timeout=timeout)
                if udresp:
                    return [udresp]
        except Exception:
            pass

        # Send OBD-II '03' (Report stored DTCs) as ASCII command to ELM-style adapters
        resp = sc.send_ascii_line('03')
        if not resp:
            return []
        # If the project has protocols helper, try parsing
        try:
            from .protocols import parse_obd_03_response

            parsed = parse_obd_03_response(resp)
            return parsed
        except Exception:
            # fallback: return hexdump
            return [_hexdump(resp)]
    finally:
        sc.close()


def clear_dtc(ecu: str, device: Optional[str] = None, baud: int = 115200, timeout: float = 2.0) -> Dict[str, Any]:
    """Attempt to clear DTCs using OBD-II '04' command on ELM-style adapters.

    Warning: this writes to the vehicle and should only be used with user confirmation.
    """
    dev = device or _find_device()
    if not dev:
        raise RuntimeError('no serial device found')
    sc = SerialComm(dev, baud=baud, timeout=timeout)
    try:
        sc.open()
        # Try UDS ClearDiagnosticInformation first
        try:
            from .uds import clear_dtc_uds
            dev = device or _find_device()
            if dev:
                r = clear_dtc_uds(dev, baud=baud, timeout=timeout)
                return {'resp_hex': r}
        except Exception:
            pass

        resp = sc.send_ascii_line('04')
        return {'resp_hex': _hexdump(resp), 'resp_ascii': resp.decode('latin-1', errors='replace')}
    finally:
        sc.close()


def read_measures(ecu: str, pids: Optional[List[str]] = None, device: Optional[str] = None, baud: int = 115200, timeout: float = 2.0) -> Dict[str, Any]:
    """Read measuring values. For ELM-style transport, send '01 <pid>' commands.

    `pids` may be a list of PID hex strings like ['0C','0D'].
    """
    dev = device or _find_device()
    if not dev:
        raise RuntimeError('no serial device found')
    sc = SerialComm(dev, baud=baud, timeout=timeout)
    out = {}
    try:
        sc.open()
        if not pids:
            # ask for supported PIDs
            resp = sc.send_ascii_line('0100')
            out['0100'] = _hexdump(resp)
            return out
        for pid in pids:
            cmd = '01' + pid
            resp = sc.send_ascii_line(cmd)
            out[pid] = _hexdump(resp)
            time.sleep(0.05)
        return out
    finally:
        sc.close()
import time
import binascii
from .serial_comm import SerialComm
from .protocols import parse_obd_03_response, parse_elm_echo_strip


def elm_send_obd(device, cmd, baud=115200, timeout=1.0):
    """Send an OBD hex command via an ELM327-like ASCII interface (e.g., '0100' or '03').

    Returns raw bytes response or empty bytes.
    """
    with SerialComm(device, baud=baud, timeout=timeout) as s:
        # ensure ELM in a reasonable state
        s.send_ascii_line('ATZ')
        time.sleep(0.2)
        s.send_ascii_line('ATE0')
        time.sleep(0.05)
        s.send_ascii_line('ATL0')
        time.sleep(0.05)
        # set automatic protocol selection
        s.send_ascii_line('ATSP0')
        time.sleep(0.05)
        # send OBD command
        resp = s.send_ascii_line(cmd)
        # try to normalize ELM ASCII hex to binary
        return resp


def scan_ecus(device, mode='elm', baud=115200, timeout=1.0):
    """Simple ECU scan. In `elm` mode uses OBD '0100' to detect supported PIDs.
    In `raw` mode it's a placeholder to send a user-supplied probe.
    """
    if mode == 'elm':
        resp = elm_send_obd(device, '0100', baud=baud, timeout=timeout)
        # normalize and return parsed PID response
        try:
            raw = parse_elm_echo_strip(resp)
            return raw
        except Exception:
            return resp
    else:
        # raw mode: the caller should use send_raw
        return b''


def read_dtc(device, mode='elm', baud=115200, timeout=1.0):
    """Read stored DTCs. In `elm` mode sends service 03.

    Returns raw response bytes; parsing is left to higher layer.
    """
    if mode == 'elm':
        resp = elm_send_obd(device, '03', baud=baud, timeout=timeout)
        raw = parse_elm_echo_strip(resp)
        dtcs = parse_obd_03_response(raw)
        return dtcs
    else:
        return b''


def clear_dtc(device, mode='elm', baud=115200, timeout=1.0):
    """Clear stored DTCs. In ELM/OBD use service 04 (reset DTCs). Returns True on ACK-like response."""
    if mode == 'elm':
        resp = elm_send_obd(device, '04', baud=baud, timeout=timeout)
        # If adapter returns '44' or OK, consider success. Simple heuristic:
        raw = parse_elm_echo_strip(resp)
        if raw and (raw.find(b"\x44") != -1 or b'OK' in resp.upper()):
            return True
        return False
    return False


def send_raw_hex(device, hexstr, baud=115200, timeout=1.0):
    """Send raw hex bytes (binary) and return response bytes."""
    # hexstr like '22 f1 90' or '22F190'
    s = hexstr.replace(' ', '')
    data = binascii.unhexlify(s)
    with SerialComm(device, baud=baud, timeout=timeout) as ser:
        return ser.send_bytes(data)


def read_measure(device, pid_cmd, baud=115200, timeout=1.0):
    """Read a measuring block / PID using OBD mode (e.g., '01 0C' for RPM). Returns raw bytes or parsed value.

    This is a convenience wrapper; higher-level parsing depends on the PID.
    """
    # send ascii OBD command without spaces (ELM accepts both)
    cmd = pid_cmd.replace(' ', '')
    resp = elm_send_obd(device, cmd, baud=baud, timeout=timeout)
    raw = parse_elm_echo_strip(resp)
    return raw
