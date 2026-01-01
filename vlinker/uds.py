import time
import binascii
from typing import Optional

from .serial_comm import SerialComm
from .logger import get_logger
from .iso_tp import send_iso_tp

logger = get_logger(__name__)


def _hexdump(b: bytes) -> str:
    return binascii.hexlify(b).decode('ascii')


def send_uds_raw(device: str, hex_payload: str, baud: int = 115200, timeout: float = 2.0) -> bytes:
    """Send raw UDS payload (hex string) and return raw bytes response.

    This is a simple wrapper using `SerialComm.send_hex`. It does not implement
    a full ISO-TP stack; for most adapters that accept hex frames directly this works.
    """
    # for larger payloads or when adapter supports ISO-TP, use ISO-TP helper
    try:
        return send_iso_tp(device, hex_payload, baud=baud, timeout=timeout)
    except Exception:
        sc = SerialComm(device, baud=baud, timeout=timeout)
        sc.open()
        try:
            resp = sc.send_hex(hex_payload)
            return resp
        finally:
            sc.close()


def tester_present(device: str, baud: int = 115200, timeout: float = 1.0) -> bytes:
    # UDS TesterPresent is 0x3E 0x00 (request), positive response 0x7E
    return send_uds_raw(device, '023E00', baud=baud, timeout=timeout)


def read_dtc_uds(device: str, baud: int = 115200, timeout: float = 3.0) -> str:
    # UDS ReadDTCInformation: service 0x19, subfunction 0x02 (ReportDTCByStatusMask)
    # Send UDS request and parse the response into a list of DTCs where possible.
    try:
        resp = send_uds_raw(device, '021902', baud=baud, timeout=timeout)
    except Exception:
        resp = send_uds_raw(device, '1902', baud=baud, timeout=timeout)
    # attempt to parse positive response (0x59)
    try:
        b = resp
        # find 0x59 in response
        idx = None
        for i in range(len(b)):
            if b[i] == 0x59:
                idx = i
                break
        if idx is None:
            return _hexdump(b)
        # payload after 0x59
        payload = b[idx+1:]
        # each DTC entry is commonly 3 bytes (MSB, MID, LSB) plus a status byte sometimes
        dtcs = []
        i = 0
        while i+2 < len(payload):
            dtc_bytes = payload[i:i+3]
            dtc_hex = ''.join(f"{x:02X}" for x in dtc_bytes)
            dtcs.append(dtc_hex)
            i += 3
            # optional status byte
            if i < len(payload) and payload[i] <= 0xFF:
                i += 1
        return ','.join(dtcs) if dtcs else _hexdump(b)
    except Exception:
        return _hexdump(resp)


def clear_dtc_uds(device: str, baud: int = 115200, timeout: float = 3.0) -> str:
    # UDS ClearDiagnosticInformation is 0x14. Request: 02 14 00 (clear all)
    try:
        resp = send_uds_raw(device, '021400', baud=baud, timeout=timeout)
    except Exception:
        resp = send_uds_raw(device, '1400', baud=baud, timeout=timeout)
    return _hexdump(resp)


def read_measure_uds(device: str, pid_hex: str, baud: int = 115200, timeout: float = 2.0) -> str:
    # Example service: 0x22 ReadDataByIdentifier (two-byte DID). If pid_hex is DID.
    # Accept pid_hex like 'F190' or '00F1'
    # build payload: length + 0x22 + DID
    payload = '22' + pid_hex
    try:
        resp = send_uds_raw(device, payload, baud=baud, timeout=timeout)
    except Exception:
        resp = b''
    return _hexdump(resp)


def parse_dtc_bytes(resp: bytes):
    """Parse a raw UDS positive response payload (bytes after 0x59) into DTC entries.

    This performs minimal, robust parsing and returns a list of dicts with
    - raw: hex string of the 3-byte DTC
    - status: optional status byte (if present after the DTC)
    - code: best-effort human string (falls back to raw)

    The function is non-destructive and tolerant of variable-length payloads.
    """
    out = []
    if not resp:
        return out
    i = 0
    L = len(resp)
    while i + 2 < L:
        dtc_bytes = resp[i:i+3]
        raw = ''.join(f"{b:02X}" for b in dtc_bytes)
        # best-effort code: present the bytes and a short hex label
        code = f"DTC_{raw}"
        entry = {'raw': raw, 'code': code}
        i += 3
        # optional status byte: if available and looks like a status (0x00-0xFF)
        if i < L:
            status = resp[i]
            entry['status'] = f"0x{status:02X}"
            i += 1
        out.append(entry)
    return out


def decode_did_value(did: int, data: bytes):
    """Decode a DID value into a best-effort representation.

    Returns a dict with raw hex, length, and ascii if printable.
    Non-breaking: does not raise on malformed input.
    """
    result = {'did': f"0x{did:04X}", 'len': len(data), 'raw': _hexdump(data)}
    try:
        s = data.decode('ascii')
        # only show ascii if it's mostly printable
        printable = sum(1 for ch in s if 32 <= ord(ch) < 127)
        if printable >= len(s) * 0.6 and len(s) > 0:
            result['ascii'] = s
    except Exception:
        pass
    return result
