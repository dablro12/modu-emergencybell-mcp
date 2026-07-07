"""전국 도시광역철도 역사 ATM (로컬 CSV 인덱스)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).resolve().parent / "data" / "subway" / "subway_atm_index.json"
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
            norm = normalize_station(name)
            if norm == key:
                exact.append(station)
                break
        else:
            candidates = [sid] + names
            for cand in candidates:
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


def search_subway_atms(
    station_query: str,
    *,
    limit: int = 5,
) -> str:
    matches = _match_stations(station_query, limit=3)
    if not matches:
        return (
            f"'{station_query}' 역의 ATM 정보를 찾지 못했습니다.\n"
            "- 전국 도시광역철도·경전철 역사 ATM 데이터입니다.\n"
            "- 예: `강남역`, `서울역`, `부산 서면역`, `대구 반월당`"
        )

    lines = [f"## 역사 ATM — {station_query}", ""]
    shown = 0
    for station in matches:
        display = station["names"][0] if station.get("names") else station_query
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

            title = f"{bank}"
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

        if shown >= limit:
            break

    lines.append("_출처: 국가철도공단 전국 도시광역철도 역사 ATM 현황 (공공데이터)_")
    return "\n".join(lines).strip()
