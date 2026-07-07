"""Geocode 실패 시 사용하는 주요 랜드마크 좌표 (WGS84 lat, lng)."""

from __future__ import annotations

from region_parse import normalize_place_query

LANDMARK_COORDS: dict[str, tuple[float, float]] = {
    "명동": (37.5636, 126.9834),
    "명동역": (37.560993, 126.986502),
    "myeongdong station": (37.560993, 126.986502),
    "myeongdong": (37.5636, 126.9834),
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
}

LANDMARK_REGION: dict[str, str] = {
    "명동": "서울특별시 중구",
    "명동역": "서울특별시 중구",
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
}

# 쿼리 문자열에 포함되면 매칭 (긴 키워드 우선)
PARTIAL_LANDMARKS: tuple[tuple[str, tuple[float, float], str], ...] = (
    ("한강공원 여의도", (37.528423, 126.932901), "서울특별시 영등포구"),
    ("이태원 해밀턴", (37.5345, 126.9946), "서울특별시 용산구"),
    ("해밀턴호텔", (37.5345, 126.9946), "서울특별시 용산구"),
    ("광안리 해수욕장", (35.1532, 129.1186), "부산광역시 수영구"),
    ("광안리", (35.1532, 129.1186), "부산광역시 수영구"),
    ("한강공원", (37.528423, 126.932901), "서울특별시 영등포구"),
    ("여의도", (37.5219, 126.9245), "서울특별시 영등포구"),
    ("이태원", (37.5345, 126.9946), "서울특별시 용산구"),
    ("해운대", (35.158698, 129.160384), "부산광역시 해운대구"),
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


def lookup_landmark_coords(query: str) -> tuple[float, float] | None:
    stripped = query.strip()
    if not stripped:
        return None
    normalized = normalize_place_query(stripped)
    for candidate in (normalized, stripped):
        key = candidate.lower()
        if key in LANDMARK_COORDS:
            return LANDMARK_COORDS[key]
        if candidate in LANDMARK_COORDS:
            return LANDMARK_COORDS[candidate]
    lowered = stripped.lower()
    for keyword, coords, _region in sorted(PARTIAL_LANDMARKS, key=lambda x: -len(x[0])):
        if keyword in stripped or keyword.lower() in lowered:
            return coords
    return None


def lookup_landmark_region(query: str) -> str:
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
    lowered = stripped.lower()
    for keyword, _coords, region in sorted(PARTIAL_LANDMARKS, key=lambda x: -len(x[0])):
        if keyword in stripped or keyword.lower() in lowered:
            return region
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
