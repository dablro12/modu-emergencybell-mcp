"""place_resolver · juso_client 테스트."""

from __future__ import annotations

import pytest

from kakao_local import extract_admin_from_document
from place_resolver import resolve_place_context


def test_extract_admin_from_kakao_keyword_doc() -> None:
    doc = {
        "place_name": "강남역 2호선",
        "y": "37.497942",
        "x": "127.027621",
        "road_address": {
            "region_1depth_name": "서울",
            "region_2depth_name": "강남구",
            "region_3depth_name": "역삼동",
        },
    }
    sido, sigungu, dong = extract_admin_from_document(doc)
    assert sido == "서울특별시"
    assert sigungu == "강남구"
    assert dong == "역삼동"


@pytest.mark.asyncio
async def test_resolve_uses_juso_for_dong(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_juso(keyword: str):
        if "창신동" in keyword:
            return {
                "sido": "서울특별시",
                "sigungu": "종로구",
                "dong": "창신동",
                "road_addr": "서울특별시 종로구 창신동",
                "jibun_addr": "서울특별시 종로구 창신동",
                "expanded_query": "서울특별시 종로구 창신동",
            }
        return None

    async def fake_kakao(*args, **kwargs):
        return None, None, ""

    monkeypatch.setattr("place_resolver.resolve_administrative", fake_juso)
    monkeypatch.setattr("place_resolver.geocode_via_kakao_candidates", fake_kakao)

    ctx = await resolve_place_context("창신동")
    assert ctx.sigungu == "종로구"
    assert ctx.sido == "서울특별시"
    assert ctx.source == "juso"
    assert ctx.confidence == "high"


@pytest.mark.asyncio
async def test_resolve_kakao_keyword_for_station(monkeypatch: pytest.MonkeyPatch) -> None:
    doc = {
        "place_name": "강남역",
        "y": "37.497942",
        "x": "127.027621",
        "road_address": {
            "region_1depth_name": "서울",
            "region_2depth_name": "강남구",
            "region_3depth_name": "역삼동",
        },
    }

    async def fake_kakao(query, **kwargs):
        return (37.497942, 127.027621), doc, "kakao_keyword"

    async def fake_juso(keyword: str):
        return None

    monkeypatch.setattr("place_resolver.geocode_via_kakao_candidates", fake_kakao)
    monkeypatch.setattr("place_resolver.resolve_administrative", fake_juso)

    ctx = await resolve_place_context("강남역")
    assert ctx.coords == (37.497942, 127.027621)
    assert ctx.sigungu == "강남구"
    assert ctx.source == "kakao_keyword"


@pytest.mark.asyncio
async def test_resolve_warns_on_centroid_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_kakao(*args, **kwargs):
        return None, None, ""

    async def fake_juso(keyword: str):
        return None

    monkeypatch.setattr("place_resolver.geocode_via_kakao_candidates", fake_kakao)
    monkeypatch.setattr("place_resolver.resolve_administrative", fake_juso)
    monkeypatch.setattr("place_resolver.lookup_landmark_coords", lambda q: None)

    ctx = await resolve_place_context("서울")
    assert ctx.warning is not None
    assert ctx.source == "sido_centroid"
