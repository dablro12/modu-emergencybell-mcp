#!/usr/bin/env python3
"""지하철 물품보관함·편의시설 CSV → subway_index.json."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUBWAY_DIR = ROOT / "data" / "subway"
OUT_FILE = SUBWAY_DIR / "subway_index.json"

STATION_SUFFIX = re.compile(r"역$")
LOCKER_NAME = re.compile(r"^(.+?)\d")


def normalize_station(name: str) -> str:
    text = (name or "").strip()
    text = STATION_SUFFIX.sub("", text)
    return text.replace(" ", "").lower()


def station_keys(name: str) -> set[str]:
    base = normalize_station(name)
    keys = {base}
    if name.strip():
        keys.add(name.strip())
    return keys


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="cp949", errors="replace") as f:
        return list(csv.DictReader(f))


def detect_city(path: Path, columns: set[str]) -> str:
    name = path.name
    if "부산" in name:
        return "부산"
    if "인천" in name:
        return "인천"
    if "역명" in columns and "소형(개수)" in columns:
        return "부산"
    if "역명" in columns and "시설현황" in columns:
        return "인천"
    return "서울"


def merge_station(stations: dict, name: str, *, city: str, line: str = "") -> dict:
    key = normalize_station(name)
    if key not in stations:
        stations[key] = {
            "names": sorted(station_keys(name)),
            "city": city,
            "lines": [],
            "lockers": [],
            "facilities": [],
            "lifts": [],
        }
    entry = stations[key]
    for alias in station_keys(name):
        if alias not in entry["names"]:
            entry["names"].append(alias)
    if line and line not in entry["lines"]:
        entry["lines"].append(line)
    return entry


def process_file(path: Path, stations: dict) -> None:
    rows = read_csv(path)
    if not rows:
        return
    columns = set(rows[0].keys())

    if "보관함명" in columns or ("역명" in columns and "시설현황" in columns) or (
        "역명" in columns and "소형(개수)" in columns
    ):
        city = detect_city(path, columns)
        for row in rows:
            if "역명" in row:
                station = row["역명"]
                line = row.get("호선", "")
            else:
                locker_name = row.get("보관함명", "")
                match = LOCKER_NAME.match(locker_name)
                station = match.group(1) if match else locker_name
                line = row.get("호선", "")
            entry = merge_station(stations, station, city=city, line=line)
            locker = {k: v for k, v in row.items() if v}
            locker["source_city"] = city
            entry["lockers"].append(locker)
        return

    if "휠체어리프트여부" in columns:
        for row in rows:
            station = row.get("역명", "")
            line = row.get("호선", "")
            entry = merge_station(stations, station, city="서울", line=line)
            entry["facilities"].append(
                {
                    "line": line,
                    "wheelchair_lift": row.get("휠체어리프트여부") == "Y",
                    "elevator": row.get("엘리베이터여부") == "Y",
                    "nursing_room": row.get("수유실여부") == "Y",
                    "meeting_place": row.get("만남의장소여부") == "Y",
                    "manual_locker": row.get("유인물품보관소여부") == "Y",
                }
            )
        return

    if "지하철역명" in columns and "노드 WKT" in columns:
        for row in rows:
            station = row.get("지하철역명", "")
            if not station:
                continue
            entry = merge_station(stations, station, city="서울")
            wkt = row.get("노드 WKT", "")
            coords = None
            if wkt.startswith("POINT(") and wkt.endswith(")"):
                parts = wkt[6:-1].split()
                if len(parts) == 2:
                    coords = {"longitude": float(parts[0]), "latitude": float(parts[1])}
            entry["lifts"].append(
                {
                    "sigungu": row.get("시군구명", ""),
                    "dong": row.get("읍면동명", ""),
                    "coords": coords,
                }
            )


def main() -> None:
    stations: dict[str, dict] = {}
    for path in sorted(SUBWAY_DIR.glob("*.csv")):
        process_file(path, stations)

    station_list = []
    for key, entry in sorted(stations.items()):
        entry["id"] = key
        entry["search_text"] = " ".join(
            filter(None, [key, *entry["names"], *entry["lines"], entry["city"]])
        ).lower()
        station_list.append(entry)

    payload = {
        "meta": {
            "source_dir": str(SUBWAY_DIR),
            "station_count": len(station_list),
            "locker_records": sum(len(s["lockers"]) for s in station_list),
        },
        "stations": station_list,
    }
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_FILE} — {payload['meta']['station_count']} stations")


if __name__ == "__main__":
    main()
