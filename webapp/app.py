from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from webapp.app_state import configure_app_state
from webapp.routes_api import router as api_router
from webapp.routes_pages import router as pages_router

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_app_state(app)
    yield


app = FastAPI(title="Windsurf Admin", lifespan=lifespan)
app.include_router(api_router)
app.include_router(pages_router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=307)
