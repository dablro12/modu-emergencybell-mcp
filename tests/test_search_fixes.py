"""Offline tests for v0.3.0 improvements."""

from __future__ import annotations

import asyncio

import pytest

from helpers import search_records, search_restrooms_by_query
from place_context import expand_place_query
from place_resolver import resolve_place_context
from landmarks import lookup_landmark_coords, lookup_landmark_region
from nemc_client import parse_treatment_day
from phrases import format_phrase_card
from region_parse import address_matches_sido, extract_sido_hint, regions_match
from safety_bell import find_safety_bells_near, search_safety_bells


def test_regions_match_sigungu_only():
    assert regions_match("서울특별시 중구", "중구") is True


def test_regions_match_jongno_not_jung():
    assert regions_match("서울특별시 종로구", "서울특별시 중구") is False
    assert regions_match("서울특별시 중구", "서울특별시 종로구") is False


def test_strip_poi_noise_jjok_e():
    from landmarks import strip_poi_noise

    assert strip_poi_noise("창신5라길 쪽에 화장실") == "창신5라길"


def test_search_records_geo_without_coords_returns_empty():
    results = search_records(
        latitude=37.564,
        longitude=126.987,
        region_prefix="서울특별시 중구",
        limit=5,
    )
    assert results == []


def test_address_matches_sido():
    assert address_matches_sido("서울특별시 용산구 이태원로", "서울특별시") is True
    assert address_matches_sido("경기도 용인시 지곡동", "서울특별시") is False
    assert address_matches_sido("부산광역시 수영구 광안해변로", "부산광역시") is True


def test_landmark_itaewon():
    coords = lookup_landmark_coords("서울 이태원 해밀턴호텔")
    assert coords is not None
    assert 37.5 < coords[0] < 37.6
    region = lookup_landmark_region("이태원")
    assert "용산" in region


def test_landmark_gwangalli():
    coords = lookup_landmark_coords("부산 광안리 해수욕장")
    assert coords is not None
    assert 35.1 < coords[0] < 35.2
    assert extract_sido_hint("부산 광안리") == "부산광역시"


def test_parse_treatment_day_korean():
    assert parse_treatment_day("월요일")[0] == "1"
    assert parse_treatment_day("공휴일")[0] == "8"
    assert parse_treatment_day("2026-05-05")[0] == "8"
    assert parse_treatment_day("2026-07-07")[0] == "2"


def test_parse_treatment_day_late_night_note():
    qt, note = parse_treatment_day("월요일 새벽 2시")
    assert qt == "1"
    assert note is not None
    assert "요일 단위" in note


def test_pharmacy_allergy_scenario():
    text = format_phrase_card(scenario="pharmacy_allergy_check", language="en")
    assert "allergic" in text.lower()
    assert "Does this medicine" in text


def test_safety_bell_itaewon_offline():
    lat, lng = lookup_landmark_coords("서울 이태원")  # type: ignore[misc]
    bells = search_safety_bells(
        latitude=lat,
        longitude=lng,
        radius_m=500,
        sido_hint="서울특별시",
        limit=5,
    )
    assert len(bells) >= 1
    for bell in bells:
        addr = bell.get("road_addr") or bell.get("jibun_addr") or ""
        assert address_matches_sido(addr, "서울특별시"), addr


def test_safety_bell_gwangalli_offline():
    lat, lng = lookup_landmark_coords("부산 광안리")  # type: ignore[misc]
    bells = search_safety_bells(
        latitude=lat,
        longitude=lng,
        radius_m=500,
        sido_hint="부산광역시",
        limit=5,
    )
    assert len(bells) >= 1
    for bell in bells:
        addr = bell.get("road_addr") or bell.get("jibun_addr") or ""
        assert address_matches_sido(addr, "부산광역시"), addr


@pytest.mark.asyncio
async def test_find_safety_bell_itaewon_async():
    text = await find_safety_bells_near(place_query="서울 이태원 해밀턴호텔", radius_m=500, limit=3)
    assert "찾지 못했습니다" not in text
    assert "용인" not in text
    assert "서울" in text


def test_expand_myeongdong_cathedral_not_dong():
    expanded = expand_place_query("명동성당")
    assert "명동성당" in expanded
    assert expanded != "서울특별시 중구 명동"
    assert expand_place_query("명동성당쪽") == expand_place_query("명동성당")


def test_strip_poi_noise():
    from landmarks import strip_poi_noise

    assert strip_poi_noise("명동성당쪽") == "명동성당"
    assert strip_poi_noise("홍대 근처") == "홍대"
    assert strip_poi_noise("혜화골목길인데 화장실도 급하고") == "혜화골목길"
    assert strip_poi_noise("경복궁 근처 화장실이랑 비상벨") == "경복궁"


def test_extract_place_golmokgil() -> None:
    from place_context import extract_place_from_text

    assert extract_place_from_text("혜화골목길인데 화장실도 급하고") == "혜화골목길"
    assert extract_place_from_text("경복궁 근처 화장실이랑 비상벨") == "경복궁"


def test_resolve_search_place_composite() -> None:
    from place_context import resolve_search_place

    place = resolve_search_place(
        "경복궁 근처 화장실이랑 비상벨 어디있어",
        fallback="서울",
    )
    assert place == "경복궁"


@pytest.mark.asyncio
async def test_search_restroom_gangnam_station():
    results, coords = await search_restrooms_by_query(
        "강남역 화장실 어디야",
        limit=3,
    )
    assert len(results) >= 1
    assert coords is not None


@pytest.mark.asyncio
async def test_search_restroom_gyeongbokgung(monkeypatch: pytest.MonkeyPatch):
    async def fake_poi(query: str):
        from poi_resolver import DynamicPoi

        return DynamicPoi(
            query="경복궁",
            place_name="경복궁",
            latitude=37.579617,
            longitude=126.977041,
            sido="서울특별시",
            sigungu="종로구",
        )

    async def fake_juso(*args, **kwargs):
        return None

    async def fake_kakao(*args, **kwargs):
        return None, None, ""

    monkeypatch.setattr("poi_resolver.resolve_dynamic_poi", fake_poi)
    monkeypatch.setattr("place_resolver.resolve_administrative", fake_juso)
    monkeypatch.setattr("place_resolver.geocode_via_kakao_candidates", fake_kakao)

    results, coords = await search_restrooms_by_query("경복궁 근처 화장실 급해", limit=3)
    assert len(results) >= 1
    assert coords is not None


@pytest.mark.asyncio
async def test_resolve_myeongdong_cathedral_landmark_override(monkeypatch: pytest.MonkeyPatch) -> None:
    doc = {
        "place_name": "명동",
        "y": "37.556581",
        "x": "126.984031",
        "road_address": {
            "region_1depth_name": "서울",
            "region_2depth_name": "중구",
            "region_3depth_name": "명동",
        },
    }

    async def fake_kakao(query, **kwargs):
        return (37.556581, 126.984031), doc, "kakao_keyword"

    async def fake_juso(keyword: str, **kwargs):
        return None

    async def fake_poi(query: str):
        return None

    monkeypatch.setattr("poi_resolver.resolve_dynamic_poi", fake_poi)
    monkeypatch.setattr("place_resolver.geocode_via_kakao_candidates", fake_kakao)
    monkeypatch.setattr("place_resolver.resolve_administrative", fake_juso)

    ctx = await resolve_place_context("명동성당쪽")
    assert ctx.coords is not None
    assert abs(ctx.coords[0] - 37.556581) < 0.02
    assert ctx.sigungu == "중구"


@pytest.mark.asyncio
async def test_search_restroom_myeongdong_cathedral():
    results, coords = await search_restrooms_by_query("명동성당쪽", limit=3)
    assert len(results) >= 1
    assert coords is not None
    lat = float(coords.split(",")[0])
    assert abs(lat - 37.5633) < 0.01


@pytest.mark.asyncio
async def test_search_restroom_changsin_vs_myeongdong_differ(monkeypatch: pytest.MonkeyPatch) -> None:
    from restroom_nearby import search_restrooms_nearby

    async def fake_nearby(latitude, longitude, **kwargs):
        if latitude > 37.57:
            return [
                {"id": "a", "name": "종로구민회관", "region": {"full_prefix": "서울특별시 종로구"}, "distance_m": 100, "opening": {"is_always_open": False, "is_closed_type": False}, "user_types": {"tags": ["general"]}},
            ]
        return [
            {"id": "b", "name": "명동역(4)", "region": {"full_prefix": "서울특별시 중구"}, "distance_m": 90, "opening": {"is_always_open": False, "is_closed_type": False}, "user_types": {"tags": ["general"]}},
        ]

    monkeypatch.setattr("restroom_nearby.search_restrooms_nearby", fake_nearby)

    changsin, _ = await search_restrooms_by_query("창신5라길", limit=3)
    myeong, _ = await search_restrooms_by_query("명동성당", limit=3)
    assert changsin and myeong
    assert changsin[0]["name"] != myeong[0]["name"]


@pytest.mark.asyncio
async def test_search_restroom_myeongdong():
    results, _ = await search_restrooms_by_query("Myeongdong Station", user_type="wheelchair", limit=3)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_hangang_yeouido_safety_bell():
    text = await find_safety_bells_near(place_query="한강공원 여의도", radius_m=300, limit=3)
    assert "찾지 못했습니다" not in text
