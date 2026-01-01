from pathlib import Path
import json
import re
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from vlinker import profile_builder

router = APIRouter()


class BuildRequest(BaseModel):
    path: str
    name: str
    algo: str
    dry_run: bool = True
    force: bool = False


def _safe_name(name: str) -> str:
    # allow letters, numbers, underscore and dash
    if not re.match(r'^[A-Za-z0-9_-]{3,64}$', name):
        raise ValueError('invalid profile name')
    return name


def _profiles_dir() -> Path:
    # save profiles under the package profiles folder
    root = Path(__file__).resolve().parents[2]
    p = root / 'vlinker' / 'profiles'
    p.mkdir(parents=True, exist_ok=True)
    return p


def _captures_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    p = root / 'captures'
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.post('/api/capture/upload')
async def upload_capture(upload: UploadFile = File(...)):
    caps = _captures_dir()
    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', upload.filename)
    dest = caps / safe
    contents = await upload.read()
    try:
        dest.write_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'failed to save capture: {e}')
    return {'path': str(dest)}


@router.get('/api/profile/list')
def list_profiles():
    pdir = _profiles_dir()
    profiles = []
    for f in pdir.glob('*.py'):
        profiles.append({'name': f.stem, 'path': str(f)})
    return {'profiles': profiles}


@router.get('/api/profile/preview')
def preview_profile(name: str):
    try:
        name = _safe_name(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    p = _profiles_dir() / f'{name}.py'
    if not p.exists():
        raise HTTPException(status_code=404, detail='profile not found')
    try:
        txt = p.read_text()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'failed to read profile: {e}')
    return {'name': name, 'content': txt}


@router.post('/api/profile/build')
def build_profile(req: BuildRequest):
    # validate name
    try:
        name = _safe_name(req.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # validate capture path exists and is inside project
    cap = Path(req.path)
    root = Path(__file__).resolve().parents[2]
    try:
        cap = cap.resolve()
    except Exception:
        raise HTTPException(status_code=400, detail='invalid path')

    if not str(cap).startswith(str(root)):
        raise HTTPException(status_code=400, detail='capture path must be inside project')
    if not cap.exists():
        raise HTTPException(status_code=404, detail='capture file not found')

    # build a richer preview using profile_builder if available
    preview = None
    try:
        # prefer an explicit preview API if present
        if hasattr(profile_builder, 'save_profile_from_suggestion'):
            preview = profile_builder.save_profile_from_suggestion(
                capture_path=str(cap), name=name, algo=req.algo, dry_run=True
            )
        # also include analysis suggestions when available
        if hasattr(profile_builder, 'analyze_capture'):
            try:
                analysis = profile_builder.analyze_capture(str(cap))
            except Exception:
                analysis = None
            if isinstance(preview, dict):
                preview.setdefault('analysis', analysis)
            else:
                preview = {'name': name, 'algo': req.algo, 'analysis': analysis}
    except Exception:
        # non-fatal: produce a minimal preview
        preview = {'name': name, 'algo': req.algo, 'notes': 'preview generated (fallback)'}

    profiles_dir = _profiles_dir()
    profile_path = profiles_dir / f'{name}.py'

    if req.dry_run:
        return {'preview': preview, 'profile_path': str(profile_path), 'written': False}

    if not req.force:
        raise HTTPException(status_code=403, detail='force flag required to write profile')

    # write the profile file atomically
    try:
        # If preview is a dict, produce a Python profile file template
        if isinstance(preview, dict):
            header = f"# Generated profile: {name}\n# algo: {req.algo}\n\n"
            body = f"PROFILE = {json.dumps(preview, indent=2)}\n"
            content = header + body
        else:
            content = str(preview)
        tmp = profile_path.with_suffix('.tmp')
        tmp.write_text(content)
        tmp.replace(profile_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'failed to write profile: {e}')

    return {'preview': preview, 'profile_path': str(profile_path), 'written': True}
