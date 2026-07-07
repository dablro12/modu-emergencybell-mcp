"""국가보훈부 보훈의료 위탁병원 검색."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from helpers import haversine_m
from place_resolver import resolve_place_context
from region_parse import region_full_prefix

DATA_FILE = Path(__file__).resolve().parent / "data" / "medical" / "veteran_hospital_index.json"

VETERAN_DISCLAIMER = (
    "⚠️ **보훈의료 위탁병원** 안내입니다. "
    "**국가유공자·보훈대상자** 등 진료 자격·급여 적용은 **국가보훈부·병원**에 확인하세요. "
    "일반 진료는 `find_open_clinic`을 사용하세요.\n\n"
    "_출처: 국가보훈부 보훈의료 위탁병원 현황(공공데이터)_"
)


@lru_cache(maxsize=1)
def load_index() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {"meta": {}, "records": [], "region_index": {}, "sido_index": {}}
    with DATA_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _region_key(sido: str, sigungu: str) -> str:
    return f"{sido}|{sigungu}"


def _candidate_indices(*, sido: str, sigungu: str) -> list[int]:
    index = load_index()
    region_index = index.get("region_index") or {}
    sido_index = index.get("sido_index") or {}
    records = index.get("records") or []

    if sido and sigungu:
        exact = region_index.get(_region_key(sido, sigungu))
        if exact:
            return list(exact)

    if sido:
        matched = list(sido_index.get(sido, []))
        if matched:
            return matched

    return list(range(len(records)))


def _matches_type(record: dict[str, Any], hospital_type: str | None) -> bool:
    if not hospital_type:
        return True
    needle = hospital_type.strip()
    return needle in (record.get("type") or "")


def search_veteran_hospitals(
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    sido: str = "",
    sigungu: str = "",
    hospital_type: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    index = load_index()
    records = index.get("records") or []
    if not records:
        return []

    indices = _candidate_indices(sido=sido, sigungu=sigungu)
    results: list[dict[str, Any]] = []
    for idx in indices:
        if idx >= len(records):
            continue
        record = records[idx]
        if not _matches_type(record, hospital_type):
            continue
        item = dict(record)
        if latitude is not None and longitude is not None:
            item["distance_m"] = int(
                haversine_m(latitude, longitude, record["lat"], record["lng"])
            )
        results.append(item)

    if latitude is not None and longitude is not None:
        results.sort(key=lambda row: row.get("distance_m", 10**9))
    else:
        results.sort(key=lambda row: row.get("name", ""))

    return results[:limit]


def format_veteran_hospital_list(
    hospitals: list[dict[str, Any]],
    *,
    region_label: str,
    coords_hint: str | None = None,
) -> str:
    if not hospitals:
        return (
            f"**{region_label}**에서 보훈의료 위탁병원을 찾지 못했습니다.\n"
            "- **시·군·구** 단위로 다시 말씀해 주세요 (예: `서울 강남구`, `부산 해운대구`).\n"
            "- 일반 병·의원은 `find_open_clinic`을 사용하세요.\n\n"
            f"{VETERAN_DISCLAIMER}"
        )

    lines = [f"## 보훈의료 위탁병원 — {region_label}"]
    if coords_hint:
        lines.append(f"- 기준: {coords_hint}")
    lines.append("")

    for idx, hospital in enumerate(hospitals, start=1):
        dist_txt = (
            f" · 약 {hospital['distance_m']}m"
            if hospital.get("distance_m") is not None
            else ""
        )
        lines.append(f"### {idx}. {hospital['name']}{dist_txt}")
        if hospital.get("type"):
            lines.append(f"- **종별**: {hospital['type']}")
        addr_parts = [
            part
            for part in (
                hospital.get("sido"),
                hospital.get("sigungu"),
                hospital.get("address"),
            )
            if part
        ]
        if addr_parts:
            lines.append(f"- **주소**: {' '.join(addr_parts)}")
        if hospital.get("phone"):
            lines.append(f"- **전화**: {hospital['phone']}")
        if hospital.get("beds") is not None:
            lines.append(f"- **병상**: {hospital['beds']} · **진료과**: {hospital.get('departments', 0)}")
        lines.append("")

    lines.append(VETERAN_DISCLAIMER)
    return "\n".join(lines)


async def find_veteran_hospitals_near(
    *,
    place_query: str,
    hospital_type: str | None = None,
    limit: int = 5,
) -> str:
    ctx = await resolve_place_context(place_query)
    region_label = region_full_prefix(ctx.sido, ctx.sigungu) or place_query
    hospitals = search_veteran_hospitals(
        latitude=ctx.latitude,
        longitude=ctx.longitude,
        sido=ctx.sido,
        sigungu=ctx.sigungu,
        hospital_type=hospital_type,
        limit=limit,
    )

    coords_hint = None
    if ctx.latitude is not None and ctx.longitude is not None:
        coords_hint = f"{ctx.latitude:.6f},{ctx.longitude:.6f}"
    elif place_query:
        coords_hint = place_query
    if ctx.warning and coords_hint:
        coords_hint += f" ({ctx.warning})"

    if not hospitals and ctx.sido and not ctx.sigungu:
        hospitals = search_veteran_hospitals(
            latitude=ctx.latitude,
            longitude=ctx.longitude,
            sido=ctx.sido,
            sigungu="",
            hospital_type=hospital_type,
            limit=limit,
        )
        region_label = ctx.sido

    return format_veteran_hospital_list(
        hospitals,
        region_label=region_label,
        coords_hint=coords_hint,
    )
