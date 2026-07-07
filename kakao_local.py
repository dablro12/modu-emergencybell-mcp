"""Kakao Local REST API client (Geocoding / place search)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from landmarks import lookup_landmark_coords, lookup_landmark_region, lookup_sido_centroid
from region_parse import (
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
    params: dict[str, Any] = {"query": query, "size": min(size, 15)}
    if x is not None and y is not None:
        params["x"] = x
        params["y"] = y
    if radius is not None:
        params["radius"] = radius

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{KAKAO_LOCAL_BASE}/v2/local/search/keyword.json",
            headers=_headers(),
            params=params,
        )
        if response.status_code != 200:
            return []
        return response.json().get("documents", [])


async def search_address(query: str, *, size: int = 1) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{KAKAO_LOCAL_BASE}/v2/local/search/address.json",
            headers=_headers(),
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
        return float(ra["y"]), float(ra["x"])
    if doc.get("address"):
        ad = doc["address"]
        return float(ad["y"]), float(ad["x"])
    return None


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
    stripped = query.strip()
    if not stripped:
        return None

    coords = lookup_landmark_coords(stripped)
    if coords:
        return coords

    sido_hint = extract_sido_hint(stripped)
    anchor = _geocode_anchor(stripped, sido_hint)

    kakao_coords = await _geocode_via_kakao(stripped, sido_hint=sido_hint, anchor=anchor)
    if kakao_coords:
        return kakao_coords

    if anchor and sido_hint:
        return anchor

    normalized = normalize_place_query(stripped)
    return lookup_landmark_coords(normalized)


async def resolve_place(
    query: str,
) -> tuple[float | None, float | None, str]:
    """좌표 + 행정구역 prefix 반환 (자연어 place_query용)."""
    coords = await geocode_place(query)
    region_prefix = lookup_landmark_region(query)
    if not region_prefix:
        sido, sigungu = parse_place_query(query)
        region_prefix = region_full_prefix(sido, sigungu)
    if coords:
        return coords[0], coords[1], region_prefix
    return None, None, region_prefix
