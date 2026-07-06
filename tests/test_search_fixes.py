"""Offline tests for region matching, restroom search, and safety bell lookup."""

from __future__ import annotations

import asyncio

import pytest

from helpers import search_records, search_restrooms_by_query, _normalize_user_type
from region_parse import normalize_place_query, regions_match
from safety_bell import find_safety_bells_near, search_safety_bells


def test_regions_match_sigungu_only():
    assert regions_match("서울특별시 중구", "중구") is True
    assert regions_match("부산광역시 해운대구", "해운대구") is True


def test_normalize_english_place():
    assert normalize_place_query("Myeongdong Station") == "명동역"
    assert normalize_place_query("COEX") == "코엑스"


def test_user_type_aliases():
    assert _normalize_user_type("with_infants") == "infant_care"
    assert _normalize_user_type("wheelchair_accessible") == "wheelchair"


def test_myeongdong_wheelchair_offline():
    results = search_records(
        query_tokens=["명동"],
        user_type="wheelchair",
        limit=5,
        strict_region=False,
    )
    assert len(results) >= 1
    assert any("명동" in r["name"] for r in results)


def test_gangnam_infant_offline():
    results = search_records(
        query_tokens=["강남역"],
        user_type="infant_care",
        limit=5,
        strict_region=False,
    )
    assert len(results) >= 1


def test_haeundae_and_token_matching():
    results = search_records(
        query_tokens=["해운대", "해수욕장"],
        limit=5,
        strict_region=False,
    )
    assert len(results) >= 1
    assert all("해운대" in r["search_text"] and "해수욕장" in r["search_text"] for r in results)


def test_coex_safety_bell_offline():
    bells = search_safety_bells(latitude=37.512535, longitude=127.058834, radius_m=500, limit=3)
    assert len(bells) >= 1


@pytest.mark.asyncio
async def test_search_restroom_myeongdong():
    results, _ = await search_restrooms_by_query("Myeongdong Station", user_type="wheelchair", limit=3)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_find_safety_bell_coex():
    text = await find_safety_bells_near(place_query="COEX", radius_m=500, limit=3)
    assert "찾지 못했습니다" not in text
    assert "안전비상벨" in text
