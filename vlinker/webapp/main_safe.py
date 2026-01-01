from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from .profile_build import router as build_router
from .diag_api import router as diag_router
from .sim_api import router as sim_router


app = FastAPI(title='vlinker webapp (safe)')

# include the build router (provides /api/profile/build)
app.include_router(build_router)
app.include_router(diag_router)
app.include_router(sim_router)

# simple health endpoint
@app.get('/api/health')
def health():
    return {'status': 'ok'}

# mount static UI at root if present
static_dir = os.path.join(os.path.dirname(__file__), 'static')
if os.path.isdir(static_dir):
    app.mount('/', StaticFiles(directory=static_dir, html=True), name='static')
