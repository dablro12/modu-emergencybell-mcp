"""한국 행정구역 파싱, 장소 쿼리 정규화, 지역 일치 검증."""

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
    "gwangalli beach": "광안리 해수욕장",
    "gwangalli": "광안리",
    "itaewon": "이태원",
    "hamilton hotel": "이태원 해밀턴호텔",
    "bexco": "벡스코",
    "mapo": "마포구",
    "yongsan": "용산구",
    "seocho": "서초구",
    "seomyeon": "서면역",
}

# 시도 약칭 → 주소에 나타나는 토큰
SIDO_ADDRESS_TOKENS: dict[str, tuple[str, ...]] = {
    "서울특별시": ("서울", "서울특별시"),
    "부산광역시": ("부산", "부산광역시"),
    "대구광역시": ("대구", "대구광역시"),
    "인천광역시": ("인천", "인천광역시"),
    "광주광역시": ("광주", "광주광역시"),
    "대전광역시": ("대전", "대전광역시"),
    "울산광역시": ("울산", "울산광역시"),
    "세종특별자치시": ("세종", "세종특별자치시"),
    "경기도": ("경기", "경기도"),
    "강원특별자치도": ("강원", "강원특별자치도", "강원도"),
    "충청북도": ("충북", "충청북도"),
    "충청남도": ("충남", "충청남도"),
    "전북특별자치도": ("전북", "전북특별자치도", "전라북도"),
    "전라남도": ("전남", "전라남도"),
    "경상북도": ("경북", "경상북도"),
    "경상남도": ("경남", "경상남도"),
    "제주특별자치도": ("제주", "제주특별자치도", "제주도"),
}


def normalize_place_query(query: str) -> str:
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


def extract_sido_hint(query: str) -> str:
    sido, _ = parse_place_query(query)
    return sido


def region_full_prefix(sido: str, sigungu: str) -> str:
    return f"{sido} {sigungu}".strip()


def sigungu_token(text: str) -> str:
    parts = text.split()
    for part in reversed(parts):
        if part.endswith(("구", "군", "시")):
            return part
    return text


def regions_match(record_prefix: str, region_hint: str) -> bool:
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


def address_matches_sido(address: str, sido_hint: str) -> bool:
    """결과 주소가 질의 시·도와 일치하는지 검증."""
    if not address or not sido_hint:
        return True
    tokens = SIDO_ADDRESS_TOKENS.get(sido_hint)
    if tokens:
        return any(token in address for token in tokens)
    return sido_hint[:2] in address


def kakao_doc_matches_sido(doc: dict, sido_hint: str) -> bool:
    if not sido_hint:
        return True
    parts = []
    for key in ("address_name", "road_address_name", "place_name"):
        if doc.get(key):
            parts.append(str(doc[key]))
    ra = doc.get("road_address") or {}
    ad = doc.get("address") or {}
    for block in (ra, ad):
        for key in ("address_name", "region_1depth_name", "region_2depth_name"):
            if block.get(key):
                parts.append(str(block[key]))
    return address_matches_sido(" ".join(parts), sido_hint)
