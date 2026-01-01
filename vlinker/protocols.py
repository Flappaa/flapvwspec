"""Protocol helpers: parse OBD/ELM and basic UDS/KWP response parsing.

This module provides small, well-documented helpers for decoding OBD-II/ELM
responses (service 03) into DTC codes, and utilities used by the diagnostics
helpers.
"""
from typing import List, Tuple


def _bytes_to_dtc(b1: int, b2: int) -> str:
    # Convert two bytes into an OBD-II DTC string like P0123
    # Per SAE J2012: first two bits define the first letter
    high = b1
    first_char_map = {0: 'P', 1: 'C', 2: 'B', 3: 'U'}
    first = (high & 0xC0) >> 6
    letter = first_char_map.get(first, '?')
    code = ((high & 0x3F) << 8) | b2
    return f"{letter}{code:04X}"


def parse_obd_03_response(resp: bytes) -> List[str]:
    """Parse an OBD service 03 response (read stored DTCs) into DTC strings.

    Expects raw bytes returned from ELM ASCII response decoded to binary bytes.
    Returns list of DTC strings, empty list if none.
    """
    if not resp:
        return []
    # Some ELMs echo ASCII hex; accept either pure binary or ASCII hex
    # If resp contains ASCII hex chars, strip whitespace and decode
    try:
        # If bytes look like ascii hex (only 0-9A-F and spaces/newlines)
        if all((32 <= b <= 127) for b in resp):
            s = ''.join(chr(b) for b in resp).strip()
            # remove non-hex characters
            import re
            s2 = re.sub(r'[^0-9A-Fa-f]', '', s)
            if len(s2) % 2 == 1:
                # odd length, drop last
                s2 = s2[:-1]
            raw = bytes.fromhex(s2)
        else:
            raw = resp
    except Exception:
        raw = resp

    # OBD 03 response format: first byte is header (0x43 for 03), then pairs
    # Some adapters include mode echo or length bytes; try to locate 0x43
    idx = raw.find(b"\x43")
    if idx == -1:
        # try 0x03 response in UDS/ISO-TP style (0x03 may not appear)
        # fallback: parse sequential pairs from start
        idx = 0
    i = idx + 1
    dtcs = []
    while i + 1 < len(raw):
        b1 = raw[i]
        b2 = raw[i + 1]
        if b1 == 0 and b2 == 0:
            break
        dtcs.append(_bytes_to_dtc(b1, b2))
        i += 2
    return dtcs


def parse_elm_echo_strip(resp: bytes) -> bytes:
    """Strip common ELM echo and prompt characters, return binary bytes when possible."""
    if not resp:
        return b''
    try:
        text = resp.decode('ascii', errors='ignore')
        # Remove prompt '>' and whitespace
        text = text.replace('>', '').replace('\r', '').replace('\n', ' ').strip()
        import re
        s2 = re.sub(r'[^0-9A-Fa-f]', '', text)
        if len(s2) % 2 == 1:
            s2 = s2[:-1]
        return bytes.fromhex(s2)
    except Exception:
        return resp
