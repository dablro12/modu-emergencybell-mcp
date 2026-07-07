"""i18n_support · 다국어 장소·의도 테스트."""

from __future__ import annotations

from i18n_support import (
    detect_input_language,
    resolve_foreign_station,
)
from place_context import classify_intents, extract_place_from_text, infer_user_type_from_text
from landmarks import resolve_landmark_poi


def test_detect_language() -> None:
    assert detect_input_language("명동 화장실") == "ko"
    assert detect_input_language("Restroom near Myeongdong") == "en"
    assert detect_input_language("明洞圣堂附近厕所") == "zh"


def test_foreign_station() -> None:
    assert resolve_foreign_station("near Gangnam Station") == "강남역"
    assert resolve_foreign_station("江南站药店") == "강남역"


def test_extract_place_english() -> None:
    place = extract_place_from_text("Wheelchair restroom near Myeongdong Cathedral")
    assert place
    poi = resolve_landmark_poi(place)
    assert poi is not None


def test_extract_place_chinese() -> None:
    place = extract_place_from_text("明洞圣堂附近哪里有轮椅厕所")
    assert "明洞" in place or "圣堂" in place
    poi = resolve_landmark_poi(place)
    assert poi is not None


def test_classify_intents_english() -> None:
    intents = classify_intents("Urgent restroom near COEX please")
    assert "restroom" in intents


def test_classify_intents_chinese() -> None:
    intents = classify_intents("海云台附近有药店吗")
    assert "pharmacy" in intents


def test_infer_wheelchair_multilingual() -> None:
    assert infer_user_type_from_text("wheelchair restroom myeongdong") == "wheelchair"
    assert infer_user_type_from_text("明洞轮椅厕所") == "wheelchair"
