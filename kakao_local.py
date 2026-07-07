"""Kakao Local REST API client (Geocoding / place search)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from landmarks import lookup_landmark_coords, lookup_landmark_region, lookup_sido_centroid
from region_parse import (
    SIDO_ALIASES,
    extract_sido_hint,
    kakao_doc_matches_sido,
    normalize_place_query,
    parse_place_query,
    region_full_prefix,
)

KAKAO_LOCAL_BASE = "https://dapi.kakao.com"
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")


def _headers() -> dict[str, str]:
    if not KAKAO_REST_API_KEY:
        raise ValueError("KAKAO_REST_API_KEY is not set")
    return {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}


async def search_keyword(
    query: str,
    *,
    x: float | None = None,
    y: float | None = None,
    radius: int | None = None,
    size: int = 1,
) -> list[dict[str, Any]]:
    if not KAKAO_REST_API_KEY:
        return []
    try:
        headers = _headers()
    except ValueError:
        return []

    params: dict[str, Any] = {"query": query, "size": min(size, 15)}
    if x is not None and y is not None:
        params["x"] = x
        params["y"] = y
    if radius is not None:
        params["radius"] = radius

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{KAKAO_LOCAL_BASE}/v2/local/search/keyword.json",
            headers=headers,
            params=params,
        )
        if response.status_code != 200:
            return []
        return response.json().get("documents", [])


async def search_address(query: str, *, size: int = 1) -> list[dict[str, Any]]:
    if not KAKAO_REST_API_KEY:
        return []
    try:
        headers = _headers()
    except ValueError:
        return []

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{KAKAO_LOCAL_BASE}/v2/local/search/address.json",
            headers=headers,
            params={"query": query, "size": min(size, 10)},
        )
        if response.status_code != 200:
            return []
        return response.json().get("documents", [])


def _pick_region_document(documents: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not documents:
        return None
    for preferred in ("H", "B"):
        for doc in documents:
            if doc.get("region_type") == preferred:
                return doc
    return documents[0]


async def coord_to_region(longitude: float, latitude: float) -> dict[str, str] | None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{KAKAO_LOCAL_BASE}/v2/local/geo/coord2regioncode.json",
            headers=_headers(),
            params={"x": longitude, "y": latitude},
        )
        if response.status_code != 200:
            return None
        documents = response.json().get("documents", [])
        doc = _pick_region_document(documents)
        if not doc:
            return None
        return {
            "region_code": doc.get("code", ""),
            "region_name": doc.get("address_name", ""),
            "region_type": doc.get("region_type", ""),
        }


def _coords_from_document(doc: dict[str, Any]) -> tuple[float, float] | None:
    if "y" in doc and "x" in doc and doc["y"] and doc["x"]:
        return float(doc["y"]), float(doc["x"])
    if doc.get("road_address"):
        ra = doc["road_address"]
        if ra.get("y") and ra.get("x"):
            return float(ra["y"]), float(ra["x"])
    if doc.get("address"):
        ad = doc["address"]
        if ad.get("y") and ad.get("x"):
            return float(ad["y"]), float(ad["x"])
    return None


def _normalize_sido_name(name: str) -> str:
    text = (name or "").strip()
    if not text:
        return ""
    if text in SIDO_ALIASES:
        return SIDO_ALIASES[text]
    if any(text.endswith(s) for s in ("특별시", "광역시", "특별자치시", "특별자치도")) or (
        text.endswith("도") and len(text) <= 5
    ):
        return text
    short_map = {
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
    return short_map.get(text, text)


def extract_admin_from_document(doc: dict[str, Any]) -> tuple[str, str, str]:
    """Kakao keyword/address document → (sido, sigungu, dong)."""
    blocks: list[dict[str, Any]] = []
    for key in ("road_address", "address"):
        block = doc.get(key)
        if isinstance(block, dict):
            blocks.append(block)

    for block in blocks:
        sido = _normalize_sido_name(block.get("region_1depth_name", ""))
        sigungu = (block.get("region_2depth_name") or "").strip()
        dong = (block.get("region_3depth_name") or "").strip()
        if sido or sigungu:
            return sido, sigungu, dong

    address_text = " ".join(
        str(doc.get(key, "") or "")
        for key in ("road_address_name", "address_name", "place_name")
    ).strip()
    if address_text:
        parts = address_text.split()
        if parts:
            sido = _normalize_sido_name(parts[0])
            sigungu = parts[1] if len(parts) > 1 and parts[1].endswith(("구", "군", "시")) else ""
            dong = ""
            for part in parts[1:]:
                if part.endswith("동"):
                    dong = part
                    break
            if sido or sigungu:
                return sido, sigungu, dong

    return "", "", ""


async def geocode_via_kakao_candidates(
    query: str,
    *,
    sido_hint: str = "",
    prefer_keyword: bool = False,
    anchor: tuple[float, float] | None = None,
) -> tuple[tuple[float, float] | None, dict[str, Any] | None, str]:
    """Kakao keyword/address 시도 → (coords, document, source_tag)."""
    if not KAKAO_REST_API_KEY:
        return None, None, ""

    normalized = normalize_place_query(query)
    candidates: list[str] = []
    for item in (normalized, query.strip()):
        if item and item not in candidates:
            candidates.append(item)

    search_order = ("keyword", "address") if prefer_keyword else ("address", "keyword")

    for candidate in candidates:
        kwargs: dict[str, Any] = {"size": 5}
        if anchor:
            kwargs["x"] = anchor[1]
            kwargs["y"] = anchor[0]
            kwargs["radius"] = 30_000

        for mode in search_order:
            try:
                if mode == "keyword":
                    documents = await search_keyword(candidate, **kwargs)
                    source = "kakao_keyword"
                else:
                    documents = await search_address(candidate, size=kwargs.get("size", 5))
                    source = "kakao_address"
            except (ValueError, OSError):
                continue

            for doc in documents:
                if sido_hint and not kakao_doc_matches_sido(doc, sido_hint):
                    continue
                coords = _coords_from_document(doc)
                if coords or extract_admin_from_document(doc)[1]:
                    return coords, doc, source

    return None, None, ""


def _geocode_anchor(query: str, sido_hint: str) -> tuple[float, float] | None:
    landmark = lookup_landmark_coords(query)
    if landmark:
        return landmark
    landmark_region = lookup_landmark_region(query)
    if landmark_region:
        _, sigungu = parse_place_query(landmark_region)
        if sigungu:
            partial = lookup_landmark_coords(sigungu)
            if partial:
                return partial
    return lookup_sido_centroid(sido_hint)


async def _geocode_via_kakao(
    query: str,
    *,
    sido_hint: str,
    anchor: tuple[float, float] | None,
) -> tuple[float, float] | None:
    if not KAKAO_REST_API_KEY:
        return None
    try:
        _headers()
    except ValueError:
        return None

    normalized = normalize_place_query(query)
    candidates = []
    for item in (normalized, query.strip()):
        if item and item not in candidates:
            candidates.append(item)

    for candidate in candidates:
        try:
            kwargs: dict[str, Any] = {"size": 5}
            if anchor:
                kwargs["x"] = anchor[1]
                kwargs["y"] = anchor[0]
                kwargs["radius"] = 30_000
            documents = await search_keyword(candidate, **kwargs)
            if not documents:
                documents = await search_address(candidate, size=5)
            for doc in documents:
                if sido_hint and not kakao_doc_matches_sido(doc, sido_hint):
                    continue
                coords = _coords_from_document(doc)
                if coords:
                    return coords
        except (ValueError, OSError):
            continue
    return None


async def geocode_place(query: str) -> tuple[float, float] | None:
    """장소명/키워드를 WGS84 (latitude, longitude)로 변환."""
    from place_resolver import resolve_place_context

    ctx = await resolve_place_context(query)
    return ctx.coords


async def resolve_place(
    query: str,
) -> tuple[float | None, float | None, str]:
    """좌표 + 행정구역 prefix 반환 (자연어 place_query용)."""
    from place_resolver import resolve_place_context

    ctx = await resolve_place_context(query)
    if ctx.coords:
        return ctx.latitude, ctx.longitude, ctx.region_prefix
    return None, None, ctx.region_prefix
