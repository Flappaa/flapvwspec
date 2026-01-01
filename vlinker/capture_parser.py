from typing import List, Tuple


def parse_capture_file(path: str) -> List[Tuple[str, str, bytes]]:
    """Parse a capture file created by `capture.start_capture`.

    Returns a list of tuples (timestamp_str, direction, data_bytes).
    """
    out = []
    with open(path, 'rb') as f:
        for raw in f:
            line = raw.decode('ascii', errors='ignore').strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) != 3:
                continue
            ts, direction, hexstr = parts
            try:
                data = bytes.fromhex(hexstr)
            except Exception:
                data = b''
            out.append((ts, direction, data))
    return out


def find_seed_requests(parsed: List[Tuple[str, str, bytes]]) -> List[Tuple[str, bytes, bytes]]:
    """Find UDS/seed requests (service 0x27) and their immediate responses.

    Returns a list of tuples (timestamp_request, seed_bytes, response_bytes).
    This is a heuristic: looks for read entries where data starts with 0x27.
    """
    results = []
    for i, (ts, dir, data) in enumerate(parsed):
        if dir != 'R' or not data:
            continue
        # check for seed request 0x27 XX (seed request subfunc)
        if data[0] == 0x27:
            # find next non-empty read response
            resp = b''
            for j in range(i + 1, min(i + 6, len(parsed))):
                _ts, _dir, _data = parsed[j]
                if _dir == 'R' and _data:
                    resp = _data
                    break
            # seed is likely in response; return pair
            results.append((ts, data, resp))
    return results
