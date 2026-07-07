"""장소·의도·파라미터 정규화 — 에이전트 오입력 보정."""

from __future__ import annotations

import re
from typing import Any

from landmarks import resolve_landmark_poi, strip_poi_noise
from region_parse import SIDO_ALIASES, parse_place_query, region_full_prefix

DONG_EXACT: dict[str, str] = {
    "창신동": "서울특별시 종로구 창신동",
    "연산9동": "부산광역시 연제구 연산9동",
    "연산동": "부산광역시 연제구 연산동",
    "명동": "서울특별시 중구 명동",
    "이태원동": "서울특별시 용산구 이태원동",
    "혜화동": "서울특별시 종로구 혜화동",
}

STATION_REGION: dict[str, str] = {
    "상봉역": "서울특별시 중랑구",
    "혜화역": "서울특별시 종로구",
    "동대문역": "서울특별시 종로구",
    "강남역": "서울특별시 강남구",
    "서울역": "서울특별시 용산구",
    "명동역": "서울특별시 중구",
    "홍대입구역": "서울특별시 마포구",
    "서면역": "부산광역시 부산진구",
    "센텀시티역": "부산광역시 해운대구",
    "해운대역": "부산광역시 해운대구",
}

SITUATION_ALIASES: dict[str, str] = {
    "gas_leak": "utility_gas",
    "gas": "utility_gas",
    "missing_child": "police",
    "missing child": "police",
    "child_missing": "police",
    "lost_child": "police",
}

FACILITY_TYPE_ALIASES: dict[str, str] = {
    "elevator": "accessibility",
    "lift": "accessibility",
    "wheelchair": "accessibility",
    "accessible": "accessibility",
    "luggage_storage": "locker",
    "luggage": "locker",
    "storage": "locker",
    "짐": "locker",
    "물품보관함": "locker",
    "lockers": "locker",
}

SAFE_CATEGORY_ALIASES: dict[str, str] = {
    "youth_shelter": "youth",
    "청소년쉼터": "youth",
    "쉼터": "youth",
    "아동안전지킴이집": "child_safety_house",
    "안전지킴이집": "child_safety_house",
}

SPECIALTY_ALIASES: dict[str, str] = {
    "internal_medicine": "internal",
    "내과": "internal",
    "veterinary": "vet",
    "동물병원": "vet",
    "vet": "vet",
    "veteran": "veteran",
    "보훈": "veteran",
}

VETERAN_KEYWORDS = (
    "보훈",
    "국가유공자",
    "유공자",
    "위탁병원",
    "보훈병원",
    "보훈의료",
    "veteran",
)

SERVICE_ALIASES_EXTRA: dict[str, str] = {
    "locker": "subway_locker",
    "luggage": "subway_locker",
    "물품보관함": "subway_locker",
    "짐맡기기": "subway_locker",
}

WFCLT_ID_PATTERN = re.compile(r"^\d{4,}-[\d-]+$")
DONG_PATTERN = re.compile(r"([가-힣]+\d*동)")
STATION_PATTERN = re.compile(r"([가-힣A-Za-z0-9]+역)")


def normalize_situation_tag(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower().replace(" ", "_")
    return SITUATION_ALIASES.get(key, value.strip())


def normalize_facility_type(value: str) -> str:
    key = value.strip().lower()
    return FACILITY_TYPE_ALIASES.get(key, FACILITY_TYPE_ALIASES.get(value.strip(), key))


def normalize_safe_category(value: str) -> str:
    key = value.strip()
    return SAFE_CATEGORY_ALIASES.get(key, SAFE_CATEGORY_ALIASES.get(key.lower(), key))


def normalize_specialty(value: str) -> str:
    key = value.strip().lower()
    return SPECIALTY_ALIASES.get(key, SPECIALTY_ALIASES.get(value.strip(), key))


def is_valid_wfclt_id(value: str | None) -> bool:
    if not value:
        return False
    text = value.strip()
    if text.lower() in {
        "elevator",
        "wheelchair_restroom",
        "wheelchair",
        "restroom",
        "luggage_storage",
        "locker",
    }:
        return False
    return bool(WFCLT_ID_PATTERN.match(text) or (text[0].isdigit() and "-" in text))


def infer_user_type_from_text(text: str) -> str | None:
    lowered = text.lower()
    if any(k in text for k in ("휠체어", "장애인 화장실", "wheelchair", "accessible restroom")):
        return "wheelchair"
    if any(k in text for k in ("기저귀", "수유", "infant", "diaper", "유아")):
        return "infant_care"
    if any(k in text for k in ("비상벨", "벨 있는", "emergency bell", "safety bell")) and "화장실" in text:
        return "elderly_safety"
    if any(k in text for k in ("어린이", "child", "kids")):
        return "child"
    return None


def extract_place_hint(text: str) -> str:
    for match in STATION_PATTERN.findall(text):
        if match in STATION_REGION:
            return match
    for match in DONG_PATTERN.findall(text):
        if match in DONG_EXACT:
            return match
    return ""


def expand_place_query(query: str) -> str:
    stripped = strip_poi_noise((query or "").strip())
    if not stripped:
        return stripped

    poi = resolve_landmark_poi(stripped)
    if poi:
        _coords, region, keyword = poi
        return f"{region} {keyword}".strip()

    sido, sigungu = parse_place_query(stripped)
    if sido and sigungu:
        return region_full_prefix(sido, sigungu) + (
            f" {stripped}" if stripped not in region_full_prefix(sido, sigungu) else ""
        ).strip()

    if stripped in DONG_EXACT:
        return DONG_EXACT[stripped]

    tokens = stripped.replace(",", " ").split()
    for dong, full in sorted(DONG_EXACT.items(), key=lambda x: -len(x[0])):
        if dong in tokens or stripped == dong:
            return full

    for station, region in STATION_REGION.items():
        if station in stripped:
            if sigungu or sido:
                return stripped
            return f"{region} {stripped}".strip()

    if stripped.endswith("동") and stripped in DONG_EXACT:
        return DONG_EXACT[stripped]

    if stripped.endswith("구") and not sido:
        for alias, full_sido in SIDO_ALIASES.items():
            if alias in ("서울", "부산", "대구", "인천"):
                return f"{full_sido} {stripped}"

    if stripped.endswith("구") and stripped in {
        "종로구", "마포구", "강남구", "중랑구", "용산구", "해운대구", "연제구", "부산진구",
    }:
        if stripped in {"종로구", "마포구", "강남구", "중랑구", "용산구"}:
            return f"서울특별시 {stripped}"
        if stripped in {"해운대구", "연제구", "부산진구"}:
            return f"부산광역시 {stripped}"

    return stripped


def classify_intents(text: str) -> list[str]:
    """Return ordered intent tags from user text."""
    lowered = text.lower()
    intents: list[str] = []

    def add(tag: str) -> None:
        if tag not in intents:
            intents.append(tag)

    if any(k in text for k in ("119", "112", "1339", "182", "전화", "신고", "실종", "가스", "누출", "독극물")):
        add("hotlines")
    if "화장실" in text or "restroom" in lowered or "toilet" in lowered or "급똥" in text:
        add("restroom")
    if any(k in text for k in ("안전비상벨", "범죄예방", "safety bell")) and "화장실" not in text:
        add("safety_bell")
    if any(
        k in text
        for k in (
            "범죄",
            "치안",
            "취약",
            "위험한",
            "crime",
            "안전할까",
            "안전한가",
            "밤에 걸",
            "야간",
            "강도",
            "절도",
            "성범죄",
            "추행",
        )
    ):
        add("crime_stats")
    if any(k in text for k in ("약국", "pharmacy")):
        add("pharmacy")
    if any(k in text for k in ("응급실", "병상", "emergency room")):
        add("emergency_room")
    if any(
        k in text
        for k in ("소아과", "병원", "의원", "진료", "clinic", "내과", "39도", "열")
    ) and not any(k in text for k in VETERAN_KEYWORDS):
        add("clinic")
    if any(k in text for k in ("물품보관함", "짐 맡", "locker", "luggage")):
        add("subway_locker")
    if any(k in text for k in ("엘리베이터", "휠체어", "접근", "장애인", "elevator", "wheelchair")):
        add("accessible")
    if any(k in text for k in ("ATM", "atm", "현금인출")):
        add("atm")
    if any(k in text for k in ("와이파이", "wifi", "wi-fi")):
        add("wifi")
    if any(k in text for k in ("버스정류장", "버스 정류장", "정류장", "정류소", "bus stop")):
        add("bus_stop")
    if any(k in text for k in VETERAN_KEYWORDS):
        add("veteran_hospital")
    if any(k in text for k in ("동물병원", "vet", "veterinary")):
        add("vet")
    if any(k in text for k in ("안전지킴이", "쉼터", "safe182", "아동안전")):
        add("safe_place")
    if any(k in text for k in ("phrase", "phrase card", "문장", "foreign", "tourist", "관광객")):
        add("phrase")

    if not intents:
        add("hotlines")
    return intents


def infer_specialty(text: str) -> str:
    if any(k in text for k in VETERAN_KEYWORDS):
        return "veteran"
    if any(k in text for k in ("소아", "아이", "pediatric")):
        return "pediatric"
    if "내과" in text or "internal" in text.lower():
        return "internal"
    return "general"
