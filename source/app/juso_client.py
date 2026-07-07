"""행정안전부 도로명주소 검색 API (juso.go.kr) — 한글·영문."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

from region_parse import parse_place_query

JUSO_KO_API_URL = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
JUSO_ENG_API_URL = "https://business.juso.go.kr/addrlink/addrEngApi.do"
JUSO_CONFM_KEY = os.getenv("JUSO_CONFM_KEY", "")
JUSO_ENG_CONFM_KEY = os.getenv("JUSO_ENG_CONFM_KEY", "")

LATIN_QUERY = re.compile(r"[A-Za-z]{3,}")
KOREAN_QUERY = re.compile(r"[가-힣]")


def is_latin_address_query(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if KOREAN_QUERY.search(stripped):
        return False
    return bool(LATIN_QUERY.search(stripped))


async def _fetch_juso(
    *,
    url: str,
    key: str,
    keyword: str,
    page: int,
    count_per_page: int,
) -> list[dict[str, Any]]:
    if not key or not keyword.strip():
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
            response = await client.get(url, params=params)
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


async def search_address(
    keyword: str,
    *,
    page: int = 1,
    count_per_page: int = 5,
) -> list[dict[str, Any]]:
    """한글 도로명·지번 주소 검색."""
    return await _fetch_juso(
        url=JUSO_KO_API_URL,
        key=JUSO_CONFM_KEY,
        keyword=keyword,
        page=page,
        count_per_page=count_per_page,
    )


async def search_address_english(
    keyword: str,
    *,
    page: int = 1,
    count_per_page: int = 5,
) -> list[dict[str, Any]]:
    """영문 도로명주소 검색 (외국인·영문 주소 입력)."""
    return await _fetch_juso(
        url=JUSO_ENG_API_URL,
        key=JUSO_ENG_CONFM_KEY,
        keyword=keyword,
        page=page,
        count_per_page=count_per_page,
    )


def _dong_from_kor_addr(kor_addr: str) -> str:
    parts = kor_addr.replace(",", " ").split()
    for part in parts:
        if part.endswith(("동", "읍", "면", "리", "가")):
            return part
    return ""


def _normalize_juso_row(row: dict[str, Any], *, lang: str) -> dict[str, str]:
    kor_addr = (row.get("korAddr") or "").strip()
    road = (row.get("roadAddr") or "").strip()
    jibun = (row.get("jibunAddr") or "").strip()

    if lang == "en" and kor_addr:
        sido, sigungu = parse_place_query(kor_addr)
        dong = _dong_from_kor_addr(kor_addr) or (row.get("emdNm") or "").strip()
        return {
            "sido": sido,
            "sigungu": sigungu,
            "dong": dong,
            "road_addr": kor_addr,
            "road_addr_en": road,
            "jibun_addr": jibun,
            "jibun_addr_en": jibun,
            "expanded_query": kor_addr,
            "display_addr_en": road or jibun,
            "lang": "en",
        }

    sido = (row.get("siNm") or "").strip()
    sigungu = (row.get("sggNm") or "").strip()
    dong = (row.get("emdNm") or row.get("liNm") or "").strip()
    return {
        "sido": sido,
        "sigungu": sigungu,
        "dong": dong,
        "road_addr": road,
        "jibun_addr": jibun,
        "expanded_query": road or jibun or " ".join(x for x in (sido, sigungu, dong) if x),
        "lang": "ko",
    }


async def resolve_administrative(
    keyword: str,
    *,
    prefer_english: bool | None = None,
) -> dict[str, str] | None:
    """첫 번째 juso 결과에서 행정구역·주소 문자열 반환."""
    use_english = is_latin_address_query(keyword) if prefer_english is None else prefer_english

    if use_english and JUSO_ENG_CONFM_KEY:
        rows = await search_address_english(keyword, count_per_page=5)
        if rows:
            return _normalize_juso_row(rows[0], lang="en")

    rows = await search_address(keyword, count_per_page=5)
    if not rows and JUSO_ENG_CONFM_KEY and not use_english:
        rows_en = await search_address_english(keyword, count_per_page=5)
        if rows_en:
            return _normalize_juso_row(rows_en[0], lang="en")

    if not rows:
        return None

    result = _normalize_juso_row(rows[0], lang="ko")
    if not result.get("sido") and not result.get("sigungu"):
        return None
    return result
