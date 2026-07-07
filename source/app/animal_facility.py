"""동물병원·동물약국 로컬 근접 검색 (행정안전부 CSV 색인)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from helpers import haversine_m
from map_preview import append_overview_map, enrich_result_lines
from place_resolver import resolve_place_context

AnimalKind = Literal["hospital", "pharmacy"]

from runtime_paths import data_path

DATA_DIR = data_path("animal")
INDEX_FILES: dict[AnimalKind, Path] = {
    "hospital": DATA_DIR / "animal_hospital_index.json",
    "pharmacy": DATA_DIR / "animal_pharmacy_index.json",
}

RADIUS_STEPS = (500, 800, 1200, 2000, 3000)
DISCLAIMER = (
    "_출처: 행정안전부 동물병원·동물약국 인허가 데이터(로컬 색인). "
    "야간·응급 진료·재고는 **전화 확인**._"
)


@lru_cache(maxsize=2)
def load_index(kind: AnimalKind) -> dict[str, Any]:
    path = INDEX_FILES[kind]
    if not path.exists():
        return {"meta": {}, "records": [], "grid": {}, "city_index": {}}
    with path.open(encoding="utf-8") as handle:
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


def search_animal_facilities(
    *,
    kind: AnimalKind,
    latitude: float,
    longitude: float,
    radius_m: int = 800,
    city_hint: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    index = load_index(kind)
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
                candidate_indices.update(indices[:8000])
                break

    results: list[dict[str, Any]] = []
    for idx in candidate_indices:
        if idx >= len(records):
            continue
        record = records[idx]
        if not _matches_city(record, city_hint):
            continue
        dist = haversine_m(latitude, longitude, record["lat"], record["lng"])
        if dist > radius_m:
            continue
        results.append({**record, "distance_m": int(dist)})

    results.sort(key=lambda item: item["distance_m"])
    return results[:limit]


def _format_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 9:
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:]}"
    return phone or ""


def format_animal_list(
    rows: list[dict[str, Any]],
    *,
    kind: AnimalKind,
    query: str,
    coords_hint: str | None = None,
    radius_used: int | None = None,
) -> str:
    label = "동물병원" if kind == "hospital" else "동물약국"
    if not rows:
        return (
            f"**{query}** 근처 {label}을 찾지 못했습니다.\n"
            f"- `find_outdoor_service_tool`의 `service`를 `{'vet_hospital' if kind == 'hospital' else 'animal_pharmacy'}`로 호출하세요.\n"
            "- **역·동·구** 이름을 더 구체적으로 알려주세요.\n\n"
            f"{DISCLAIMER}"
        )

    lines = [f"## {label} — {query}"]
    if kind == "hospital":
        lines.append("⚠️ 야간·응급 진료 여부는 **병원에 전화 확인**하세요.")
    if coords_hint:
        lines.append(f"- 기준 위치: {coords_hint}")
    if radius_used:
        lines.append(f"- 검색 반경: **{radius_used}m**")
    lines.append("")

    append_overview_map(lines, rows, title=f"{query} 근처 {label}")

    for idx, row in enumerate(rows, start=1):
        addr = row.get("road_addr") or row.get("lot_addr") or ""
        lines.append(f"### {idx}. {row['name']} · 약 {row['distance_m']}m")
        lines.append(f"- **주소**: {addr}")
        phone = _format_phone(row.get("phone") or "")
        if phone:
            lines.append(f"- **전화**: {phone}")
        enrich_result_lines(lines, name=row["name"], item=row, rank=idx)
        lines.append("")

    lines.append(DISCLAIMER)
    return "\n".join(lines).strip()


async def find_animal_facilities_near(
    *,
    place_query: str,
    kind: AnimalKind,
    radius_m: int = 800,
    limit: int = 5,
) -> str:
    ctx = await resolve_place_context(place_query)
    if ctx.latitude is None or ctx.longitude is None:
        label = "동물병원" if kind == "hospital" else "동물약국"
        return (
            f"**{place_query}** 위치를 특정하지 못했습니다.\n"
            f"- **동·역·구** 이름으로 다시 말씀해 주세요 (예: `홍대입구`, `부산 서면`).\n\n"
            f"{DISCLAIMER}"
        )

    city_hint = _city_hint(ctx.sido, ctx.sigungu, ctx.expanded_query)
    rows: list[dict[str, Any]] = []
    radius_used = radius_m
    for step in RADIUS_STEPS:
        if step < radius_m:
            continue
        radius_used = max(step, radius_m)
        rows = search_animal_facilities(
            kind=kind,
            latitude=ctx.latitude,
            longitude=ctx.longitude,
            radius_m=radius_used,
            city_hint=city_hint,
            limit=limit,
        )
        if rows:
            break

    coords_hint = f"{ctx.latitude:.6f},{ctx.longitude:.6f}"
    if ctx.warning:
        coords_hint += f" ({ctx.warning})"

    return format_animal_list(
        rows,
        kind=kind,
        query=ctx.expanded_query or place_query,
        coords_hint=coords_hint,
        radius_used=radius_used if rows else None,
    )
