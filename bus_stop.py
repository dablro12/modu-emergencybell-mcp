"""전국 버스정류장 근접 검색 (국토교통부 로컬 색인)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from helpers import haversine_m
from place_resolver import resolve_place_context

DATA_FILE = Path(__file__).resolve().parent / "data" / "bus" / "bus_stop_index.json"

RADIUS_STEPS = (300, 500, 800, 1200)
BUS_STOP_DISCLAIMER = (
    "_출처: 국토교통부 전국 버스정류장 위치정보(공공데이터). "
    "노선·도착 정보는 포함되지 않습니다._"
)


@lru_cache(maxsize=1)
def load_index() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {"meta": {}, "records": [], "grid": {}, "city_index": {}}
    with DATA_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def grid_key(lat: float, lng: float) -> str:
    return f"{int(lat * 100)}:{int(lng * 100)}"


def neighbor_grid_keys(lat: float, lng: float) -> list[str]:
    base_lat = int(lat * 100)
    base_lng = int(lng * 100)
    return [
        f"{base_lat + dlat}:{base_lng + dlng}"
        for dlat in (-1, 0, 1)
        for dlng in (-1, 0, 1)
    ]


def _city_hint(sido: str, sigungu: str, expanded_query: str) -> str:
    parts = [part for part in (sido, sigungu, expanded_query) if part]
    return " ".join(parts)


def _matches_city(record: dict[str, Any], city_hint: str) -> bool:
    if not city_hint:
        return True
    city = record.get("city") or ""
    if not city:
        return True
    hint_tokens = city_hint.replace(",", " ").split()
    return any(token in city for token in hint_tokens if len(token) >= 2)


def _matches_name(record: dict[str, Any], stop_name: str | None) -> bool:
    if not stop_name:
        return True
    needle = stop_name.strip().lower()
    hay = record.get("name", "").lower()
    return needle in hay or hay in needle


def search_bus_stops(
    *,
    latitude: float,
    longitude: float,
    radius_m: int = 500,
    stop_name: str | None = None,
    city_hint: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    index = load_index()
    records = index.get("records") or []
    grid = index.get("grid") or {}
    if not records:
        return []

    candidate_indices: set[int] = set()
    for key in neighbor_grid_keys(latitude, longitude):
        candidate_indices.update(grid.get(key, []))

    if not candidate_indices and city_hint:
        city_index = index.get("city_index") or {}
        for city, indices in city_index.items():
            if any(token in city for token in city_hint.split() if len(token) >= 2):
                candidate_indices.update(indices[:5000])
                break

    results: list[dict[str, Any]] = []
    for idx in candidate_indices:
        if idx >= len(records):
            continue
        record = records[idx]
        if not _matches_city(record, city_hint):
            continue
        if not _matches_name(record, stop_name):
            continue
        dist = haversine_m(latitude, longitude, record["lat"], record["lng"])
        if dist > radius_m:
            continue
        results.append({**record, "distance_m": int(dist)})

    results.sort(key=lambda item: item["distance_m"])
    return results[:limit]


def format_bus_stop_list(
    stops: list[dict[str, Any]],
    *,
    query: str | None = None,
    coords_hint: str | None = None,
    radius_used: int | None = None,
) -> str:
    if not stops:
        hint = query or "해당 장소"
        return (
            f"**{hint}** 근처에서 버스정류장을 찾지 못했습니다.\n"
            "- **역·동·구 이름**을 더 구체적으로 알려주세요 (예: `강남역`, `종로구 창신동`).\n"
            "- 정류장 **이름**을 알고 있으면 `stop_name`으로 검색하세요.\n\n"
            f"{BUS_STOP_DISCLAIMER}"
        )

    lines = ["## 버스정류장"]
    if query:
        lines.append(f"- 검색: **{query}**")
    if coords_hint:
        lines.append(f"- 기준 위치: {coords_hint}")
    if radius_used:
        lines.append(f"- 검색 반경: **{radius_used}m**")
    lines.append("")

    for idx, stop in enumerate(stops, start=1):
        lines.append(f"### {idx}. {stop['name']} · 약 {stop['distance_m']}m")
        lines.append(f"- **정류장번호**: {stop['id']}")
        if stop.get("mobile"):
            lines.append(f"- **모바일단축번호**: {stop['mobile']}")
        if stop.get("city"):
            lines.append(f"- **도시**: {stop['city']}")
        lines.append(f"- **좌표**: {stop['lat']:.6f}, {stop['lng']:.6f}")
        lines.append("")

    lines.append(BUS_STOP_DISCLAIMER)
    return "\n".join(lines)


async def find_bus_stops_near(
    *,
    place_query: str,
    stop_name: str | None = None,
    radius_m: int = 500,
    limit: int = 5,
) -> str:
    ctx = await resolve_place_context(place_query)
    if ctx.latitude is None or ctx.longitude is None:
        return (
            f"**{place_query}** 위치를 특정하지 못했습니다.\n"
            "- **동·역·구** 이름으로 다시 말씀해 주세요 (예: `강남역`, `부산 서면`).\n\n"
            f"{BUS_STOP_DISCLAIMER}"
        )

    city_hint = _city_hint(ctx.sido, ctx.sigungu, ctx.expanded_query)
    stops: list[dict[str, Any]] = []
    radius_used = radius_m
    for step in RADIUS_STEPS:
        if step < radius_m:
            continue
        radius_used = max(step, radius_m)
        stops = search_bus_stops(
            latitude=ctx.latitude,
            longitude=ctx.longitude,
            radius_m=radius_used,
            stop_name=stop_name,
            city_hint=city_hint,
            limit=limit,
        )
        if stops:
            break

    coords_hint = f"{ctx.latitude:.6f},{ctx.longitude:.6f}"
    if ctx.warning:
        coords_hint += f" ({ctx.warning})"

    return format_bus_stop_list(
        stops,
        query=stop_name or ctx.expanded_query or place_query,
        coords_hint=coords_hint,
        radius_used=radius_used if stops else None,
    )
