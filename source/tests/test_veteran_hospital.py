"""Tests for veteran entrusted hospital search."""

from __future__ import annotations

from pathlib import Path

import pytest

from place_context import classify_intents, infer_specialty, normalize_specialty
from scripts.process_veteran_hospital_data import write_mini_fixture
from veteran_hospital import find_veteran_hospitals_near, load_index, search_veteran_hospitals

INDEX_FILE = Path(__file__).resolve().parents[2] / "data" / "medical" / "veteran_hospital_index.json"


@pytest.fixture(scope="module", autouse=True)
def ensure_veteran_index() -> None:
    if not INDEX_FILE.exists():
        write_mini_fixture()


def test_index_loaded():
    data = load_index()
    assert data.get("meta", {}).get("record_count", 0) >= 1


def test_search_gangnam_region():
    rows = search_veteran_hospitals(
        latitude=37.497942,
        longitude=127.027621,
        sido="서울특별시",
        sigungu="강남구",
        limit=5,
    )
    assert rows
    assert rows[0]["name"]


def test_specialty_alias_veteran():
    assert normalize_specialty("보훈") == "veteran"
    assert infer_specialty("강남구 보훈병원") == "veteran"


def test_classify_veteran_intent():
    intents = classify_intents("국가유공자 위탁병원 찾아줘")
    assert "veteran_hospital" in intents


@pytest.mark.asyncio
async def test_find_veteran_hospitals_near_offline(monkeypatch: pytest.MonkeyPatch):
    class FakeCtx:
        latitude = 37.497942
        longitude = 127.027621
        sido = "서울특별시"
        sigungu = "강남구"
        warning = None

    async def fake_resolve(_query: str):
        return FakeCtx()

    monkeypatch.setattr("veteran_hospital.resolve_place_context", fake_resolve)
    text = await find_veteran_hospitals_near(place_query="강남구", limit=3)
    assert "보훈의료 위탁병원" in text
    assert "강남세브란스병원" in text or "위탁병원" in text
