"""Dynamic POI resolver tests (mocked Kakao)."""

from __future__ import annotations

import pytest

from poi_resolver import _score_document, resolve_dynamic_poi


def test_score_prefers_palace_over_station_for_gyeongbokgung() -> None:
    palace = {"place_name": "경복궁", "category_name": "여행 > 관광,명소 > 궁"}
    station = {"place_name": "경복궁역", "category_name": "교통,수송 > 지하철,전철 > 역"}
    assert _score_document(palace, "경복궁") > _score_document(station, "경복궁")


def test_score_prefers_station_when_query_has_station_suffix() -> None:
    palace = {"place_name": "경복궁", "category_name": "여행 > 관광,명소 > 궁"}
    station = {"place_name": "경복궁역", "category_name": "교통,수송 > 지하철,전철 > 역"}
    assert _score_document(station, "경복궁역") > _score_document(palace, "경복궁역")


@pytest.mark.asyncio
async def test_resolve_dynamic_poi_gyeongbokgung(monkeypatch: pytest.MonkeyPatch) -> None:
    docs = [
        {
            "place_name": "경복궁역",
            "category_name": "교통,수송 > 지하철,전철 > 역",
            "y": "37.575762",
            "x": "126.973530",
            "road_address_name": "서울 종로구 사직로 지하",
            "road_address": {
                "region_1depth_name": "서울",
                "region_2depth_name": "종로구",
                "region_3depth_name": "적선동",
            },
        },
        {
            "place_name": "경복궁",
            "category_name": "여행 > 관광,명소 > 궁",
            "y": "37.579617",
            "x": "126.977041",
            "road_address_name": "서울 종로구 사직로 161",
            "road_address": {
                "region_1depth_name": "서울",
                "region_2depth_name": "종로구",
                "region_3depth_name": "세종로",
            },
        },
    ]

    async def fake_search(query: str, **kwargs):
        return docs

    monkeypatch.setattr("poi_resolver.search_keyword", fake_search)

    poi = await resolve_dynamic_poi("경복궁 근처 화장실")
    assert poi is not None
    assert poi.place_name == "경복궁"
    assert 37.57 < poi.latitude < 37.59
    assert 126.97 < poi.longitude < 126.99
    assert poi.sigungu == "종로구"


@pytest.mark.asyncio
async def test_resolve_place_context_uses_dynamic_poi(monkeypatch: pytest.MonkeyPatch) -> None:
    from place_resolver import resolve_place_context

    async def fake_poi(query: str):
        from poi_resolver import DynamicPoi

        return DynamicPoi(
            query="경복궁",
            place_name="경복궁",
            latitude=37.579617,
            longitude=126.977041,
            sido="서울특별시",
            sigungu="종로구",
            road_address="서울 종로구 사직로 161",
        )

    async def fake_juso(*args, **kwargs):
        return None

    async def fake_kakao(*args, **kwargs):
        return None, None, ""

    monkeypatch.setattr("poi_resolver.resolve_dynamic_poi", fake_poi)
    monkeypatch.setattr("place_resolver.resolve_administrative", fake_juso)
    monkeypatch.setattr("place_resolver.geocode_via_kakao_candidates", fake_kakao)

    ctx = await resolve_place_context("경복궁 근처 화장실")
    assert ctx.coords == (37.579617, 126.977041)
    assert ctx.poi_name == "경복궁"
    assert ctx.sigungu == "종로구"
    assert ctx.source == "kakao_poi"
