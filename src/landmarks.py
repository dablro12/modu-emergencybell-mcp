"""Geocode 실패 시 사용하는 주요 랜드마크 좌표 (WGS84 lat, lng)."""

from __future__ import annotations

import re

from region_parse import normalize_place_query

POI_NOISE = re.compile(r"^\d+$|^\(.+\)$")
POI_SUFFIXES = (
    " 근처",
    " 부근",
    " 일대",
    " 인근",
    " 앞",
    " 뒤",
    " 옆",
    " 근방",
    " 주변",
    "쪽",
    "쪽에",
    " near",
    " nearby",
    " area",
    " around",
    "附近",
    "周边",
    "一带",
)
POI_CHAT_NOISE = re.compile(
    r"(급똥|똥|급히|지금\s?여기|알려\s?줘|찾아\s?줘|제발|도와\s?줘|"
    r"어디(?:있어|있냐|야|임)?|"
    r"urgent(?:ly)?|please|help\s*me|where\s+is|"
    r"在哪|哪里|帮帮我)",
    re.IGNORECASE,
)
# 의도·시설 키워드 + 붙는 조사/연결어 (화장실도, 화장실이랑 등 통째 제거)
INTENT_PHRASE_NOISE = re.compile(
    r"(?:"
    r"화장실|비상벨|편의점|약국|응급실|응급|병원|의원|캐리어|와이파이|wifi|"
    r"restroom|toilet|bathroom|safety\s*bell|emergency\s*bell|pharmacy|hospital|"
    r"厕所|洗手间|卫生间|비상"
    r")(?:이랑|랑|하고|과|와|도|은|는|을|를)?(?:\s*(?:급하고|급해|급함|없어|없냐|없을까))?",
    re.IGNORECASE,
)
ORPHAN_CONNECTOR_NOISE = re.compile(r"\s*(?:이랑|랑|하고|과|와)\s+")
TRAILING_CHAT_NOISE = re.compile(
    r"(?:인데|는데|데|야|요|임|음|ㅋ+|ㅎ+)(?:\s*도\s*)?"
    r"(?:급하고|급해|급함|없어|없냐|없을까|어디|어디있|어디있어|어디야)?\s*$"
)
ROAD_GIL_PATTERN = re.compile(
    r"([\uac00-\ud7a3]+(?:골목길|골목|대로|로|길)(?:\d+가|-?\d+)?)"
)
LANDMARK_COORDS: dict[str, tuple[float, float]] = {
    "명동": (37.5636, 126.9834),
    "명동성당": (37.5633, 126.9870),
    "myeongdong cathedral": (37.5633, 126.9870),
    "명동역": (37.560993, 126.986502),
    "myeongdong station": (37.560993, 126.986502),
    "myeongdong": (37.5636, 126.9834),
    "경복궁역": (37.575762, 126.973530),
    "gyeongbokgung station": (37.575762, 126.973530),
    "강남역": (37.497942, 127.027621),
    "gangnam station": (37.497942, 127.027621),
    "코엑스": (37.512535, 127.058834),
    "coex": (37.512535, 127.058834),
    "여의도공원": (37.528423, 126.932901),
    "yeouido park": (37.528423, 126.932901),
    "yeouido": (37.5219, 126.9245),
    "한강공원 여의도": (37.528423, 126.932901),
    "성수동": (37.5443, 127.0557),
    "성수동 카페거리": (37.5443, 127.0557),
    "seongsu cafe street": (37.5443, 127.0557),
    "seongsu": (37.5443, 127.0557),
    "해운대 해수욕장": (35.158698, 129.160384),
    "해운대": (35.158698, 129.160384),
    "haeundae beach": (35.158698, 129.160384),
    "홍대입구역": (37.557192, 126.925381),
    "hongdae": (37.557192, 126.925381),
    "이태원": (37.5345, 126.9946),
    "itaewon": (37.5345, 126.9946),
    "해밀턴호텔": (37.5345, 126.9946),
    "이태원 해밀턴호텔": (37.5345, 126.9946),
    "광안리": (35.1532, 129.1186),
    "광안리 해수욕장": (35.1532, 129.1186),
    "gwangalli": (35.1532, 129.1186),
    "서면역": (35.1578, 129.0599),
    "seomyeon": (35.1578, 129.0599),
    "제주공항": (33.5066, 126.4926),
    "jeju airport": (33.5066, 126.4926),
    # 中文 랜드마크
    "明洞": (37.5636, 126.9834),
    "明洞圣堂": (37.5633, 126.9870),
    "明洞大教堂": (37.5633, 126.9870),
    "江南": (37.497942, 127.027621),
    "江南站": (37.497942, 127.027621),
    "梨泰院": (37.5345, 126.9946),
    "海云台": (35.158698, 129.160384),
    "海雲台": (35.158698, 129.160384),
    "弘大": (37.557192, 126.925381),
    "西面": (35.1578, 129.0599),
    "光安里": (35.1532, 129.1186),
    "济州机场": (33.5066, 126.4926),
    "首尔站": (37.5544, 126.9706),
}

LANDMARK_REGION: dict[str, str] = {
    "명동": "서울특별시 중구",
    "명동성당": "서울특별시 중구",
    "명동역": "서울특별시 중구",
    "경복궁역": "서울특별시 종로구",
    "강남역": "서울특별시 강남구",
    "코엑스": "서울특별시 강남구",
    "coex": "서울특별시 강남구",
    "여의도공원": "서울특별시 영등포구",
    "한강공원 여의도": "서울특별시 영등포구",
    "성수동": "서울특별시 성동구",
    "이태원": "서울특별시 용산구",
    "해밀턴호텔": "서울특별시 용산구",
    "해운대 해수욕장": "부산광역시 해운대구",
    "광안리": "부산광역시 수영구",
    "광안리 해수욕장": "부산광역시 수영구",
    "서면역": "부산광역시 부산진구",
    "明洞": "서울특별시 중구",
    "明洞圣堂": "서울특별시 중구",
    "江南": "서울특별시 강남구",
    "梨泰院": "서울특별시 용산구",
    "海云台": "부산광역시 해운대구",
    "弘大": "서울특별시 마포구",
    "光安里": "부산광역시 수영구",
}

# 쿼리 문자열에 포함되면 매칭 (긴 키워드 우선)
PARTIAL_LANDMARKS: tuple[tuple[str, tuple[float, float], str], ...] = (
    ("명동성당", (37.5633, 126.9870), "서울특별시 중구"),
    ("myeongdong cathedral", (37.5633, 126.9870), "서울특별시 중구"),
    ("明洞圣堂", (37.5633, 126.9870), "서울특별시 중구"),
    ("明洞大教堂", (37.5633, 126.9870), "서울특별시 중구"),
    ("gangnam station", (37.497942, 127.027621), "서울특별시 강남구"),
    ("江南", (37.497942, 127.027621), "서울특별시 강남구"),
    ("한강공원 여의도", (37.528423, 126.932901), "서울특별시 영등포구"),
    ("이태원 해밀턴", (37.5345, 126.9946), "서울특별시 용산구"),
    ("해밀턴호텔", (37.5345, 126.9946), "서울특별시 용산구"),
    ("광안리 해수욕장", (35.1532, 129.1186), "부산광역시 수영구"),
    ("광안리", (35.1532, 129.1186), "부산광역시 수영구"),
    ("명동", (37.5636, 126.9834), "서울특별시 중구"),
    ("경복궁역", (37.575762, 126.973530), "서울특별시 종로구"),
    ("gyeongbokgung station", (37.575762, 126.973530), "서울특별시 종로구"),
    ("明洞", (37.5636, 126.9834), "서울특별시 중구"),
    ("myeongdong", (37.5636, 126.9834), "서울특별시 중구"),
    ("홍대", (37.557192, 126.925381), "서울특별시 마포구"),
    ("한강공원", (37.528423, 126.932901), "서울특별시 영등포구"),
    ("여의도", (37.5219, 126.9245), "서울특별시 영등포구"),
    ("이태원", (37.5345, 126.9946), "서울특별시 용산구"),
    ("해운대", (35.158698, 129.160384), "부산광역시 해운대구"),
    ("海云台", (35.158698, 129.160384), "부산광역시 해운대구"),
    ("itaewon", (37.5345, 126.9946), "서울특별시 용산구"),
    ("梨泰院", (37.5345, 126.9946), "서울특별시 용산구"),
    ("hongdae", (37.557192, 126.925381), "서울특별시 마포구"),
    ("弘大", (37.557192, 126.925381), "서울특별시 마포구"),
    ("서면", (35.1578, 129.0599), "부산광역시 부산진구"),
)

SIDO_CENTROIDS: dict[str, tuple[float, float]] = {
    "서울특별시": (37.5665, 126.9780),
    "부산광역시": (35.1796, 129.0756),
    "대구광역시": (35.8714, 128.6014),
    "인천광역시": (37.4563, 126.7052),
    "광주광역시": (35.1595, 126.8526),
    "대전광역시": (36.3504, 127.3845),
    "울산광역시": (35.5384, 129.3114),
    "세종특별자치시": (36.4800, 127.2890),
    "경기도": (37.4138, 127.5183),
    "강원특별자치도": (37.8228, 128.1555),
    "충청북도": (36.6357, 127.4917),
    "충청남도": (36.5184, 126.8000),
    "전북특별자치도": (35.7175, 127.1530),
    "전라남도": (34.8679, 126.9910),
    "경상북도": (36.4919, 128.8889),
    "경상남도": (35.4606, 128.2132),
    "제주특별자치도": (33.4890, 126.4983),
}


def strip_poi_noise(query: str) -> str:
    """자연어 잡음(쪽·근처·급똥·near·附近 등) 제거 후 POI 키워드만 남김."""
    from i18n_support import strip_multilingual_noise

    stripped = (query or "").strip()
    if not stripped:
        return stripped

    cleaned = INTENT_PHRASE_NOISE.sub(" ", stripped)
    cleaned = POI_CHAT_NOISE.sub(" ", cleaned)
    cleaned = strip_multilingual_noise(cleaned)
    cleaned = ORPHAN_CONNECTOR_NOISE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.!?，。！？")

    while cleaned:
        next_cleaned = TRAILING_CHAT_NOISE.sub("", cleaned).strip(" ,.!?")
        if next_cleaned == cleaned:
            break
        cleaned = next_cleaned

    for suffix in POI_SUFFIXES:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned or stripped


def resolve_landmark_poi(query: str) -> tuple[tuple[float, float], str, str] | None:
    """부분 랜드마크 매칭 — (좌표, 행정구역, 키워드)."""
    for candidate in (
        strip_poi_noise(query),
        (query or "").strip(),
        normalize_place_query(strip_poi_noise(query)),
    ):
        if not candidate:
            continue
        lowered = candidate.lower()
        for keyword, coords, region in sorted(PARTIAL_LANDMARKS, key=lambda x: -len(x[0])):
            if keyword in candidate or keyword.lower() in lowered:
                return coords, region, keyword
        for key in (candidate, lowered):
            if key in LANDMARK_COORDS:
                region = LANDMARK_REGION.get(key) or LANDMARK_REGION.get(candidate, "")
                return LANDMARK_COORDS[key], region, candidate
    return None


def lookup_landmark_coords(query: str) -> tuple[float, float] | None:
    poi = resolve_landmark_poi(query)
    if poi:
        return poi[0]
    return None


def lookup_landmark_region(query: str) -> str:
    poi = resolve_landmark_poi(query)
    if poi:
        return poi[1]
    stripped = query.strip()
    if not stripped:
        return ""
    normalized = normalize_place_query(stripped)
    for candidate in (normalized, stripped):
        if candidate in LANDMARK_REGION:
            return LANDMARK_REGION[candidate]
        key = candidate.lower()
        if key in LANDMARK_REGION:
            return LANDMARK_REGION[key]
    return ""


def lookup_sido_centroid(sido: str) -> tuple[float, float] | None:
    if not sido:
        return None
    if sido in SIDO_CENTROIDS:
        return SIDO_CENTROIDS[sido]
    for key, coords in SIDO_CENTROIDS.items():
        if sido in key or key.startswith(sido[:2]):
            return coords
    return None


def extract_landmark_search_term(query: str) -> str:
    """API·토큰 검색용 랜드마크명 — 주소 번지·괄호 동명은 제외."""
    stripped = strip_poi_noise(query)
    if not stripped:
        return ""
    poi = resolve_landmark_poi(stripped)
    if poi:
        return poi[2]
    lowered = stripped.lower()
    for keyword, _coords, _region in sorted(PARTIAL_LANDMARKS, key=lambda x: -len(x[0])):
        if keyword in stripped or keyword.lower() in lowered:
            return keyword
    for candidate in (stripped, normalize_place_query(stripped)):
        if candidate in LANDMARK_COORDS:
            return candidate
        key = candidate.lower()
        if key in LANDMARK_COORDS:
            return key
    tokens: list[str] = []
    for tok in stripped.replace(",", " ").split():
        tok = tok.strip()
        if len(tok) < 2 or tok.isdigit() or POI_NOISE.match(tok):
            continue
        if tok.startswith("(") and tok.endswith(")"):
            continue
        tokens.append(tok)
    for tok in tokens:
        if not any(ch.isdigit() for ch in tok):
            return tok
    return tokens[0] if tokens else stripped
