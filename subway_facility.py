"""지하철 물품보관함·편의시설 (로컬 CSV 인덱스)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).resolve().parent / "data" / "subway" / "subway_index.json"
STATION_SUFFIX = re.compile(r"역$")


def normalize_station(name: str) -> str:
    text = STATION_SUFFIX.sub("", (name or "").strip())
    return text.replace(" ", "").lower()


@lru_cache(maxsize=1)
def load_index() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {"stations": [], "meta": {}}
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _match_station(query: str) -> dict[str, Any] | None:
    key = normalize_station(query)
    stations = load_index().get("stations") or []
    for station in stations:
        if station.get("id") == key:
            return station
        if key and key in station.get("search_text", ""):
            return station
        for name in station.get("names", []):
            if normalize_station(name) == key:
                return station
    return None


def find_subway_facility(
    station_query: str,
    *,
    facility_type: str = "all",
    limit: int = 5,
) -> str:
    station = _match_station(station_query)
    if not station:
        return (
            f"'{station_query}' 역 정보를 찾지 못했습니다.\n"
            "- 서울·부산·인천 지하철 데이터만 포함됩니다.\n"
            "- 예: `강남역`, `서울역`, `부산 서면`"
        )

    show_lockers = facility_type in ("all", "locker", "lockers")
    show_access = facility_type in ("all", "accessibility", "accessible", "wheelchair")

    display_name = station["names"][0] if station.get("names") else station_query
    lines = [
        f"## 지하철 시설 — {display_name}",
        f"- **도시**: {station.get('city', '')} · **노선**: {', '.join(station.get('lines') or []) or '정보없음'}",
        "",
    ]

    if show_lockers:
        lockers = station.get("lockers") or []
        lines.append(f"### 물품보관함 ({len(lockers)}건)")
        if not lockers:
            lines.append("- 등록된 보관함 정보 없음")
        for locker in lockers[:limit]:
            if "보관함명" in locker:
                title = locker["보관함명"]
                detail = locker.get("상세위치", "")
            else:
                title = station.get("names", [display_name])[0]
                detail = locker.get("상세위치", "")
                if locker.get("시설현황"):
                    detail = f"{detail} · {locker['시설현황']}".strip(" ·")
            fee = locker.get("이용요금") or locker.get("운영사") or ""
            lines.append(f"- **{title}**: {detail}")
            if fee:
                lines.append(f"  - {fee}")
        lines.append("")

    if show_access:
        facilities = station.get("facilities") or []
        lifts = station.get("lifts") or []
        lines.append("### 접근성·편의시설")
        if facilities:
            for fac in facilities[:limit]:
                tags = []
                if fac.get("wheelchair_lift"):
                    tags.append("휠체어리프트")
                if fac.get("elevator"):
                    tags.append("엘리베이터")
                if fac.get("nursing_room"):
                    tags.append("수유실")
                if fac.get("manual_locker"):
                    tags.append("유인물품보관소")
                line = fac.get("line") or ""
                lines.append(f"- {line}: {', '.join(tags) if tags else '기본정보만'}")
        elif lifts:
            lines.append(f"- 출입구 리프트 {len(lifts)}곳 (서울시 데이터)")
            for lift in lifts[:limit]:
                loc = " · ".join(filter(None, [lift.get("sigungu"), lift.get("dong")]))
                lines.append(f"  - {loc}")
        else:
            lines.append("- 접근성 상세 정보 없음")

    lines.append("")
    lines.append("_출처: 서울·부산·인천교통공사 공공데이터_")
    return "\n".join(lines).strip()
