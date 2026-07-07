"""Offline tests for v0.3.0 improvements."""

from __future__ import annotations

import asyncio

import pytest

from helpers import search_records, search_restrooms_by_query
from landmarks import lookup_landmark_coords, lookup_landmark_region
from nemc_client import parse_treatment_day
from phrases import format_phrase_card
from region_parse import address_matches_sido, extract_sido_hint, regions_match
from safety_bell import find_safety_bells_near, search_safety_bells


def test_regions_match_sigungu_only():
    assert regions_match("서울특별시 중구", "중구") is True


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


@pytest.mark.asyncio
async def test_search_restroom_myeongdong():
    results, _ = await search_restrooms_by_query("Myeongdong Station", user_type="wheelchair", limit=3)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_hangang_yeouido_safety_bell():
    text = await find_safety_bells_near(place_query="한강공원 여의도", radius_m=300, limit=3)
    assert "찾지 못했습니다" not in text
