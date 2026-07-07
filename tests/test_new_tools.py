"""Tests for v0.4.0 new tools (subway, wifi, vet, outdoor services)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datago_json_client import format_vet_list, format_wifi_list
from outdoor_services import normalize_service
from scripts.process_subway_data import normalize_station
from subway_facility import find_subway_facility, load_index

SUBWAY_INDEX = Path(__file__).resolve().parent.parent / "data" / "subway" / "subway_index.json"
SUBWAY_ATM_INDEX = Path(__file__).resolve().parent.parent / "data" / "subway" / "subway_atm_index.json"


@pytest.fixture(scope="module", autouse=True)
def ensure_subway_index() -> None:
    if not SUBWAY_INDEX.exists():
        import scripts.process_subway_data as processor

        processor.main()
    if not SUBWAY_ATM_INDEX.exists():
        import scripts.process_subway_atm_data as atm_processor

        atm_processor.main()


def test_normalize_station():
    assert normalize_station("강남역") == "강남"
    assert normalize_station("서울 역") == "서울"


def test_subway_index_loaded():
    data = load_index()
    assert data.get("meta", {}).get("station_count", 0) > 100


def test_find_subway_gangnam():
    text = find_subway_facility("강남역")
    assert "강남" in text
    assert "물품보관함" in text


def test_find_subway_seoul_station_not_garak():
    text = find_subway_facility("서울역")
    assert "가락시장" not in text
    assert "서울" in text


def test_find_subway_busan():
    text = find_subway_facility("서면")
    assert "물품보관함" in text or "등록된" in text


def test_find_subway_unknown():
    text = find_subway_facility("존재하지않는역")
    assert "찾지 못했습니다" in text


def test_service_aliases():
    assert normalize_service("동물병원") == "vet_hospital"
    assert normalize_service("와이파이") == "wifi"
    assert normalize_service("atm") == "atm"
    assert normalize_service("storage") == "locker"
    assert normalize_service("캐리어") == "locker"


def test_format_wifi_empty():
    assert "찾지 못했습니다" in format_wifi_list([], query="테스트")


def test_format_vet_empty():
    assert "찾지 못했습니다" in format_vet_list([], query="테스트")


def test_subway_atm_index_loaded():
    from subway_atm import load_index

    data = load_index()
    assert data.get("meta", {}).get("station_count", 0) > 100


def test_search_subway_atm_gangnam():
    from subway_atm import search_subway_atms

    import asyncio

    text = asyncio.run(search_subway_atms("강남역", station_query="강남역", limit=3))
    assert "강남" in text
    assert "ATM" in text or "효성" in text or "은행" in text


def test_search_subway_atm_seoul_station():
    from subway_atm import search_subway_atms

    import asyncio

    text = asyncio.run(search_subway_atms("서울역", limit=2))
    assert "서울" in text
    assert "찾지 못했습니다" not in text


def test_search_subway_atm_myungdong_fallback():
    from subway_atm import search_subway_atms

    import asyncio

    text = asyncio.run(search_subway_atms("명동", limit=2))
    assert "찾지 못했습니다" not in text
    assert "명동" in text or "가까운" in text


def test_search_subway_atm_unknown():
    from subway_atm import search_subway_atms

    import asyncio

    text = asyncio.run(search_subway_atms("존재하지않는곳xyz123", limit=2))
    assert "찾지 못했습니다" in text


@pytest.mark.live
@pytest.mark.asyncio
async def test_wifi_api_live():
    pytest.importorskip("httpx")
    import os

    if not (os.getenv("DATA_GO_KR_SERVICE_KEY") or "").strip():
        pytest.skip("DATA_GO_KR_SERVICE_KEY not set")

    from datago_json_client import search_free_wifi

    rows = await search_free_wifi(place_query="서울", limit=1)
    assert len(rows) >= 1
    assert any(k in rows[0] for k in ("LCTN_ROAD_NM_ADDR", "INSTL_PLC_NM", "INSTL_FCLT_SE_NM"))


@pytest.mark.live
@pytest.mark.asyncio
async def test_vet_api_live():
    import os

    if not (os.getenv("DATA_GO_KR_SERVICE_KEY") or "").strip():
        pytest.skip("DATA_GO_KR_SERVICE_KEY not set")

    from datago_json_client import search_vet_hospitals

    rows = await search_vet_hospitals(place_query="서울", limit=3)
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_safe182_live():
    import os

    if not os.getenv("SAFE182_AUTH_ID") or not os.getenv("SAFE182_AUTH_KEY"):
        pytest.skip("SAFE182 credentials not set")

    from safe182_client import search_safe_places

    text = await search_safe_places(place_query="서울 종로구", category="child_safety_house", limit=2)
    assert "안전Dream" in text or "아동" in text or "찾지 못했습니다" in text


@pytest.mark.live
@pytest.mark.asyncio
async def test_disabled_facility_list_live():
    import os

    if not (os.getenv("DATA_GO_KR_SERVICE_KEY") or "").strip():
        pytest.skip("DATA_GO_KR_SERVICE_KEY not set")

    from accessible_facility_client import _search_disabled_facilities

    rows = await _search_disabled_facilities(place_query="서울역", limit=3)
    assert len(rows) >= 1
    assert any("서울" in (row.get("faclNm") or "") or "서울" in (row.get("lcMnad") or "") for row in rows)


@pytest.mark.live
@pytest.mark.asyncio
async def test_disabled_facility_detail_live():
    import os

    if not (os.getenv("DATA_GO_KR_SERVICE_KEY") or "").strip():
        pytest.skip("DATA_GO_KR_SERVICE_KEY not set")

    from accessible_facility_client import find_accessible_facility

    text = await find_accessible_facility(
        place_query="서울역",
        facility_id="4421010800-1-01490001",
    )
    assert "장애인 편의시설" in text
    assert "승강기" in text or "화장실" in text


@pytest.mark.asyncio
async def test_accessible_facility_offline():
    from unittest.mock import AsyncMock, patch

    from accessible_facility_client import find_accessible_facility

    with patch(
        "accessible_facility_client._search_disabled_facilities",
        new=AsyncMock(return_value=[]),
    ):
        text = await find_accessible_facility(place_query="강남역", include_subway=True, limit=3)
    assert "접근성" in text or "화장실" in text or "지하철" in text
