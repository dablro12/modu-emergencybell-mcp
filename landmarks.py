"""Geocode 실패 시 사용하는 주요 랜드마크 좌표 (WGS84 lat, lng)."""

from __future__ import annotations

from region_parse import normalize_place_query

# PlayMCP·관광 질의에 자주 나오는 장소 (Kakao Local 미활성화 대비)
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
    "성수동": (37.5443, 127.0557),
    "성수동 카페거리": (37.5443, 127.0557),
    "seongsu cafe street": (37.5443, 127.0557),
    "seongsu": (37.5443, 127.0557),
    "해운대 해수욕장": (35.158698, 129.160384),
    "해운대": (35.158698, 129.160384),
    "haeundae beach": (35.158698, 129.160384),
    "홍대입구역": (37.557192, 126.925381),
    "hongdae": (37.557192, 126.925381),
}

# 역·랜드마크 → 행정구역 (geocode 없이 region 검색)
LANDMARK_REGION: dict[str, str] = {
    "명동": "서울특별시 중구",
    "명동역": "서울특별시 중구",
    "강남역": "서울특별시 강남구",
    "코엑스": "서울특별시 강남구",
    "coex": "서울특별시 강남구",
    "여의도공원": "서울특별시 영등포구",
    "성수동": "서울특별시 성동구",
    "성수동 카페거리": "서울특별시 성동구",
    "해운대 해수욕장": "부산광역시 해운대구",
    "해운대": "부산광역시 해운대구",
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
    return ""
