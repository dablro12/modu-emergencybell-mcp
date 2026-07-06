"""공중화장실 데이터 로드·검색·포맷."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from kakao_local import coord_to_region, geocode_place
from region_parse import parse_place_query
from restroom_parser import is_open_now

DATA_DIR = Path(__file__).resolve().parent / "data" / "toilet_data"
RECORDS_FILE = DATA_DIR / "공중화장실_01_전체레코드.json"
META_FILE = DATA_DIR / "공중화장실_02_메타정보.json"

USER_TYPE_ALIASES = {
    "wheelchair": "wheelchair",
    "disabled": "wheelchair",
    "장애인": "wheelchair",
    "child": "child",
    "어린이": "child",
    "유아": "infant_care",
    "infant": "infant_care",
    "infant_care": "infant_care",
    "기저귀": "infant_care",
    "elderly": "elderly_safety",
    "elderly_safety": "elderly_safety",
    "general": "general",
}


@lru_cache(maxsize=1)
def load_records() -> tuple[dict, ...]:
    if not RECORDS_FILE.exists():
        return tuple()
    with RECORDS_FILE.open(encoding="utf-8") as f:
        return tuple(json.load(f))


@lru_cache(maxsize=1)
def load_meta() -> dict[str, Any]:
    if not META_FILE.exists():
        return {}
    with META_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


async def geocode(query: str) -> tuple[float, float] | None:
    return await geocode_place(query)


def _normalize_user_type(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower()
    return USER_TYPE_ALIASES.get(key, key)


def _matches_user_type(record: dict[str, Any], user_type: str | None) -> bool:
    if not user_type or user_type == "general":
        return True
    return user_type in record["user_types"]["tags"]


def _matches_open_now(record: dict[str, Any], open_now: bool) -> bool:
    if not open_now:
        return True
    status = is_open_now(record["opening"])
    return status is not False


def _region_hint_from_coords(lat: float, lng: float, region_info: dict[str, str] | None) -> str:
    if region_info and region_info.get("region_name"):
        return region_info["region_name"]
    return ""


def _matches_region(record: dict[str, Any], region_hint: str) -> bool:
    if not region_hint:
        return True
    record_prefix = record["region"]["full_prefix"]
    if not record_prefix:
        return True
    return record_prefix in region_hint or region_hint.startswith(record_prefix.split()[0])


def search_records(
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    query_tokens: list[str] | None = None,
    region_prefix: str = "",
    radius_m: int = 500,
    user_type: str | None = None,
    open_now: bool = False,
    limit: int = 10,
) -> list[dict[str, Any]]:
    records = list(load_records())
    user_type = _normalize_user_type(user_type)
    tokens = [t.lower() for t in (query_tokens or []) if t]

    filtered: list[dict[str, Any]] = []
    for record in records:
        if not _matches_region(record, region_prefix):
            continue
        if tokens and not all(tok in record["search_text"] for tok in tokens):
            continue
        if not _matches_user_type(record, user_type):
            continue
        if not _matches_open_now(record, open_now):
            continue
        filtered.append(dict(record))

    if latitude is not None and longitude is not None:
        for record in filtered:
            if record.get("latitude") and record.get("longitude"):
                record["distance_m"] = int(
                    haversine_m(latitude, longitude, record["latitude"], record["longitude"])
                )
            else:
                record["distance_m"] = None
        with_coords = [r for r in filtered if r.get("distance_m") is not None]
        without_coords = [r for r in filtered if r.get("distance_m") is None]
        with_coords.sort(key=lambda r: r["distance_m"])
        if with_coords:
            filtered = [r for r in with_coords if r["distance_m"] <= radius_m] or with_coords
        else:
            filtered = without_coords

    return filtered[:limit]


async def fetch_restrooms(
    latitude: float,
    longitude: float,
    radius: int = 500,
    *,
    user_type: str | None = None,
    open_now: bool = False,
    limit: int = 10,
) -> list[dict[str, Any]]:
    region_info = None
    region_prefix = ""
    try:
        region_info = await coord_to_region(longitude, latitude)
        region_prefix = _region_hint_from_coords(latitude, longitude, region_info)
    except (ValueError, OSError):
        pass

    return search_records(
        latitude=latitude,
        longitude=longitude,
        region_prefix=region_prefix,
        radius_m=radius,
        user_type=user_type,
        open_now=open_now,
        limit=limit,
    )


async def search_restrooms_by_query(
    query: str,
    radius: int = 500,
    *,
    user_type: str | None = None,
    open_now: bool = False,
    limit: int = 10,
) -> tuple[list[dict[str, Any]], str | None]:
    coords = await geocode(query)
    if coords is None:
        tokens = query.replace(",", " ").split()
        sido, sigungu = parse_place_query(query)
        region_prefix = f"{sido} {sigungu}".strip()
        results = search_records(
            query_tokens=tokens if not region_prefix else None,
            region_prefix=region_prefix,
            user_type=user_type,
            open_now=open_now,
            limit=limit,
        )
        return results, None

    lat, lng = coords
    results = await fetch_restrooms(
        lat, lng, radius, user_type=user_type, open_now=open_now, limit=limit
    )
    return results, f"{lat:.6f},{lng:.6f}"


def get_record_by_id(record_id: str) -> dict[str, Any] | None:
    for record in load_records():
        if record["id"] == record_id:
            return dict(record)
    return None


def format_restroom_list(
    restrooms: list[dict[str, Any]],
    *,
    query: str | None = None,
    coords_hint: str | None = None,
) -> str:
    if not restrooms:
        hint = f"'{query}'" if query else "해당 조건"
        return f"{hint}에 맞는 공중화장실을 찾지 못했습니다."

    lines = []
    if query:
        lines.append(f"## 검색: {query}")
    if coords_hint:
        lines.append(f"- 기준 좌표: {coords_hint}")
    lines.append("")

    for idx, r in enumerate(restrooms, start=1):
        opening = r["opening"]
        ut = r["user_types"]
        fac = r["facilities"]
        tags = ", ".join(
            label
            for key, label in [
                ("wheelchair", "장애인"),
                ("child", "어린이"),
                ("infant_care", "기저귀교환"),
                ("elderly_safety", "비상벨"),
            ]
            if ut.get(key)
        )
        dist = r.get("distance_m")
        dist_text = f" · 약 {dist}m" if dist is not None else ""
        open_label = opening["type_raw"] or "정보없음"
        if opening.get("detail"):
            open_label += f" ({opening['detail'][:40]})"

        lines.append(f"### {idx}. {r['name']}{dist_text}")
        lines.append(f"- **주소**: {r['road_address'] or r['jibun_address']}")
        lines.append(f"- **개방**: {open_label}")
        if tags:
            lines.append(f"- **이용자 유형**: {tags}")
        if fac["emergency_bell"]:
            lines.append(f"- **비상벨**: {fac['emergency_bell_location'] or '설치'}")
        if fac["diaper_station"]:
            lines.append(f"- **기저귀 교환대**: {fac['diaper_station_location'] or '있음'}")
        if r.get("phone"):
            lines.append(f"- **전화**: {r['phone']}")
        lines.append(f"- **ID**: `{r['id']}`")
        lines.append("")

    meta = load_meta()
    if meta.get("source_agency"):
        lines.append(f"_출처: {meta['source_agency']}_")

    return "\n".join(lines).strip()


def format_dataset_info() -> str:
    meta = load_meta()
    if not meta:
        return "데이터가 아직 처리되지 않았습니다. `python scripts/process_restroom_data.py`를 실행하세요."

    summaries_path = DATA_DIR / "공중화장실_06_통계요약.json"
    summaries = {}
    if summaries_path.exists():
        with summaries_path.open(encoding="utf-8") as f:
            summaries = json.load(f)

    lines = [
        "## modu-emergencybell(모두의비상벨) Dataset Info",
        f"- **총 화장실**: {meta.get('total_records', 0):,}곳",
        f"- **원본 파일**: {meta.get('source_file', '')}",
        f"- **출처**: {meta.get('source_agency', '')}",
        "",
        "### 이용자 유형별",
    ]
    for tag, count in summaries.get("user_type_counts", {}).items():
        desc = meta.get("user_type_definitions", {}).get(tag, "")
        lines.append(f"- `{tag}`: {count:,}곳 — {desc}")

    lines.append("\n### 개방 시간 유형")
    for tag, count in summaries.get("opening_type_counts", {}).items():
        desc = meta.get("opening_type_definitions", {}).get(tag, "")
        lines.append(f"- `{tag}`: {count:,}곳 — {desc}")

    return "\n".join(lines)
