"""Advanced diagnostic helpers: security access (seed/key), coding/adaptation wrappers.

This module provides conservative, generic helpers to perform UDS-like security
seed/key requests and send raw UDS diagnostic requests. These are intentionally
generic: real vehicle-specific key algorithms are not implemented here — the
module provides the messaging scaffolding so you can plug in a key algorithm
or enter the key manually during testing.
"""
from .serial_comm import SerialComm
from .protocols import parse_elm_echo_strip
from .ecu_profiles import get_profile
import time


def request_seed(device, sub_function=0x01, baud=115200, timeout=1.0):
    """Request security seed using UDS service 0x27 with given sub-function.

    Sends ASCII hex '27 XX' and returns raw response bytes (seed) or None.
    """
    cmd = f"27{int(sub_function):02X}"
    with SerialComm(device, baud=baud, timeout=timeout) as s:
        resp = s.send_hex(cmd)
        # normalize ELM ascii to binary when possible
        raw = parse_elm_echo_strip(resp)
        return raw


def send_key(device, key_bytes: bytes, sub_function=0x02, baud=115200, timeout=1.0):
    """Send security key using UDS service 0x27 sub-function 0x02 + key bytes.

    Returns response bytes.
    """
    hexstr = ''.join(f"{b:02X}" for b in key_bytes)
    cmd = f"27{int(sub_function):02X}{hexstr}"
    with SerialComm(device, baud=baud, timeout=timeout) as s:
        resp = s.send_hex(cmd)
        raw = parse_elm_echo_strip(resp)
        return raw


def security_access_with_profile(device, profile_name: str, sub_function=0x01, baud=115200, timeout=1.0):
    """Perform seed/key security access using a named profile.

    If the profile defines `seed_key_algo`, it's called with the seed bytes to
    produce the key which is then sent. If the profile's algo is None, the
    function returns the seed so the operator can compute and call `send_key`.
    Returns a dict with keys: `seed`, `key`, `response`, `mode`.
    """
    profile = get_profile(profile_name)
    if not profile:
        raise ValueError('Unknown profile: ' + profile_name)
    seed = request_seed(device, sub_function=sub_function, baud=baud, timeout=timeout)
    result = {'seed': seed, 'key': None, 'response': None, 'mode': 'manual'}
    algo = profile.get('seed_key_algo')
    if algo:
        # compute key and send
        try:
            key = algo(seed or b'')
        except Exception as e:
            raise RuntimeError('Profile algorithm failed: ' + str(e))
        result['key'] = key
        resp = send_key(device, key, sub_function=sub_function, baud=baud, timeout=timeout)
        result['response'] = resp
        result['mode'] = 'auto'
    else:
        # manual mode; return seed and let user compute key
        result['mode'] = 'manual'
    return result


def send_uds_raw(device, hex_payload: str, baud=115200, timeout=1.0):
    """Send a raw UDS hex payload (no spaces) and return normalized response bytes."""
    with SerialComm(device, baud=baud, timeout=timeout) as s:
        resp = s.send_hex(hex_payload)
        raw = parse_elm_echo_strip(resp)
        return raw


def perform_coding_write(device, identifier_hex: str, data_bytes: bytes, baud=115200, timeout=1.0, dry_run: bool=False):
    """Generic coding write using UDS 0x2E (writeDataByIdentifier) or similar.

    identifier_hex: 'F190' (example D/I) or similar. data_bytes appended.
    If `dry_run` is True the prepared payload (hex string) is returned and
    no request is sent to the device.
    Returns raw response bytes or payload string when dry_run=True.
    """
    hex_data = ''.join(f"{b:02X}" for b in data_bytes)
    cmd = f"2E{identifier_hex}{hex_data}"
    if dry_run:
        # return prepared payload (no send)
        return cmd
    return send_uds_raw(device, cmd, baud=baud, timeout=timeout)
