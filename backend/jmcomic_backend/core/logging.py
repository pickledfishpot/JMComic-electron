"""日志配置."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_logging(log_dir: Path, level: int = logging.INFO) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Use a rotating handler in production if needed.
    file_handler = logging.FileHandler(
        log_dir / "backend.log", mode="a", encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = []
    root.addHandler(console_handler)
    root.addHandler(file_handler)
