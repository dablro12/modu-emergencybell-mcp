"""Tests for bus stop local index search."""

from __future__ import annotations

from pathlib import Path

import pytest

from bus_stop import format_bus_stop_list, load_index, search_bus_stops
from outdoor_services import normalize_service
from scripts.process_bus_stop_data import write_mini_fixture

INDEX_FILE = Path(__file__).resolve().parent.parent / "data" / "bus" / "bus_stop_index.json"


@pytest.fixture(scope="module", autouse=True)
def ensure_bus_index() -> None:
    if not INDEX_FILE.exists():
        write_mini_fixture()


def test_index_loaded():
    data = load_index()
    assert data.get("meta", {}).get("record_count", 0) >= 1


def test_search_near_gangnam():
    stops = search_bus_stops(
        latitude=37.497942,
        longitude=127.027621,
        radius_m=500,
        city_hint="서울",
        limit=5,
    )
    assert stops
    assert stops[0]["distance_m"] <= 500


def test_service_alias_bus_stop():
    assert normalize_service("버스정류장") == "bus_stop"
    assert normalize_service("bus") == "bus_stop"


def test_format_empty():
    text = format_bus_stop_list([], query="테스트")
    assert "찾지 못했습니다" in text


@pytest.mark.asyncio
async def test_find_bus_stops_near_offline(monkeypatch: pytest.MonkeyPatch):
    from bus_stop import find_bus_stops_near

    class FakeCtx:
        latitude = 37.497942
        longitude = 127.027621
        sido = "서울특별시"
        sigungu = "강남구"
        expanded_query = "서울특별시 강남구"
        warning = None

    async def fake_resolve(_query: str):
        return FakeCtx()

    monkeypatch.setattr("bus_stop.resolve_place_context", fake_resolve)
    text = await find_bus_stops_near(place_query="강남역", limit=3)
    assert "버스정류장" in text
    assert "정류장번호" in text
