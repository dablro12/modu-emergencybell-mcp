"""place_context · emergency_guide 단위 테스트."""

from __future__ import annotations

import pytest

from place_context import (
    classify_intents,
    expand_place_query,
    infer_user_type_from_text,
    is_valid_wfclt_id,
    normalize_facility_type,
    normalize_situation_tag,
    normalize_specialty,
)


def test_expand_changsin_dong() -> None:
    assert "종로구" in expand_place_query("창신동")
    assert "서울" in expand_place_query("창신동")


def test_expand_yeonsan9_dong() -> None:
    expanded = expand_place_query("연산9동")
    assert "연제구" in expanded
    assert "부산" in expanded


def test_expand_gu_only() -> None:
    assert expand_place_query("종로구").startswith("서울")


def test_normalize_situation_aliases() -> None:
    assert normalize_situation_tag("gas_leak") == "utility_gas"
    assert normalize_situation_tag("missing_child") == "police"


def test_normalize_facility_type_aliases() -> None:
    assert normalize_facility_type("elevator") == "accessibility"
    assert normalize_facility_type("luggage_storage") == "locker"


def test_normalize_specialty_aliases() -> None:
    assert normalize_specialty("internal_medicine") == "internal"
    assert normalize_specialty("veterinary") == "vet"


def test_infer_user_type_from_text() -> None:
    assert infer_user_type_from_text("명동 휠체어 화장실") == "wheelchair"
    assert infer_user_type_from_text("코엑스 기저귀 갈곳") == "infant_care"
    assert infer_user_type_from_text("비상벨 있는 화장실") == "elderly_safety"


def test_is_valid_wfclt_id() -> None:
    assert not is_valid_wfclt_id("elevator")
    assert not is_valid_wfclt_id("wheelchair_restroom")
    assert is_valid_wfclt_id("4421010800-1-01490001")


def test_classify_intents_gas() -> None:
    intents = classify_intents("집에서 가스 냄새가 날 때")
    assert "hotlines" in intents


def test_classify_intents_fever_child() -> None:
    intents = classify_intents("새벽 아이 39도")
    assert "clinic" in intents
    assert "hotlines" in intents or "pharmacy" in intents or "clinic" in intents


@pytest.mark.asyncio
async def test_emergency_guide_offline_hotlines(monkeypatch: pytest.MonkeyPatch) -> None:
    from emergency_guide import emergency_guide

    def fake_hotlines(*args, **kwargs):
        return "## hotlines ok"

    monkeypatch.setattr("emergency_guide.format_emergency_hotlines", fake_hotlines)

    result = await emergency_guide("집에서 가스 냄새", place_query="서울")
    assert "hotlines ok" in result
    assert "통합 안내" in result
