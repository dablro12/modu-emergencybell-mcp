"""장소·의도·파라미터 정규화 — 에이전트 오입력 보정."""

from __future__ import annotations

import re
from typing import Any

from landmarks import resolve_landmark_poi, strip_poi_noise
from i18n_support import (
    EN_PLACE_NOISE,
    ZH_PLACE_NOISE,
    foreign_intent_keywords,
    resolve_foreign_station,
)
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
SIGUNGU_PATTERN = re.compile(r"([가-힣]+(?:구|군))")

# 장소가 아닌 의도어 — place_query로 넘어오면 무시
PLACE_NOISE_TOKENS = frozenset({
    "화장실",
    "급똥",
    "똥",
    "와이파이",
    "wifi",
    "wi-fi",
    "atm",
    "약국",
    "병원",
    "응급실",
    "버스",
    "정류장",
    "정류소",
    "화장실알려줘",
    "알려줘",
    "찾아줘",
    *EN_PLACE_NOISE,
    *ZH_PLACE_NOISE,
})

REGION_FALLBACK_TOKENS = (
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "종로구",
    "마포구",
    "강남구",
    "용산구",
    "중구",
    "해운대구",
    "연제구",
    "부산진구",
    "중랑구",
)


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
    if any(
        k in text or k in lowered
        for k in ("휠체어", "장애인 화장실", "wheelchair", "accessible restroom", "轮椅", "无障碍")
    ):
        return "wheelchair"
    if any(k in text or k in lowered for k in ("기저귀", "수유", "infant", "diaper", "유아", "婴儿")):
        return "infant_care"
    if any(
        k in text or k in lowered
        for k in ("비상벨", "벨 있는", "emergency bell", "safety bell")
    ) and any(k in text for k in ("화장실", "restroom", "toilet", "厕所")):
        return "elderly_safety"
    if any(k in text or k in lowered for k in ("어린이", "child", "kids", "儿童")):
        return "child"
    return None


def extract_place_hint(text: str) -> str:
    """하위 호환 — extract_place_from_text 사용 권장."""
    return extract_place_from_text(text)


def extract_place_from_text(text: str) -> str:
    """사용자 원문에서 장소 힌트 추출 (랜드마크·역·동·구·시도)."""
    stripped = (text or "").strip()
    if not stripped:
        return ""

    cleaned = strip_poi_noise(stripped)

    station = resolve_foreign_station(cleaned) or resolve_foreign_station(stripped)
    if station:
        return station

    poi = resolve_landmark_poi(cleaned) or resolve_landmark_poi(stripped)
    if poi:
        return poi[2]

    for match in STATION_PATTERN.findall(cleaned):
        if match in STATION_REGION:
            return match
        if match.endswith("역") and len(match) >= 2:
            return match

    tokens = cleaned.replace(",", " ").split()
    for dong, _full in sorted(DONG_EXACT.items(), key=lambda x: -len(x[0])):
        if dong in tokens or cleaned == dong:
            return dong

    for match in DONG_PATTERN.findall(cleaned):
        if match in DONG_EXACT:
            return match
        if match.endswith("동") and len(match) >= 2:
            return match

    for match in SIGUNGU_PATTERN.findall(cleaned):
        return match

    for token in REGION_FALLBACK_TOKENS:
        if token in cleaned:
            return token

    for station in STATION_REGION:
        if station.replace("역", "") in cleaned and "역" in cleaned:
            return station

    return ""


def _is_generic_region_token(name: str) -> bool:
    return name in REGION_FALLBACK_TOKENS or name in SIDO_ALIASES or name in SIDO_ALIASES.values()


def merge_place_inputs(place_query: str | None, user_request: str | None) -> str:
    """LLM place_query + user_request 원문 → 서버 측 최적 장소 문자열."""
    pq = strip_poi_noise((place_query or "").strip())
    ur = (user_request or "").strip()

    if pq in PLACE_NOISE_TOKENS:
        pq = ""

    from_text = extract_place_from_text(ur) if ur else ""
    pq_poi = resolve_landmark_poi(pq) if pq else None
    from_poi = resolve_landmark_poi(from_text) if from_text else None

    if pq and ur:
        if pq_poi and (not from_poi or len(pq_poi[2]) >= len(from_poi[2])):
            return pq_poi[2]
        if from_poi and not pq_poi:
            return from_poi[2]
        if pq and not _is_generic_region_token(pq) and _is_generic_region_token(from_text):
            return pq
        if from_text and not _is_generic_region_token(from_text) and (
            _is_generic_region_token(pq) or len(from_text) > len(pq)
        ):
            return from_text
        if pq in ur or from_text == pq:
            return pq
        return from_text or pq

    if pq:
        return pq_poi[2] if pq_poi else pq

    if from_text:
        return from_poi[2] if from_poi else from_text

    if ur:
        cleaned = strip_poi_noise(ur)
        if cleaned and cleaned not in PLACE_NOISE_TOKENS:
            return cleaned

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
    """Return ordered intent tags from user text (한·영·중)."""
    lowered = text.lower()
    intents: list[str] = []
    fk = foreign_intent_keywords()

    def add(tag: str) -> None:
        if tag not in intents:
            intents.append(tag)

    if any(
        k in text or k in lowered
        for k in ("119", "112", "1339", "182", "전화", "신고", "실종", "가스", "누출", "독극물", *fk["hotlines_en"], *fk["hotlines_zh"])
    ):
        add("hotlines")
    if any(
        k in text or k in lowered
        for k in (
            "화장실",
            "restroom",
            "toilet",
            "급똥",
            "똥",
            "볼일",
            "대변",
            "오줌",
            "배변",
            *fk["restroom_en"],
            *fk["restroom_zh"],
        )
    ):
        add("restroom")
    if any(
        k in text or k in lowered
        for k in ("안전비상벨", "범죄예방", "safety bell")
    ) and not any(k in text for k in ("화장실", "restroom", "toilet", "厕所")):
        add("safety_bell")
    if any(
        k in text or k in lowered
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
            *fk["safety_en"],
            *fk["safety_zh"],
        )
    ):
        add("crime_stats")
    if any(k in text or k in lowered for k in ("약국", "pharmacy", *fk["pharmacy_en"], *fk["pharmacy_zh"])):
        add("pharmacy")
    if any(
        k in text or k in lowered
        for k in ("응급실", "병상", "emergency room", *fk["emergency_en"], *fk["emergency_zh"])
    ):
        add("emergency_room")
    if any(
        k in text or k in lowered
        for k in ("소아과", "병원", "의원", "진료", "clinic", "내과", "39度", "39도", "열", "fever", *fk["clinic_en"], *fk["clinic_zh"])
    ) and not any(k in text for k in VETERAN_KEYWORDS):
        add("clinic")
    if any(
        k in text or k in lowered
        for k in ("물품보관함", "짐 맡", "locker", "luggage", *fk["locker_en"], *fk["locker_zh"])
    ):
        add("subway_locker")
    if any(
        k in text or k in lowered
        for k in ("엘리베이터", "휠체어", "접근", "장애인", "elevator", "wheelchair", *fk["accessible_en"], *fk["accessible_zh"])
    ):
        add("accessible")
    if any(k in text or k in lowered for k in ("ATM", "atm", "현금인출")):
        add("atm")
    if any(k in text or k in lowered for k in ("와이파이", "wifi", "wi-fi", *fk["wifi_en"], *fk["wifi_zh"])):
        add("wifi")
    if any(
        k in text or k in lowered
        for k in ("버스정류장", "버스 정류장", "정류장", "정류소", "bus stop", *fk["bus_en"], *fk["bus_zh"])
    ):
        add("bus_stop")
    if any(k in text for k in VETERAN_KEYWORDS):
        add("veteran_hospital")
    if any(k in text or k in lowered for k in ("동물병원", "vet", "veterinary", *fk["vet_en"], *fk["vet_zh"])):
        add("vet")
    if any(k in text or k in lowered for k in ("안전지킴이", "쉼터", "safe182", "아동안전")):
        add("safe_place")
    if any(
        k in text or k in lowered
        for k in ("phrase card", "show to staff", "店员", "怎么说", "怎么说")
    ):
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
