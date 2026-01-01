"""Profile builder: heuristic analysis of capture files to propose seed->key algorithms.

This module provides simple heuristics (identity, reverse, XOR constant, rotate)
to propose candidate algorithms from captured seed/response pairs. Results are
suggestions only and must be validated on a vehicle.
"""
from typing import List, Tuple, Optional
from .capture_parser import parse_capture_file, find_seed_requests
from .ecu_profiles import _PROFILES
import os


def _xor_const(seed: bytes, const: int) -> bytes:
    return bytes([(b ^ const) & 0xFF for b in seed])


def _reverse(seed: bytes) -> bytes:
    return seed[::-1]


def _identity(seed: bytes) -> bytes:
    return bytes(seed)


def _rotl(seed: bytes, n: int) -> bytes:
    out = bytearray()
    for b in seed:
        out.append(((b << n) & 0xFF) | ((b >> (8 - n)) & 0xFF))
    return bytes(out)


def analyze_capture(path: str) -> List[dict]:
    parsed = parse_capture_file(path)
    pairs = find_seed_requests(parsed)
    suggestions = []
    for ts, req, resp in pairs:
        # attempt to extract seed bytes from response heuristically
        seed = b''
        if resp and resp[0] == 0x67 and len(resp) > 2:
            # positive 27 response: 0x67 <subfunc> <seed...>
            seed = resp[2:]
        elif resp and len(resp) >= 2:
            seed = resp[1:]

        if not seed:
            continue

        cand = {
            'ts': ts,
            'seed_hex': seed.hex(),
            'candidates': []
        }
        # identity
        cand['candidates'].append({'name': 'identity', 'key_hex': _identity(seed).hex()})
        # reverse
        cand['candidates'].append({'name': 'reverse', 'key_hex': _reverse(seed).hex()})
        # rotate 1..3
        for n in (1, 2, 3):
            cand['candidates'].append({'name': f'rotl_{n}', 'key_hex': _rotl(seed, n).hex()})
        # xor few constants
        for c in (0x5A, 0xA5, 0xFF, 0x01, 0x55):
            cand['candidates'].append({'name': f'xor_{c:02X}', 'key_hex': _xor_const(seed, c).hex(), 'const': c})

        suggestions.append(cand)
    return suggestions


def _propose_from_seed(seed: bytes) -> List[dict]:
    """Given a seed, propose likely key transforms (name + key_hex)."""
    if not seed:
        return []
    proposals = []
    # identity
    proposals.append({'name': 'identity', 'key_hex': seed.hex()})
    # reverse
    proposals.append({'name': 'reverse', 'key_hex': seed[::-1].hex()})
    # rotl 1..3
    for n in (1, 2, 3):
        out = bytearray()
        for b in seed:
            out.append(((b << n) & 0xFF) | ((b >> (8 - n)) & 0xFF))
        proposals.append({'name': f'rotl_{n}', 'key_hex': bytes(out).hex()})
    # xor with common constants and repeating small keys
    for c in (0x5A, 0xA5, 0xFF, 0x01, 0x55):
        proposals.append({'name': f'xor_{c:02X}', 'key_hex': _xor_const(seed, c).hex(), 'const': c})
    # small repeating-key xor of length 2..4 by trying first bytes
    for klen in (2, 3, 4):
        if len(seed) >= klen:
            key = bytes([seed[i] ^ seed[i % klen] for i in range(klen)])
            if any(key):
                proposals.append({'name': f'rep_xor_{klen}', 'key_hex': _xor_const(seed, key[0]).hex(), 'key_bytes': key.hex()})
    return proposals


def interactive_build(capture_path: str) -> str:
    """Interactive flow: analyze capture, prompt user to choose candidate, save profile.

    Returns path to written profile or empty string if aborted.
    """
    suggestions = analyze_capture(capture_path)
    if not suggestions:
        print('No suggestions found in capture.')
        return ''
    # Present each suggestion and candidate proposals
    for idx, s in enumerate(suggestions):
        print(f"[{idx}] Seed at {s['ts']}: {s['seed_hex']}")
        cands = _propose_from_seed(bytes.fromhex(s['seed_hex']))
        for j, c in enumerate(cands):
            print(f"   ({j}) {c['name']} -> {c['key_hex']}")
    try:
        sel = input('Choose suggestion index (or q to quit): ').strip()
        if sel.lower() == 'q':
            return ''
        sel_i = int(sel)
        chosen = suggestions[sel_i]
    except Exception:
        print('Invalid selection')
        return ''
    cands = _propose_from_seed(bytes.fromhex(chosen['seed_hex']))
    try:
        sel2 = input('Choose candidate index to use as algorithm (or q to quit): ').strip()
        if sel2.lower() == 'q':
            return ''
        sel_j = int(sel2)
        cand = cands[sel_j]
    except Exception:
        print('Invalid candidate')
        return ''
    prof_name = input('Enter profile name to save (e.g. my_vw_profile): ').strip()
    if not prof_name:
        print('No name provided; aborting')
        return ''
    # map candidate to algo_name expected by save_profile_from_suggestion
    algo_name = cand['name']
    path = save_profile_from_suggestion(prof_name, chosen, algo_name)
    if path:
        print('Profile saved to', path)
        return path
    print('Failed to save profile')
    return ''


def save_profile_from_suggestion(name: str, suggestion: dict, algo_name: str, out_dir: str = None) -> Optional[str]:
    """Save a simple profile using the chosen algorithm name from suggestion.

    algo_name should match one of the candidate names (e.g., 'reverse' or 'xor_5A').
    This writes a new Python file under `vlinker/profiles/<name>.py` containing
    a small profile that uses the chosen demo algorithm.
    Returns path to saved file or None on error.
    """
    out_dir = out_dir or os.path.join(os.path.dirname(__file__), 'profiles')
    os.makedirs(out_dir, exist_ok=True)
    chosen = None
    for c in suggestion.get('candidates', []):
        if c['name'] == algo_name:
            chosen = c
            break
    if not chosen:
        return None

    # Map algo_name to a callable pattern
    algo_code = ''
    if algo_name == 'reverse':
        algo_code = 'demo_reverse_seed_algo'
        import_line = 'from ..ecu_profiles import demo_reverse_seed_algo'
    elif algo_name.startswith('xor_'):
        const = chosen.get('const', 0x5A)
        algo_code = f"(lambda s: bytes([(b ^ {const}) & 0xFF for b in s]))"
        import_line = ''
    elif algo_name == 'identity':
        algo_code = '(lambda s: bytes(s))'
        import_line = ''
    else:
        # fallback to identity
        algo_code = '(lambda s: bytes(s))'
        import_line = ''

    fname = os.path.join(out_dir, f"{name}.py")
    with open(fname, 'w') as f:
        f.write('"""Auto-generated ECU profile from capture analysis."""\n')
        if import_line:
            f.write(import_line + '\n')
        f.write('\n')
        f.write('PROFILE = {\n')
        f.write(f"    'name': '{name}',\n")
        f.write(f"    'seed_key_algo': {algo_code},\n")
        f.write("    'notes': 'Auto-generated from capture. Validate before use.'\n")
        f.write('}\n')
    return fname
