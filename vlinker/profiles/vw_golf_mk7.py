"""VW Golf Mk7 ECU profile (example).

This profile contains metadata, common identifiers and a placeholder seed/key
algorithm for testing. Replace or extend with verified algorithms obtained
from captures or vendor documentation before using on real vehicles.
"""
from ..ecu_profiles import demo_reverse_seed_algo

PROFILE = {
    'name': 'VW Golf Mk7 (example)',
    'year_range': (2013, 2019),
    'modules': {
        # Example identifier -> friendly name mapping
        'F190': 'Central Electronics (Coding longcoding)',
        '0100': 'Engine (OBD)',
    },
    'seed_key_algo': demo_reverse_seed_algo,
    'notes': 'Example profile. Use only for testing; update with real algorithms.'
}
