#!/usr/bin/env python3
"""전국 도시광역철도 역사 ATM xlsx/csv → subway_atm_index.json."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUBWAY_DIR = ROOT / "data" / "subway"
XLSX_GLOB = "*ATM*.xlsx"
CSV_NAME = "전국_도시광역철도_역사_ATM_현황_20251230.csv"
OUT_FILE = SUBWAY_DIR / "subway_atm_index.json"

STATION_SUFFIX = re.compile(r"역$")

COLUMNS = [
    "철도운영기관명",
    "운영기관코드",
    "운영노선명",
    "노선코드",
    "역명",
    "역코드",
    "관리번호",
    "지상지하구분",
    "지상지하구분코드",
    "역층",
    "상세위치",
    "금융기관명",
    "이용가능시간",
    "연락처",
    "데이터기준일자",
    "참고사항",
]


def normalize_station(name: str) -> str:
    text = STATION_SUFFIX.sub("", (name or "").strip())
    return text.replace(" ", "").lower()


def _cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text in ("#VALUE!", "#N/A"):
        return ""
    return text


def xlsx_to_csv(xlsx_path: Path, csv_path: Path) -> int:
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb["ATM"]
    count = 0
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for idx, row in enumerate(ws.iter_rows(values_only=True)):
            if idx < 2:
                continue
            if not row or not row[4]:
                continue
            writer.writerow([_cell(v) for v in row[:16]])
            count += 1
    wb.close()
    return count


def read_atm_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def merge_station(stations: dict[str, dict], row: dict[str, str]) -> dict:
    raw_name = row["역명"]
    key = normalize_station(raw_name)
    if key not in stations:
        stations[key] = {
            "names": [],
            "operators": [],
            "lines": [],
            "atms": [],
        }
    entry = stations[key]
    for alias in {raw_name, STATION_SUFFIX.sub("", raw_name.strip())}:
        if alias and alias not in entry["names"]:
            entry["names"].append(alias)
    operator = row.get("철도운영기관명", "")
    line = row.get("운영노선명", "")
    if operator and operator not in entry["operators"]:
        entry["operators"].append(operator)
    if line and line not in entry["lines"]:
        entry["lines"].append(line)
    entry["atms"].append(
        {
            "operator": operator,
            "line": line,
            "line_code": row.get("노선코드", ""),
            "bank": row.get("금융기관명", ""),
            "location": row.get("상세위치", ""),
            "floor": row.get("역층", ""),
            "ground": row.get("지상지하구분", ""),
            "hours": row.get("이용가능시간", ""),
            "phone": row.get("연락처", ""),
            "note": row.get("참고사항", ""),
            "as_of": row.get("데이터기준일자", ""),
        }
    )
    return entry


def _collect_station_coords() -> dict[str, list[tuple[float, float]]]:
    coords: dict[str, list[tuple[float, float]]] = defaultdict(list)
    subway_index = SUBWAY_DIR / "subway_index.json"
    if subway_index.exists():
        data = json.loads(subway_index.read_text(encoding="utf-8"))
        for station in data.get("stations") or []:
            for lift in station.get("lifts") or []:
                point = lift.get("coords") or {}
                if point.get("latitude") and point.get("longitude"):
                    coords[normalize_station(station.get("id", ""))].append(
                        (float(point["latitude"]), float(point["longitude"]))
                    )

    for path in SUBWAY_DIR.glob("*리프트*"):
        with path.open(encoding="cp949", errors="replace") as f:
            for row in csv.DictReader(f):
                name = row.get("지하철역명") or row.get("역명") or ""
                wkt = row.get("노드 WKT", "")
                if wkt.startswith("POINT(") and wkt.endswith(")"):
                    parts = wkt[6:-1].split()
                    if len(parts) == 2:
                        lng, lat = float(parts[0]), float(parts[1])
                        coords[normalize_station(name)].append((lat, lng))

    try:
        from landmarks import LANDMARK_COORDS

        for name, (lat, lng) in LANDMARK_COORDS.items():
            if name.endswith("역"):
                coords[normalize_station(name)].append((lat, lng))
    except ImportError:
        pass

    return coords


def _attach_coordinates(stations: list[dict]) -> None:
    coord_map = _collect_station_coords()
    attached = 0
    for station in stations:
        points = coord_map.get(station["id"], [])
        if not points:
            continue
        station["latitude"] = round(sum(p[0] for p in points) / len(points), 6)
        station["longitude"] = round(sum(p[1] for p in points) / len(points), 6)
        attached += 1
    return None


def build_index(rows: list[dict[str, str]]) -> dict:
    stations: dict[str, dict] = {}
    for row in rows:
        if not row.get("역명"):
            continue
        merge_station(stations, row)

    station_list = []
    for key, entry in sorted(stations.items()):
        entry["id"] = key
        entry["search_text"] = " ".join(
            filter(None, [key, *entry["names"], *entry["lines"], *entry["operators"]])
        ).lower()
        station_list.append(entry)

    _attach_coordinates(station_list)

    return {
        "meta": {
            "source_csv": CSV_NAME,
            "station_count": len(station_list),
            "atm_count": sum(len(s["atms"]) for s in station_list),
            "stations_with_coords": sum(
                1 for s in station_list if s.get("latitude") is not None
            ),
        },
        "stations": station_list,
    }


def main() -> None:
    csv_path = SUBWAY_DIR / CSV_NAME
    xlsx_files = sorted(SUBWAY_DIR.glob(XLSX_GLOB))
    if xlsx_files and not csv_path.exists():
        count = xlsx_to_csv(xlsx_files[0], csv_path)
        print(f"Wrote {csv_path} — {count} rows")
    elif xlsx_files and csv_path.exists():
        count = xlsx_to_csv(xlsx_files[0], csv_path)
        print(f"Updated {csv_path} — {count} rows")
    elif not csv_path.exists():
        raise SystemExit(f"Missing {csv_path} and no xlsx found in {SUBWAY_DIR}")

    rows = read_atm_csv(csv_path)
    payload = build_index(rows)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote {OUT_FILE} — {payload['meta']['station_count']} stations, "
        f"{payload['meta']['atm_count']} ATMs"
    )


if __name__ == "__main__":
    main()
