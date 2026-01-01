from fastapi import APIRouter, Query
from typing import List
from ..simulator import make_iso_tp_frames, reassemble_iso_tp_frames
import binascii

router = APIRouter(prefix='/api/sim', tags=['sim'])


def _hex(b: bytes) -> str:
    return binascii.hexlify(b).decode('ascii')


@router.get('/frames')
def frames(payload: str = Query(..., description='hex payload, e.g. 0A0B0C'), mtu: int = 8):
    """Return ISO-TP frames for the supplied hex payload."""
    data = binascii.unhexlify(payload.replace(' ', ''))
    fr = make_iso_tp_frames(data, can_mtu=mtu)
    return {'payload_len': len(data), 'frames': [ _hex(f) for f in fr ]}


@router.get('/reassemble')
def reassemble(frames: List[str] = Query(..., description='list of frames as hex strings')):
    """Reassemble a list of ISO-TP frames (hex) and return the payload."""
    raw = [binascii.unhexlify(f.replace(' ', '')) for f in frames]
    out = reassemble_iso_tp_frames(raw)
    return {'payload_hex': _hex(out), 'len': len(out)}


@router.get('/run-tests')
def run_tests():
    """Run lightweight simulator tests and return pass/fail."""
    tests = [b'hello', b'x'*50, b'0123456789ABCDEF0123456789']
    results = []
    for t in tests:
        fr = make_iso_tp_frames(t, can_mtu=8)
        out = reassemble_iso_tp_frames(fr)
        results.append({'payload_len': len(t), 'frames': len(fr), 'ok': out == t})
    ok = all(r['ok'] for r in results)
    return {'ok': ok, 'results': results}
