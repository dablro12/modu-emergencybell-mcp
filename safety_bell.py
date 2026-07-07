"""범죄예방 안전비상벨(길·공원) 로컬 검색."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from helpers import haversine_m
from kakao_local import coord_to_region, geocode_place, resolve_place
from landmarks import lookup_landmark_coords, lookup_landmark_region
from region_parse import (
    address_matches_sido,
    extract_sido_hint,
    normalize_place_query,
    parse_place_query,
    region_full_prefix,
    regions_match,
)

DATA_DIR = Path(__file__).resolve().parent / "data" / "emergencybell"
RECORDS_FILE = DATA_DIR / "safety_bell_records.json"

RADIUS_STEPS = (500, 1000, 2000, 3000)

SAFETY_BELL_DISCLAIMER = (
    "⚠️ **안내**: 범죄예방용 **길·공원 안전비상벨** 위치입니다. "
    "화장실 벽 비상벨(`search_restroom` · `user_type=elderly_safety`)과 다릅니다. "
    "**119 신고 대행·발신 없음.** 생명이 위협되면 **112**(범죄) 또는 **119**(응급)에 직접 전화하세요."
)


@lru_cache(maxsize=1)
def load_records() -> tuple[dict[str, Any], ...]:
    if not RECORDS_FILE.exists():
        return tuple()
    with RECORDS_FILE.open(encoding="utf-8") as f:
        return tuple(json.load(f))


def _bell_address(bell: dict[str, Any]) -> str:
    return bell.get("road_addr") or bell.get("jibun_addr") or ""


def _filter_by_sido(bells: list[dict[str, Any]], sido_hint: str) -> list[dict[str, Any]]:
    if not sido_hint:
        return bells
    matched = [b for b in bells if address_matches_sido(_bell_address(b), sido_hint)]
    return matched or bells


def _filter_by_place_type(bells: list[dict[str, Any]], place_type: str | None) -> list[dict[str, Any]]:
    if not place_type:
        return bells
    needle = place_type.strip()
    filtered = [b for b in bells if needle in (b.get("place_type") or "")]
    return filtered or bells


def search_safety_bells(
    *,
    latitude: float,
    longitude: float,
    radius_m: int = 500,
    place_type: str | None = None,
    region_prefix: str = "",
    sido_hint: str = "",
    limit: int = 5,
    strict_region: bool = False,
) -> list[dict[str, Any]]:
    records = list(load_records())
    results: list[dict[str, Any]] = []

    for record in records:
        if strict_region and region_prefix and not regions_match(record["region"]["full_prefix"], region_prefix):
            continue
        dist = haversine_m(latitude, longitude, record["lat"], record["lng"])
        if dist > radius_m:
            continue
        results.append({**record, "distance_m": int(dist)})

    results.sort(key=lambda r: r["distance_m"])
    results = _filter_by_sido(results, sido_hint)
    results = _filter_by_place_type(results, place_type)
    return results[:limit]


def format_safety_bell_list(
    bells: list[dict[str, Any]],
    *,
    query: str | None = None,
    coords_hint: str | None = None,
    radius_used: int | None = None,
    region_mismatch: bool = False,
) -> str:
    if not bells:
        hint = query or "해당 장소"
        return (
            f"**{hint}** 근처에서 안전비상벨을 찾지 못했습니다.\n"
            "- **구/군 + 랜드마크**로 다시 시도해 보세요 (예: `서울 용산구 이태원`, `부산 광안리`).\n"
            "- 화장실 **벽 비상벨**은 `search_restroom`(user_type=elderly_safety)을 사용하세요.\n\n"
            f"{SAFETY_BELL_DISCLAIMER}"
        )

    lines = ["## 길·공원 안전비상벨 (범죄예방)"]
    if query:
        lines.append(f"- 검색: **{query}**")
    if coords_hint:
        lines.append(f"- 기준 위치: {coords_hint}")
    if radius_used:
        lines.append(f"- 검색 반경: **{radius_used}m**")
    if region_mismatch:
        lines.append("- ⚠️ 일부 결과가 요청 지역과 다를 수 있어 **주소를 꼭 확인**하세요.")
    lines.append("")

    for idx, bell in enumerate(bells, start=1):
        addr = _bell_address(bell)
        lines.append(f"### {idx}. {bell['place_type'] or '안전비상벨'} · 약 {bell['distance_m']}m")
        if bell["location"]:
            lines.append(f"- **설치위치**: {bell['location']}")
        if addr:
            lines.append(f"- **주소**: {addr}")
        if bell["link_mode"]:
            lines.append(f"- **연계**: {bell['link_mode']}")
        links = []
        if bell["police_link"] == "Y":
            links.append("경찰")
        if bell["security_link"] == "Y":
            links.append("경비")
        if bell["office_link"] == "Y":
            links.append("관리사무소")
        if links:
            lines.append(f"- **연계기관**: {', '.join(links)}")
        if bell["mgmt_org"]:
            lines.append(f"- **관리**: {bell['mgmt_org']}")
        if bell["mgmt_tel"]:
            lines.append(f"- **관리 연락처**: {bell['mgmt_tel']}")
        lines.append("")

    lines.append(SAFETY_BELL_DISCLAIMER)
    lines.append("_출처: 행정안전부 전국안전비상벨위치 표준데이터 (공공데이터)_")
    return "\n".join(lines)


def _region_centroid(region_prefix: str) -> tuple[float, float] | None:
    matches = [r for r in load_records() if regions_match(r["region"]["full_prefix"], region_prefix)]
    if not matches:
        return None
    lat = sum(r["lat"] for r in matches) / len(matches)
    lng = sum(r["lng"] for r in matches) / len(matches)
    return lat, lng


def _coords_hint(lat: float, lng: float, *, region_prefix: str = "", fallback: bool = False) -> str:
    hint = f"{lat:.6f},{lng:.6f}"
    if fallback and region_prefix:
        hint += f" (지역 중심 추정 · {region_prefix})"
    return hint


async def find_safety_bells_near(
    *,
    place_query: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_m: int = 500,
    place_type: str | None = None,
    limit: int = 5,
) -> str:
    lat, lng = latitude, longitude
    region_prefix = ""
    region_fallback = False
    normalized_query = normalize_place_query(place_query) if place_query else None
    sido_hint = extract_sido_hint(place_query) if place_query else ""

    if place_query and (lat is None or lng is None):
        resolved_lat, resolved_lng, region_prefix = await resolve_place(place_query)
        if resolved_lat is not None and resolved_lng is not None:
            lat, lng = resolved_lat, resolved_lng
        elif not region_prefix:
            region_prefix = lookup_landmark_region(place_query)
            if not region_prefix:
                sido, sigungu = parse_place_query(place_query)
                region_prefix = region_full_prefix(sido, sigungu)

    if lat is not None and lng is not None and not region_prefix:
        try:
            region = await coord_to_region(lng, lat)
            if region and region.get("region_name"):
                region_prefix = region["region_name"]
        except (ValueError, OSError):
            pass

    if (lat is None or lng is None) and region_prefix:
        centroid = _region_centroid(region_prefix)
        if centroid:
            lat, lng = centroid
            region_fallback = True

    if lat is None or lng is None:
        return (
            f"**{place_query or '해당 장소'}** 위치를 특정하지 못했습니다.\n"
            "- **시·구 + 랜드마크**로 다시 말씀해 주세요 (예: `서울 용산구 이태원`, `부산 수영구 광안리`).\n\n"
            f"{SAFETY_BELL_DISCLAIMER}"
        )

    bells: list[dict[str, Any]] = []
    radius_used = radius_m
    for step in RADIUS_STEPS:
        if step < radius_m:
            continue
        radius_used = step if region_fallback else max(step, radius_m)
        bells = search_safety_bells(
            latitude=lat,
            longitude=lng,
            radius_m=radius_used,
            place_type=place_type,
            region_prefix=region_prefix,
            sido_hint=sido_hint,
            limit=limit,
            strict_region=False,
        )
        if bells:
            break

    region_mismatch = bool(
        sido_hint and bells and not all(address_matches_sido(_bell_address(b), sido_hint) for b in bells)
    )
    if region_mismatch:
        strict = _filter_by_sido(bells, sido_hint)
        if strict:
            bells = strict[:limit]

    coords_hint = _coords_hint(lat, lng, region_prefix=region_prefix, fallback=region_fallback)
    return format_safety_bell_list(
        bells,
        query=normalized_query or place_query,
        coords_hint=coords_hint,
        radius_used=radius_used if bells else None,
        region_mismatch=region_mismatch,
    )
