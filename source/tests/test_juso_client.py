"""juso 한·영 도로명주소 API 테스트."""

from __future__ import annotations

import os

import pytest

from juso_client import is_latin_address_query, resolve_administrative


def test_is_latin_address_query():
    assert is_latin_address_query("238 Gangnam-daero, Seoul")
    assert is_latin_address_query("Itaewon-ro Yongsan-gu")
    assert not is_latin_address_query("종로구 창신동")
    assert not is_latin_address_query("강남역")


@pytest.mark.asyncio
async def test_resolve_korean_juso_live():
    if not os.getenv("JUSO_CONFM_KEY"):
        pytest.skip("JUSO_CONFM_KEY not set")
    row = await resolve_administrative("종로구 창신동")
    assert row is not None
    assert "종로구" in row.get("sigungu", "")
    assert row.get("lang") == "ko"


@pytest.mark.asyncio
async def test_resolve_english_juso_live():
    if not os.getenv("JUSO_ENG_CONFM_KEY"):
        pytest.skip("JUSO_ENG_CONFM_KEY not set")
    row = await resolve_administrative("Gangnam-daero Seoul", prefer_english=True)
    assert row is not None
    assert row.get("lang") == "en"
    assert "서울" in row.get("road_addr", "") or "강남" in row.get("road_addr", "")


@pytest.mark.asyncio
async def test_resolve_english_to_korean_admin_live():
    if not os.getenv("JUSO_ENG_CONFM_KEY"):
        pytest.skip("JUSO_ENG_CONFM_KEY not set")
    from place_resolver import resolve_place_context

    ctx = await resolve_place_context("238 Gangnam-daero, Gangnam-gu, Seoul")
    assert ctx.sigungu == "강남구"
    assert ctx.sido == "서울특별시"
    assert ctx.source in {"juso_eng", "juso", "juso+kakao_address", "kakao_address", "kakao_keyword"}
