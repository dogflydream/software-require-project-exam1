"""绿循校园——校园闲置教材与物品循环流转系统。"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import database
from models import Health

app = FastAPI(title="绿循校园", version="0.0.1")

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def startup() -> None:
    database.init_db()


@app.get("/api/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", app="绿循校园")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
