"""VW helpers: long-coding utilities and simple coding scaffolding.

These helpers handle conversions between long-coding hex strings and bytes,
allow reading/setting individual bits, and provide a small helper to prepare
coding write payloads. They intentionally do not implement vehicle-specific
mapping — that must be provided by the user or created from VCDS data.
"""
from typing import Tuple


def longcoding_str_to_bytes(s: str) -> bytes:
    """Convert a long-coding hex string to bytes.

    Accepts strings like '0123456789ABCDEF' or with spaces '01 23 45'.
    Returns a bytes object representing the coding.
    """
    s2 = ''.join(s.split())
    if len(s2) % 2 == 1:
        s2 = '0' + s2
    return bytes.fromhex(s2)


def bytes_to_longcoding_str(b: bytes) -> str:
    """Convert coding bytes to an uppercase hex string without spaces."""
    return ''.join(f"{x:02X}" for x in b)


def get_longcoding_bit(coding: bytes, byte_index: int, bit_index: int) -> int:
    """Get a single bit from coding bytes.

    byte_index: 0-based index into coding bytes.
    bit_index: 0..7 (0 is least-significant bit).
    Returns 0 or 1.
    """
    if byte_index < 0 or byte_index >= len(coding):
        raise IndexError('byte_index out of range')
    b = coding[byte_index]
    return (b >> bit_index) & 1


def set_longcoding_bit(coding: bytes, byte_index: int, bit_index: int, value: int) -> bytes:
    """Return a new bytes object with the requested bit set to value (0/1)."""
    if value not in (0, 1):
        raise ValueError('value must be 0 or 1')
    arr = bytearray(coding)
    if byte_index < 0 or byte_index >= len(arr):
        raise IndexError('byte_index out of range')
    mask = 1 << bit_index
    if value:
        arr[byte_index] |= mask
    else:
        arr[byte_index] &= (~mask) & 0xFF
    return bytes(arr)


def update_longcoding_bytes(coding: bytes, updates: Tuple[Tuple[int, int, int], ...]) -> bytes:
    """Apply multiple updates and return new coding bytes.

    updates: iterable of (byte_index, bit_index, value)
    """
    arr = bytearray(coding)
    for byte_index, bit_index, value in updates:
        if value not in (0, 1):
            raise ValueError('value must be 0 or 1')
        if byte_index < 0 or byte_index >= len(arr):
            raise IndexError('byte_index out of range')
        mask = 1 << bit_index
        if value:
            arr[byte_index] |= mask
        else:
            arr[byte_index] &= (~mask) & 0xFF
    return bytes(arr)


def prepare_coding_write_payload(identifier_hex: str, coding_bytes: bytes) -> str:
    """Prepare a hex payload for a UDS writeDataByIdentifier (0x2E) or similar.

    identifier_hex: string of the identifier (e.g., 'F190').
    Returns a hex string (no spaces) suitable for `send_uds_raw`.
    """
    id_clean = ''.join(identifier_hex.split()).upper()
    if len(id_clean) % 2 == 1:
        raise ValueError('identifier_hex must have even length')
    payload = id_clean + ''.join(f"{b:02X}" for b in coding_bytes)
    # prefix with service 2E
    return '2E' + payload
