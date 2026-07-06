"""Kakao Local REST API client (Geocoding / place search)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from landmarks import lookup_landmark_coords
from region_parse import normalize_place_query

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
    """WGS84 좌표 → 행정구역 (시군구 우선)."""
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


async def geocode_place(query: str) -> tuple[float, float] | None:
    """장소명/키워드를 WGS84 (latitude, longitude)로 변환."""
    fallback = lookup_landmark_coords(query)
    if fallback:
        return fallback

    normalized = normalize_place_query(query)
    for candidate in (normalized, query.strip()):
        if not candidate:
            continue
        try:
            documents = await search_keyword(candidate, size=1)
            if not documents:
                documents = await search_address(candidate, size=1)
            if documents:
                coords = _coords_from_document(documents[0])
                if coords:
                    return coords
        except (ValueError, OSError):
            break
    return lookup_landmark_coords(normalized)
