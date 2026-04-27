from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI(title="Windsurf Admin")


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=307)
