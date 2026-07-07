#!/usr/bin/env python3
"""행정안전부 안전비상벨 CSV → 구조화 JSON (로컬 검색용)."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "emergencybell"
OUT_DIR = DATA_DIR


def find_source_csv() -> Path:
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV in {DATA_DIR}")
    return files[0]


def _parse_float(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _region_prefix(road_addr: str) -> str:
    parts = road_addr.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    if parts:
        return parts[0]
    return ""


def parse_row(row: dict[str, str], idx: int) -> dict | None:
    lat = _parse_float(row.get("WGS84위도", ""))
    lng = _parse_float(row.get("WGS84경도", ""))
    if lat is None or lng is None:
        return None

    road = (row.get("소재지도로명주소") or "").strip()
    jibun = (row.get("소재지지번주소") or "").strip()
    mgmt_id = (row.get("안전비상벨관리번호") or row.get("관리번호") or str(idx)).strip()
    place_type = (row.get("설치장소유형") or "").strip()
    location = (row.get("설치위치") or "").strip()
    purpose = (row.get("설치목적") or "").strip()

    search_bits = [road, jibun, place_type, location, purpose, mgmt_id]
    search_text = " ".join(b for b in search_bits if b).lower()

    return {
        "id": mgmt_id,
        "install_purpose": purpose,
        "place_type": place_type,
        "location": location,
        "road_addr": road,
        "jibun_addr": jibun,
        "lat": lat,
        "lng": lng,
        "link_mode": (row.get("연계방식") or "").strip(),
        "police_link": (row.get("경찰연계유무") or "").strip(),
        "security_link": (row.get("경비업체연계유무") or "").strip(),
        "office_link": (row.get("관리사무소연계유무") or "").strip(),
        "extra_features": (row.get("부가기능") or "").strip(),
        "install_year": (row.get("안전비상벨설치연도") or "").strip(),
        "mgmt_org": (row.get("관리기관명") or "").strip(),
        "mgmt_tel": (row.get("관리기관전화번호") or "").strip(),
        "region": {"full_prefix": _region_prefix(road)},
        "search_text": search_text,
    }


def build_indexes(records: list[dict]) -> dict:
    region_index: dict[str, list[str]] = defaultdict(list)
    place_type_index: dict[str, list[str]] = defaultdict(list)

    for record in records:
        rid = record["id"]
        prefix = record["region"]["full_prefix"]
        if prefix:
            region_index[prefix].append(rid)
        ptype = record["place_type"]
        if ptype:
            place_type_index[ptype].append(rid)

    return {
        "region_index": dict(region_index),
        "place_type_index": dict(place_type_index),
    }


def main() -> None:
    source = find_source_csv()
    records: list[dict] = []

    for encoding in ("utf-8-sig", "cp949", "utf-8"):
        try:
            with source.open(encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader, start=1):
                    parsed = parse_row(row, idx)
                    if parsed:
                        records.append(parsed)
            break
        except UnicodeDecodeError:
            records.clear()
            continue

    indexes = build_indexes(records)
    place_counts = Counter(r["place_type"] for r in records if r["place_type"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "safety_bell_records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "safety_bell_region_index.json").write_text(
        json.dumps(indexes["region_index"], ensure_ascii=False),
        encoding="utf-8",
    )
    (OUT_DIR / "safety_bell_meta.json").write_text(
        json.dumps(
            {
                "source_csv": source.name,
                "record_count": len(records),
                "place_type_counts": dict(place_counts.most_common(30)),
                "note": "Crime-prevention outdoor bells — NOT restroom wall buttons or 119 dispatch.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {len(records)} records from {source.name}")


if __name__ == "__main__":
    main()
