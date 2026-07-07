"""Project root and data directory paths (src/ layout)."""

from __future__ import annotations

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
DATA_ROOT = PROJECT_ROOT / "data"


def data_path(*parts: str) -> Path:
    return DATA_ROOT.joinpath(*parts)
