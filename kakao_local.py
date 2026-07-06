"""Kakao Local REST API client (Geocoding / place search)."""

from __future__ import annotations

import os
from typing import Any

import httpx

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
    """장소 키워드 검색 (예: '벡스코', '서울대학교병원')."""
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
    """주소 검색 → 좌표 (도로명/지번)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{KAKAO_LOCAL_BASE}/v2/local/search/address.json",
            headers=_headers(),
            params={"query": query, "size": min(size, 10)},
        )
        if response.status_code != 200:
            return []
        return response.json().get("documents", [])


async def coord_to_region(longitude: float, latitude: float) -> dict[str, str] | None:
    """WGS84 좌표 → 행정구역 (시도/시군구)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{KAKAO_LOCAL_BASE}/v2/local/geo/coord2regioncode.json",
            headers=_headers(),
            params={"x": longitude, "y": latitude},
        )
        if response.status_code != 200:
            return None
        documents = response.json().get("documents", [])
        if not documents:
            return None
        doc = documents[0]
        return {
            "region_code": doc.get("code", ""),
            "region_name": doc.get("address_name", ""),
            "region_type": doc.get("region_type", ""),
        }


async def geocode_place(query: str) -> tuple[float, float] | None:
    """장소명/키워드를 WGS84 (latitude, longitude)로 변환."""
    documents = await search_keyword(query, size=1)
    if not documents:
        documents = await search_address(query, size=1)
    if not documents:
        return None

    doc = documents[0]
    if "y" in doc and "x" in doc:
        return float(doc["y"]), float(doc["x"])

    if doc.get("road_address"):
        return float(doc["road_address"]["y"]), float(doc["road_address"]["x"])
    if doc.get("address"):
        return float(doc["address"]["y"]), float(doc["address"]["x"])
    return None
