from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import tempfile
from pathlib import Path
from typing import Any

app = FastAPI(title='vlinker-web')

# serve the static UI
static_dir = Path(__file__).parent / 'static'
if static_dir.exists():
    app.mount('/', StaticFiles(directory=str(static_dir), html=True), name='static')


@app.post('/api/profile/analyze')
async def api_profile_analyze(path: str | None = None, upload: UploadFile | None = None) -> Any:
    from vlinker.profile_builder import analyze_capture
    if upload:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            shutil.copyfileobj(upload.file, tmp)
            tmp.flush()
            result = analyze_capture(tmp.name)
        finally:
            tmp.close()
        return {'suggestions': result}
    if not path:
        raise HTTPException(status_code=400, detail='path or upload required')
    res = analyze_capture(path)
    return {'suggestions': res}


@app.post('/api/profile/build')
async def api_profile_build(path: str, name: str, algo: str) -> Any:
    from vlinker.profile_builder import analyze_capture, save_profile_from_suggestion
    res = analyze_capture(path)
    if not res:
        raise HTTPException(status_code=404, detail='no suggestions found')
    suggestion = res[0]
    out = save_profile_from_suggestion(name, suggestion, algo)
    if not out:
        raise HTTPException(status_code=500, detail='failed to save profile')
    return {'profile_path': out}


@app.post('/api/diag/read-dtc')
async def api_diag_read_dtc(device: str, mode: str = 'elm', baud: int = 115200, timeout: float = 1.0) -> Any:
    from vlinker.diag import read_dtc
    dtcs = read_dtc(device, mode=mode, baud=baud, timeout=timeout)
    return {'dtcs': dtcs}


@app.post('/api/adv/req-seed')
async def api_adv_req_seed(device: str, baud: int = 115200, timeout: float = 1.0) -> Any:
    from vlinker.advanced import request_seed
    seed = request_seed(device, baud=baud, timeout=timeout)
    return {'seed_hex': seed.hex() if seed else None}


@app.post('/api/adv/send-key')
async def api_adv_send_key(device: str, key_hex: str, baud: int = 115200, timeout: float = 1.0) -> Any:
    from vlinker.advanced import send_key
    key = bytes.fromhex(key_hex.replace(' ', ''))
    resp = send_key(device, key, baud=baud, timeout=timeout)
    return {'response_hex': resp.hex() if resp else None}


@app.post('/api/capture/upload')
async def api_capture_upload(file: UploadFile = File(...)) -> Any:
    tmpdir = tempfile.mkdtemp(prefix='vlinker-upload-')
    outpath = Path(tmpdir) / file.filename
    with open(outpath, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    return {'path': str(outpath)}


@app.get('/ui')
async def ui_index():
    idx = static_dir / 'index.html'
    if idx.exists():
        return FileResponse(idx)
    raise HTTPException(status_code=404)
