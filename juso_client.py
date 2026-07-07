"""행정안전부 도로명주소 검색 API (juso.go.kr)."""

from __future__ import annotations

import os
from typing import Any

import httpx

JUSO_API_URL = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
JUSO_CONFM_KEY = os.getenv("JUSO_CONFM_KEY", "")


def _require_key() -> str:
    if not JUSO_CONFM_KEY:
        raise ValueError("JUSO_CONFM_KEY is not set")
    return JUSO_CONFM_KEY


async def search_address(
    keyword: str,
    *,
    page: int = 1,
    count_per_page: int = 5,
) -> list[dict[str, Any]]:
    """주소 검색어 → 도로명·지번 주소 및 시·군·구·동."""
    key = JUSO_CONFM_KEY
    if not key:
        return []

    params = {
        "confmKey": key,
        "currentPage": max(page, 1),
        "countPerPage": min(max(count_per_page, 1), 10),
        "keyword": keyword.strip(),
        "resultType": "json",
        "hstryYn": "N",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(JUSO_API_URL, params=params)
            if response.status_code != 200:
                return []
            payload = response.json()
    except (ValueError, OSError, httpx.HTTPError):
        return []

    results = payload.get("results") or {}
    common = results.get("common") or {}
    if str(common.get("errorCode", "")) not in ("0", "00"):
        return []

    rows = results.get("juso") or []
    return [row for row in rows if isinstance(row, dict)]


async def resolve_administrative(keyword: str) -> dict[str, str] | None:
    """첫 번째 juso 결과에서 행정구역·주소 문자열 반환."""
    rows = await search_address(keyword, count_per_page=5)
    if not rows:
        return None

    row = rows[0]
    sido = (row.get("siNm") or "").strip()
    sigungu = (row.get("sggNm") or "").strip()
    dong = (row.get("emdNm") or row.get("liNm") or "").strip()
    road = (row.get("roadAddr") or "").strip()
    jibun = (row.get("jibunAddr") or "").strip()
    if not sido and not sigungu:
        return None

    return {
        "sido": sido,
        "sigungu": sigungu,
        "dong": dong,
        "road_addr": road,
        "jibun_addr": jibun,
        "expanded_query": road or jibun or " ".join(x for x in (sido, sigungu, dong) if x),
    }
