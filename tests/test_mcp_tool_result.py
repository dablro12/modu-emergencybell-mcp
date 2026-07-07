"""mcp_tool_result · juso-first place_resolver 테스트."""

from __future__ import annotations

import pytest
from mcp.types import CallToolResult

from mcp_tool_result import is_failure_text, tool_result
from place_resolver import looks_like_address, should_juso_first


def test_is_failure_text() -> None:
    assert is_failure_text("명동에 맞는 공중화장실을 찾지 못했습니다.")
    assert not is_failure_text("## 검색: 강남역\n### 1. OO화장실")


def test_tool_result_sets_is_error() -> None:
    out = tool_result("결과 없음 — 찾지 못했습니다.")
    assert isinstance(out, CallToolResult)
    assert out.isError is True


def test_tool_result_success() -> None:
    out = tool_result("## 화장실\n### 1. 테스트")
    assert out == "## 화장실\n### 1. 테스트"


def test_looks_like_address() -> None:
    assert looks_like_address("서울특별시 중구 세종대로 110")
    assert looks_like_address("종로구 창신동 123-4")
    assert not looks_like_address("강남역")


def test_should_juso_first() -> None:
    assert should_juso_first("서울특별시 중구 세종대로 110")
    assert should_juso_first("창신동")
    assert not should_juso_first("명동성당")
    assert not should_juso_first("강남역")


@pytest.mark.asyncio
async def test_resolve_juso_first_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from place_resolver import resolve_place_context

    async def fake_juso(keyword: str, **kwargs):
        if "세종대로" in keyword:
            return {
                "sido": "서울특별시",
                "sigungu": "중구",
                "dong": "태평로1가",
                "road_addr": "서울특별시 중구 세종대로 110",
                "jibun_addr": "서울특별시 중구 태평로1가",
                "expanded_query": "서울특별시 중구 세종대로 110",
                "lang": "ko",
            }
        return None

    async def fake_kakao(*args, **kwargs):
        return None, None, ""

    async def fake_geocode_juso(ctx, address, *, sido_hint):
        ctx.apply_coords(37.5665, 126.9780)
        ctx.source = "juso+kakao_address"

    monkeypatch.setattr("place_resolver.resolve_administrative", fake_juso)
    monkeypatch.setattr("place_resolver.geocode_via_kakao_candidates", fake_kakao)
    monkeypatch.setattr("place_resolver._geocode_juso_address", fake_geocode_juso)
    monkeypatch.setattr("place_resolver.lookup_landmark_coords", lambda q: None)
    monkeypatch.setattr("place_resolver.resolve_landmark_poi", lambda q: None)

    ctx = await resolve_place_context("서울특별시 중구 세종대로 110")
    assert ctx.sigungu == "중구"
    assert "juso" in ctx.source
    assert ctx.coords is not None
