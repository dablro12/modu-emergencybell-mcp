"""범죄예방 안전비상벨(길·공원) 로컬 검색."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from helpers import haversine_m
from kakao_local import coord_to_region, geocode_place
from region_parse import parse_place_query

DATA_DIR = Path(__file__).resolve().parent / "data" / "emergencybell"
RECORDS_FILE = DATA_DIR / "safety_bell_records.json"

SAFETY_BELL_DISCLAIMER = (
    "⚠️ **안내**: 범죄예방용 **길·공원 안전비상벨** 위치입니다. "
    "화장실 벽 비상벨(`search_restroom` · `elderly_safety`)과 다릅니다. "
    "**119 신고 대행·발신 없음.** 생명이 위협되면 **112**(범죄) 또는 **119**(응급)에 직접 전화하세요."
)


@lru_cache(maxsize=1)
def load_records() -> tuple[dict[str, Any], ...]:
    if not RECORDS_FILE.exists():
        return tuple()
    with RECORDS_FILE.open(encoding="utf-8") as f:
        return tuple(json.load(f))


def _matches_region(record: dict[str, Any], region_hint: str) -> bool:
    if not region_hint:
        return True
    prefix = record["region"]["full_prefix"]
    if not prefix:
        return True
    return prefix in region_hint or region_hint.startswith(prefix.split()[0])


def search_safety_bells(
    *,
    latitude: float,
    longitude: float,
    radius_m: int = 500,
    place_type: str | None = None,
    region_prefix: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    records = list(load_records())
    place_type = (place_type or "").strip()
    results: list[dict[str, Any]] = []

    for record in records:
        if not _matches_region(record, region_prefix):
            continue
        if place_type and place_type not in record["place_type"]:
            continue
        dist = haversine_m(latitude, longitude, record["lat"], record["lng"])
        if dist > radius_m:
            continue
        results.append({**record, "distance_m": int(dist)})

    results.sort(key=lambda r: r["distance_m"])
    return results[:limit]


def format_safety_bell_list(
    bells: list[dict[str, Any]],
    *,
    query: str | None = None,
    coords_hint: str | None = None,
) -> str:
    if not bells:
        hint = query or coords_hint or "해당 위치"
        return (
            f"**{hint}** 근처에서 안전비상벨을 찾지 못했습니다.\n"
            "- 반경을 넓히거나 다른 장소를 시도해 보세요.\n"
            "- 화장실 **벽 비상벨**은 `search_restroom`(user_type=elderly_safety)을 사용하세요.\n\n"
            f"{SAFETY_BELL_DISCLAIMER}"
        )

    lines = ["## 길·공원 안전비상벨 (범죄예방)"]
    if query:
        lines.append(f"- 검색: **{query}**")
    if coords_hint:
        lines.append(f"- 기준: {coords_hint}")
    lines.append("")

    for idx, bell in enumerate(bells, start=1):
        addr = bell["road_addr"] or bell["jibun_addr"]
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
    matches = [r for r in load_records() if _matches_region(r, region_prefix)]
    if not matches:
        return None
    lat = sum(r["lat"] for r in matches) / len(matches)
    lng = sum(r["lng"] for r in matches) / len(matches)
    return lat, lng


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

    if place_query and (lat is None or lng is None):
        try:
            coords = await geocode_place(place_query)
            if coords:
                lat, lng = coords
        except (ValueError, OSError, Exception):
            pass

    if lat is not None and lng is not None:
        try:
            region = await coord_to_region(lng, lat)
            if region and region.get("region_name"):
                region_prefix = region["region_name"]
        except (ValueError, OSError, Exception):
            pass

    if place_query and not region_prefix:
        sido, sigungu = parse_place_query(place_query)
        region_prefix = f"{sido} {sigungu}".strip()

    if place_query and not region_prefix:
        sido, sigungu = parse_place_query(place_query)
        region_prefix = f"{sido} {sigungu}".strip()

    region_fallback = False
    if (lat is None or lng is None) and region_prefix:
        centroid = _region_centroid(region_prefix)
        if centroid:
            lat, lng = centroid
            region_fallback = True

    if lat is None or lng is None:
        return (
            "좌표를 특정하지 못했습니다. `place_query`에 **구/군**까지 넣거나 "
            "`latitude`/`longitude`를 제공하세요.\n\n"
            f"{SAFETY_BELL_DISCLAIMER}"
        )

    search_radius = radius_m * 4 if region_fallback else radius_m
    bells = search_safety_bells(
        latitude=lat,
        longitude=lng,
        radius_m=search_radius,
        place_type=place_type,
        region_prefix=region_prefix,
        limit=limit,
    )
    coords_hint = f"{lat:.6f},{lng:.6f}"
    if region_fallback:
        coords_hint += f" (지역 중심 추정 · {region_prefix})"
    return format_safety_bell_list(bells, query=place_query, coords_hint=coords_hint)
