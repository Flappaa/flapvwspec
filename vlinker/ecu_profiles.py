"""ECU profiles and seed/key algorithm hooks.

This module provides a registry of ECU profiles. Each profile can include a
`seed_key_algo` callable that takes seed bytes and returns key bytes. If the
algorithm is None, the CLI will fall back to manual key entry.

IMPORTANT: Provided algorithms are placeholders for testing only. Real
algorithms for specific ECUs require reverse engineering or vendor data.
"""
from typing import Callable, Optional, Dict


def demo_reverse_seed_algo(seed: bytes) -> bytes:
    """Demo algorithm: return reversed seed (placeholder only)."""
    return seed[::-1]


_PROFILES: Dict[str, Dict] = {
    'vw_generic': {
        'name': 'VW Generic (demo)',
        'seed_key_algo': demo_reverse_seed_algo,
        'notes': 'Demo profile: seed->key is reverse; replace with real algo for production.'
    },
    'manual': {
        'name': 'Manual entry',
        'seed_key_algo': None,
        'notes': 'No algorithm: operator must supply key manually.'
    }
}


# Additional demo profiles (placeholders only)
def xor_with_constant(const: int):
    def _algo(seed: bytes) -> bytes:
        return bytes([(b ^ const) & 0xFF for b in seed])
    return _algo


_PROFILES.update({
    'bosch_demo': {
        'name': 'Bosch demo profile',
        'seed_key_algo': xor_with_constant(0x5A),
        'notes': 'Placeholder XOR algorithm for testing only.'
    },
    'siemens_demo': {
        'name': 'Siemens demo profile',
        'seed_key_algo': lambda s: s[::-1] if s else b'',
        'notes': 'Another placeholder; replace with real algorithm after capture.'
    },
})


def list_profiles():
    return list(_PROFILES.keys())


def get_profile(name: str) -> Optional[Dict]:
    return _PROFILES.get(name)
