"""FastAPI lifespan + uvicorn 入口.

Electron 主进程通过 --data-dir 传入数据目录，后端所有持久化路径均基于此.
"""

from __future__ import annotations

import argparse
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jmcomic_backend.api import deps
from jmcomic_backend.api.routes import health, settings
from jmcomic_backend.api import ws
from jmcomic_backend.core.config import API_PREFIX, DEFAULT_PORT, VERSION
from jmcomic_backend.core.logging import configure_logging
from jmcomic_backend.core.paths import AppPaths
from jmcomic_backend.core.settings import AppSettings


@asynccontextmanager
async def lifespan(app: FastAPI):
    paths: AppPaths = app.state.paths
    paths.ensure_all()
    configure_logging(paths.log_dir)
    logging.info("JMComic backend starting, version=%s, data_dir=%s", VERSION, paths.data_dir)
    yield
    logging.info("JMComic backend shutting down")


def create_app(data_dir: Path) -> FastAPI:
    app = FastAPI(
        title="JMComic Backend",
        version=VERSION,
        lifespan=lifespan,
    )

    # CORS: only allow Electron origin and localhost during dev.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "app://.*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.paths = AppPaths(data_dir)
    app.state.settings = AppSettings.load_from_file(app.state.paths.config_file)

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(settings.router, prefix=API_PREFIX)
    app.include_router(ws.router)

    return app


def _resolve_data_dir(data_dir: str | None) -> Path:
    if not data_dir:
        data_dir = os.environ.get("JMCOMIC_DATA_DIR")
    if not data_dir:
        raise ValueError("--data-dir or JMCOMIC_DATA_DIR environment variable is required")
    path = Path(data_dir).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JMComic Electron backend")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="host to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port to listen on")
    parser.add_argument("--data-dir", type=str, default=None, help="runtime data directory")
    parser.add_argument("--reload", action="store_true", help="enable auto-reload (dev only)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    host = os.environ.get("JMCOMIC_HOST", args.host)
    port = int(os.environ.get("JMCOMIC_PORT", args.port))
    data_dir = _resolve_data_dir(args.data_dir)

    app = create_app(data_dir)
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
        reload=args.reload,
    )


# Expose a default app for `uvicorn jmcomic_backend.main:app`.
# Data dir is read from JMCOMIC_DATA_DIR environment variable.
try:
    app = create_app(_resolve_data_dir(None))
except ValueError:
    # If data dir is not set, leave `app` undefined so uvicorn will report a clear error.
    app = None  # type: ignore[assignment]

if __name__ == "__main__":
    main()
