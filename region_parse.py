"""한국 행정구역 파싱 및 장소 쿼리 정규화."""

from __future__ import annotations

SIDO_ALIASES: dict[str, str] = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}

SEOUL_DISTRICTS = frozenset({
    "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구",
    "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구",
    "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구",
})

# 영문·약어 → Kakao/검색에 유리한 한글 (PlayMCP 다국어 질의)
PLACE_QUERY_ALIASES: dict[str, str] = {
    "myeongdong station": "명동역",
    "myeongdong": "명동",
    "gangnam station": "강남역",
    "gangnam": "강남",
    "hongdae": "홍대입구역",
    "coex": "코엑스",
    "yeouido park": "여의도공원",
    "yeouido": "여의도",
    "seongsu": "성수동",
    "seongsu cafe street": "성수동 카페거리",
    "haeundae beach": "해운대 해수욕장",
    "haeundae": "해운대",
    "bexco": "벡스코",
    "mapo": "마포구",
    "yongsan": "용산구",
}


def normalize_place_query(query: str) -> str:
    """영문 장소명 등을 검색 친화적 한글로 변환."""
    stripped = query.strip()
    if not stripped:
        return stripped
    key = stripped.lower()
    if key in PLACE_QUERY_ALIASES:
        return PLACE_QUERY_ALIASES[key]
    for alias, korean in PLACE_QUERY_ALIASES.items():
        if alias in key:
            return korean
    return stripped


def parse_place_query(query: str) -> tuple[str, str]:
    """장소 문자열에서 시도·시군구 추출 (geocode 없이)."""
    normalized = normalize_place_query(query)
    parts = normalized.replace(",", " ").split()
    sido = ""
    sigungu = ""

    for part in parts:
        if part in SIDO_ALIASES:
            sido = SIDO_ALIASES[part]
            continue
        if any(
            part.endswith(s)
            for s in ("특별시", "광역시", "특별자치시", "특별자치도")
        ) or (part.endswith("도") and len(part) <= 5):
            sido = part
            continue
        if part.endswith(("구", "군")):
            sigungu = part
            continue
        if part.endswith("시") and part not in SIDO_ALIASES.values():
            if not sigungu:
                sigungu = part

    if not sido and sigungu in SEOUL_DISTRICTS:
        sido = "서울특별시"

    return sido, sigungu


def region_full_prefix(sido: str, sigungu: str) -> str:
    return f"{sido} {sigungu}".strip()


def sigungu_token(text: str) -> str:
    """'서울특별시 중구' → '중구', '중구' → '중구'."""
    parts = text.split()
    for part in reversed(parts):
        if part.endswith(("구", "군", "시")):
            return part
    return text


def regions_match(record_prefix: str, region_hint: str) -> bool:
    """행정구역 문자열 상호 매칭 (Kakao 응답 형식 차이 흡수)."""
    if not region_hint:
        return True
    if not record_prefix:
        return True
    if record_prefix in region_hint or region_hint in record_prefix:
        return True
    if sigungu_token(record_prefix) == sigungu_token(region_hint):
        return True
    record_parts = set(record_prefix.split())
    hint_parts = set(region_hint.split())
    if record_parts & hint_parts:
        return True
    return False
