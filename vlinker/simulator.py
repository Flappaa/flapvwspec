"""Simple ISO-TP frame generator and reassembler for testing.

This is a small helper to create CAN-like 8-byte ISO-TP frames
and reassemble them. It's intended for offline tests and simulator
workflows and does not attempt to be a full ISO-TP stack.
"""
from typing import List


def make_iso_tp_frames(payload: bytes, can_mtu: int = 8) -> List[bytes]:
    """Generate ISO-TP frames (single-frame or multi-frame) for a payload.

    - Single Frame (SF): first byte = payload length (0x00..0x07), remaining bytes = payload
    - First Frame (FF): first byte = 0x10 | ((len>>8) & 0x0F), second byte = len & 0xFF
      remaining bytes are payload (up to can_mtu-2)
    - Consecutive Frame (CF): first byte = 0x20 | (seq & 0x0F), remaining bytes follow

    Returns list of raw frame bytes (each length = can_mtu).
    """
    if can_mtu < 3:
        raise ValueError('can_mtu must be >=3')
    plen = len(payload)
    frames: List[bytes] = []
    if plen <= (can_mtu - 1):
        # Single Frame
        pci = plen & 0x0F
        data = bytes([pci]) + payload
        data = data.ljust(can_mtu, b"\x00")
        frames.append(data)
        return frames

    # Multi-frame
    # First Frame: 2-byte PCI
    ff_payload_space = can_mtu - 2
    ff_len_upper = (plen >> 8) & 0x0F
    ff_len_lower = plen & 0xFF
    pci0 = 0x10 | ff_len_upper
    first = bytes([pci0, ff_len_lower]) + payload[:ff_payload_space]
    first = first.ljust(can_mtu, b"\x00")
    frames.append(first)

    # Consecutive frames
    seq = 1
    offset = ff_payload_space
    cf_payload_space = can_mtu - 1
    while offset < plen:
        chunk = payload[offset:offset + cf_payload_space]
        pci = 0x20 | (seq & 0x0F)
        cf = bytes([pci]) + chunk
        cf = cf.ljust(can_mtu, b"\x00")
        frames.append(cf)
        offset += cf_payload_space
        seq = (seq + 1) & 0x0F

    return frames


def reassemble_iso_tp_frames(frames: List[bytes]) -> bytes:
    """Reassemble payload bytes from a list of ISO-TP frames.

    Accepts frames in order (as produced by make_iso_tp_frames).
    Performs minimal validation of PCI bytes.
    """
    if not frames:
        return b""
    first = frames[0]
    pci0 = first[0]
    if (pci0 & 0xF0) == 0x00:
        # Single Frame
        length = pci0 & 0x0F
        return first[1:1 + length]

    if (pci0 & 0xF0) == 0x10:
        # First Frame
        upper = pci0 & 0x0F
        length = (upper << 8) | first[1]
        ff_payload = first[2:]
        out = bytearray()
        out.extend(ff_payload)
        expected = length
        # append from CFs
        for cf in frames[1:]:
            pci = cf[0]
            if (pci & 0xF0) != 0x20:
                raise ValueError('Expected Consecutive Frame')
            out.extend(cf[1:])
        return bytes(out[:expected])

    raise ValueError('Unknown PCI type')
