"""동물병원·반려동물 라우팅 테스트."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from animal_facility import load_index, search_animal_facilities
from outdoor_services import normalize_service
from place_context import classify_intents, infer_specialty, is_pet_care_query

INDEX = Path(__file__).resolve().parent.parent / "data" / "animal" / "animal_hospital_index.json"


@pytest.mark.skipif(not INDEX.exists(), reason="animal index not built")
def test_animal_hospital_index_has_records() -> None:
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    assert payload["meta"]["record_count"] > 1000


@pytest.mark.skipif(not INDEX.exists(), reason="animal index not built")
def test_search_animal_hospitals_near_hongdae() -> None:
    rows = search_animal_facilities(
        kind="hospital",
        latitude=37.5563,
        longitude=126.9236,
        radius_m=1500,
        city_hint="서울 마포구",
        limit=5,
    )
    assert rows
    assert all("distance_m" in row for row in rows)
    assert rows[0]["distance_m"] <= 1500


def test_is_pet_care_query() -> None:
    assert is_pet_care_query("홍대입구 근처 강아지 토해서 동물병원 급해")
    assert is_pet_care_query("my dog is vomiting near Hongdae")
    assert not is_pet_care_query("아이 39도 소아과")


def test_classify_intents_pet_not_clinic() -> None:
    intents = classify_intents("홍대 강아지 토함 동물병원")
    assert "vet" in intents
    assert "clinic" not in intents
    assert "emergency_room" not in intents


def test_infer_specialty_vet() -> None:
    assert infer_specialty("강아지 구토") == "vet"


def test_normalize_animal_pharmacy_service() -> None:
    assert normalize_service("동물약국") == "animal_pharmacy"
    assert normalize_service("animal_pharmacy") == "animal_pharmacy"


def test_load_index_empty_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    load_index.cache_clear()
    monkeypatch.setattr(
        "animal_facility.INDEX_FILES",
        {"hospital": Path("/nonexistent/hospital.json"), "pharmacy": Path("/nonexistent/pharmacy.json")},
    )
    assert load_index("hospital")["records"] == []
    load_index.cache_clear()
