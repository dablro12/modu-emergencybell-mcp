"""건강 트리아지 단위 테스트."""

from __future__ import annotations

import pytest

from health_triage import analyze_health_request, classify_health_urgency
from place_context import classify_intents


def test_lego_swallow_urgency() -> None:
    triage = analyze_health_request("아이가 레고 블록 삼켰어 어떻게 하지")
    assert triage.category == "foreign_body_child"
    assert triage.urgency in ("urgent", "critical")
    assert "소아" in triage.department_ko or "응급" in triage.department_ko


def test_wrong_pet_medicine_critical() -> None:
    triage = analyze_health_request("강아지 약을 내 약인 줄 알고 잘못 먹었어")
    assert triage.category == "wrong_species_drug"
    assert triage.urgency == "critical"


def test_headache_after_soccer() -> None:
    triage = analyze_health_request("신설동역에서 축구하고 목이 쑤시고 머리가 아파")
    assert triage.specialty in ("internal", "ent")
    assert classify_health_urgency("신설동역에서 축구하고 목이 쑤시고 머리가 아파") in (
        "low",
        "moderate",
        "urgent",
    )


def test_health_triage_intent() -> None:
    intents = classify_intents("본드 마셨어 어떡해")
    assert "health_triage" in intents


@pytest.mark.live
@pytest.mark.asyncio
async def test_health_triage_integration() -> None:
    import os

    if not (os.getenv("DATA_GO_KR_SERVICE_KEY") or "").strip():
        pytest.skip("DATA_GO_KR_SERVICE_KEY not set")

    from health_triage import health_triage

    result = await health_triage("아이 레고 삼켰어 서울 마포구", place_query="마포구")
    assert "1339" in result or "119" in result
    assert "면책" in result or "진단" in result
