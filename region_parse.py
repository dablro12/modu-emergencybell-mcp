"""한국 행정구역 파싱 (Kakao geocode 실패 시 fallback)."""

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


def parse_place_query(query: str) -> tuple[str, str]:
    """장소 문자열에서 시도·시군구 추출 (geocode 없이)."""
    parts = query.strip().replace(",", " ").split()
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
