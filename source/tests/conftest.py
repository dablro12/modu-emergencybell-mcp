import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "source" / "app"
SOURCE = ROOT / "source"
for path in (APP, SOURCE, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def datago_service_key() -> str:
    return (os.getenv("DATA_GO_KR_SERVICE_KEY") or "").strip()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: requires external API credentials")
