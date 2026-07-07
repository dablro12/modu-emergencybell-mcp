"""전국 도시광역철도 역사 ATM (로컬 CSV 인덱스)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from helpers import haversine_m
from kakao_local import geocode_place, search_keyword
from landmarks import LANDMARK_COORDS, lookup_landmark_coords
from region_parse import normalize_place_query

from runtime_paths import data_path

DATA_FILE = data_path("subway", "subway_atm_index.json")
STATION_SUFFIX = re.compile(r"역$")
STATION_IN_QUERY = re.compile(r"([가-힣][가-힣0-9]*역)")
NEARBY_RADIUS_M = 3500


def normalize_station(name: str) -> str:
    text = STATION_SUFFIX.sub("", (name or "").strip())
    return text.replace(" ", "").lower()


@lru_cache(maxsize=1)
def load_index() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {"stations": [], "meta": {}}
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _station_candidates(place_query: str, station_query: str | None = None) -> list[str]:
    candidates: list[str] = []

    def add(value: str | None) -> None:
        text = (value or "").strip()
        if not text or text in candidates:
            return
        candidates.append(text)

    add(station_query)
    add(place_query)
    for token in STATION_IN_QUERY.findall(place_query or ""):
        add(token)

    normalized = normalize_place_query(place_query or "")
    add(normalized)
    if normalized and not normalized.endswith("역"):
        add(f"{normalized}역")
        base = STATION_SUFFIX.sub("", normalized)
        if base:
            add(f"{base}역")

    query_lower = (place_query or "").lower()
    for landmark_name in LANDMARK_COORDS:
        if landmark_name in (place_query or "") or landmark_name.lower() in query_lower:
            add(landmark_name)
            if not landmark_name.endswith("역"):
                add(f"{landmark_name}역")

    return candidates


def _match_stations(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    key = normalize_station(query)
    if not key:
        return []
    stations = load_index().get("stations") or []
    exact: list[dict[str, Any]] = []
    partial: list[tuple[int, dict[str, Any]]] = []

    for station in stations:
        sid = station.get("id", "")
        names = station.get("names") or []
        if sid == key:
            exact.append(station)
            continue
        for name in names:
            if normalize_station(name) == key:
                exact.append(station)
                break
        else:
            for cand in [sid, *names]:
                norm = normalize_station(cand)
                if not norm:
                    continue
                if key in norm or norm in key:
                    partial.append((len(norm), station))
                    break

    if exact:
        return exact[:limit]

    partial.sort(key=lambda item: item[0], reverse=True)
    return [station for _, station in partial[:limit]]


def _resolve_direct_match(
    place_query: str,
    station_query: str | None,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    for candidate in _station_candidates(place_query, station_query):
        matches = _match_stations(candidate, limit=limit)
        if matches:
            return matches
    return []


def _nearest_stations_with_coords(
    lat: float,
    lng: float,
    *,
    max_radius_m: int = NEARBY_RADIUS_M,
    limit: int = 3,
) -> list[tuple[dict[str, Any], int]]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for station in load_index().get("stations") or []:
        try:
            st_lat = float(station.get("latitude"))
            st_lng = float(station.get("longitude"))
        except (TypeError, ValueError):
            continue
        dist = int(haversine_m(lat, lng, st_lat, st_lng))
        if dist <= max_radius_m:
            ranked.append((dist, station))
    ranked.sort(key=lambda item: item[0])
    return [(station, dist) for dist, station in ranked[:limit]]


async def _match_station_near_coords(
    lat: float,
    lng: float,
    place_hint: str,
    *,
    max_radius_m: int = NEARBY_RADIUS_M,
) -> tuple[dict[str, Any], int] | None:
    nearest = _nearest_stations_with_coords(
        lat, lng, max_radius_m=max_radius_m, limit=1
    )
    if nearest:
        return nearest[0]

    if not place_hint:
        place_hint = "역"
    search_terms = []
    for term in (f"{place_hint}역", place_hint, "지하철역"):
        if term and term not in search_terms:
            search_terms.append(term)

    for term in search_terms:
        docs = await search_keyword(term, x=lng, y=lat, radius=max_radius_m, size=15)
        for doc in docs:
            place_name = doc.get("place_name") or doc.get("address_name") or ""
            matches = _match_stations(place_name, limit=1)
            if not matches:
                continue
            try:
                doc_lat = float(doc.get("y"))
                doc_lng = float(doc.get("x"))
                dist = int(haversine_m(lat, lng, doc_lat, doc_lng))
            except (TypeError, ValueError):
                dist = 0
            if dist <= max_radius_m:
                return matches[0], dist
    return None


def _format_station_block(
    station: dict[str, Any],
    *,
    start_index: int,
    limit: int,
) -> tuple[list[str], int]:
    lines: list[str] = []
    shown = start_index
    display = station["names"][0] if station.get("names") else station.get("id", "")
    operators = ", ".join(station.get("operators") or []) or "정보없음"
    line_names = ", ".join(station.get("lines") or []) or "정보없음"
    lines.append(f"### {display}")
    lines.append(f"- **운영기관**: {operators}")
    lines.append(f"- **노선**: {line_names}")
    lines.append("")

    for atm in station.get("atms") or []:
        if shown >= limit:
            break
        shown += 1
        bank = (atm.get("bank") or "ATM").strip()
        loc = (atm.get("location") or "").strip()
        hours = (atm.get("hours") or "").strip()
        phone = (atm.get("phone") or "").strip()
        floor = atm.get("floor", "")
        ground = (atm.get("ground") or "").strip()
        line = (atm.get("line") or "").strip()

        title = bank
        if line:
            title += f" ({line})"
        lines.append(f"#### {shown}. {title}")
        if loc:
            lines.append(f"- **위치**: {loc}")
        if ground or floor:
            parts = [p for p in (ground, f"{floor}층" if floor else "") if p]
            lines.append(f"- **층**: {' · '.join(parts)}")
        if hours:
            lines.append(f"- **이용시간**: {hours}")
        if phone:
            lines.append(f"- **연락처**: {phone}")
        note = (atm.get("note") or "").strip()
        if note:
            lines.append(f"- **참고**: {note}")
        lines.append("")

    return lines, shown


async def search_subway_atms(
    place_query: str,
    *,
    station_query: str | None = None,
    limit: int = 5,
) -> str:
    input_label = (station_query or place_query).strip()
    matches = _resolve_direct_match(place_query, station_query, limit=3)
    fallback_note = ""

    if not matches:
        coords = await geocode_place(place_query)
        if not coords:
            landmark = lookup_landmark_coords(place_query)
            if landmark:
                coords = landmark

        if coords:
            lat, lng = coords
            hint = STATION_SUFFIX.sub("", normalize_place_query(place_query))
            nearby = await _match_station_near_coords(lat, lng, hint)
            if nearby:
                station, dist = nearby
                matches = [station]
                display = station["names"][0] if station.get("names") else station.get("id", "")
                fallback_note = (
                    f"입력하신 **{input_label}** 에서 역명을 바로 찾지 못해 "
                    f"가까운 **{display}** 기준으로 안내합니다 (약 {dist}m)."
                )
        if not matches:
            return (
                f"**{input_label}** 주변에 ATM 데이터가 있는 역을 찾지 못했습니다.\n"
                "- 역 이름을 넣어 주세요. 예: `강남역`, `서울역`, `부산 서면역`\n"
                "- 전국 도시광역철도·경전철 **역사 안** ATM만 조회됩니다."
            )

    lines = [f"## 역사 ATM — {input_label}", ""]
    if fallback_note:
        lines.append(f"_{fallback_note}_")
        lines.append("")

    shown = 0
    for station in matches:
        block, shown = _format_station_block(station, start_index=shown, limit=limit)
        lines.extend(block)
        if shown >= limit:
            break

    lines.append("_출처: 국가철도공단 전국 도시광역철도 역사 ATM 현황 (공공데이터)_")
    return "\n".join(lines).strip()
