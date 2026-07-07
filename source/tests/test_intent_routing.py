"""의도 분류 · Tool 라우팅 · 장소 파라미터 복구 테스트."""

from __future__ import annotations

import pytest

from intent_routing import classify_and_route, tools_for_intents
from place_context import (
    classify_intents,
    extract_place_from_text,
    merge_place_inputs,
)


def test_extract_place_myeongdong_cathedral() -> None:
    assert extract_place_from_text("명동성당쪽인데 급똥이야") == "명동성당"


def test_extract_place_hongdae() -> None:
    assert extract_place_from_text("홍대 와이파이 어디") == "홍대"


def test_extract_place_gangnam_station() -> None:
    assert extract_place_from_text("강남역 버스정류장") == "강남역"


def test_merge_place_inputs_prefers_landmark_from_user_request() -> None:
    merged = merge_place_inputs("화장실", "명동성당쪽 급똥")
    assert merged == "명동성당"


def test_merge_place_inputs_place_query_wins_when_specific() -> None:
    merged = merge_place_inputs("COEX", "서울 강남 물품보관함")
    assert merged == "COEX"


def test_classify_intents_urgent_restroom() -> None:
    intents = classify_intents("명동성당쪽 급똥 화장실")
    assert "restroom" in intents


def test_tools_for_intents_restroom() -> None:
    routes = tools_for_intents(["restroom", "hotlines"])
    tools = [r["tool"] for r in routes]
    assert "find_nearest_restroom" in tools
    assert "get_emergency_hotlines" in tools


@pytest.mark.asyncio
async def test_classify_and_route_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve(**kwargs):
        from place_resolver import PlaceContext

        return "서울특별시 중구 명동성당", PlaceContext(
            query="명동성당",
            expanded_query="서울특별시 중구 명동성당",
            latitude=37.5633,
            longitude=126.987,
            sido="서울특별시",
            sigungu="중구",
            source="landmark_poi",
            confidence="medium",
        )

    monkeypatch.setattr("intent_routing.resolve_effective_place", fake_resolve)

    text = await classify_and_route("명동성당쪽 급똥", place_query=None)
    assert "find_nearest_restroom" in text
    assert "명동성당" in text
    assert "emergency_guide_tool" not in text or "의도" in text
