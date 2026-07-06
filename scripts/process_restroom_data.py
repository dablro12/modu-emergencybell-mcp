#!/usr/bin/env python3
"""행정안전부 공중화장실 CSV → 구조화 JSON (공중화장실_##)."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from restroom_parser import parse_record

DATA_DIR = ROOT / "data" / "toilet_data"


def find_source_csv() -> Path:
    files = list(DATA_DIR.glob("*.csv"))
    if not files:
        files = list((ROOT / "data").glob("**/공중화장실*.csv"))
    if not files:
        raise FileNotFoundError(f"No restroom CSV in {DATA_DIR}")
    return files[0]


def build_indexes(records: list[dict]) -> dict:
    user_type_index: dict[str, list[str]] = defaultdict(list)
    opening_index: dict[str, list[str]] = defaultdict(list)
    region_index: dict[str, list[str]] = defaultdict(list)

    for record in records:
        rid = record["id"]
        for tag in record["user_types"]["tags"]:
            user_type_index[tag].append(rid)
        opening_index[record["opening"]["type"]].append(rid)
        key = record["region"]["full_prefix"]
        if key:
            region_index[key].append(rid)

    return {
        "user_type_index": dict(user_type_index),
        "opening_type_index": dict(opening_index),
        "region_index": dict(region_index),
    }


def build_summaries(records: list[dict]) -> dict:
    user_type_counts = Counter()
    facility_counts = Counter()
    opening_counts = Counter()

    for record in records:
        for tag in record["user_types"]["tags"]:
            user_type_counts[tag] += 1
        opening_counts[record["opening"]["type"]] += 1
        facilities = record["facilities"]
        if facilities["emergency_bell"]:
            facility_counts["emergency_bell"] += 1
        if facilities["diaper_station"]:
            facility_counts["diaper_station"] += 1
        if facilities["cctv_entrance"]:
            facility_counts["cctv_entrance"] += 1
        if record["user_types"]["wheelchair"]:
            facility_counts["wheelchair_accessible"] += 1
        if record["user_types"]["child"]:
            facility_counts["child_toilet"] += 1

    return {
        "user_type_counts": dict(user_type_counts),
        "opening_type_counts": dict(opening_counts),
        "facility_counts": dict(facility_counts),
        "region_top20": Counter(r["region"]["full_prefix"] for r in records if r["region"]["full_prefix"]).most_common(20),
    }


def main() -> None:
    source = find_source_csv()
    records: list[dict] = []

    with source.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("관리번호"):
                continue
            records.append(parse_record(row))

    indexes = build_indexes(records)
    summaries = build_summaries(records)

    meta = {
        "source_file": source.name,
        "source_encoding": "utf-8",
        "source_agency": "행정안전부 공중화장실 표준데이터",
        "total_records": len(records),
        "data_standard_dates": Counter(r["data_date"] for r in records if r["data_date"]).most_common(5),
        "user_type_definitions": {
            "general": "일반 이용 가능 (개방 중인 공중화장실)",
            "wheelchair": "휠체어/장애인용 대변기·소변기 1개 이상",
            "child": "어린이용 대변기·소변기 1개 이상",
            "infant_care": "기저귀 교환대 있음",
            "elderly_safety": "비상벨 설치 (고령자·안전 취약)",
        },
        "opening_type_definitions": {
            "always": "상시 개방",
            "scheduled": "정시 개방 (개방시간상세 참고)",
            "irregular": "불규칙 개방",
            "closed": "미개방 유형",
            "unknown": "개방시간 정보 없음",
        },
        "note": "latitude/longitude는 원본 CSV에 없음. 반경 검색 시 Kakao Local API로 사용자 위치를 geocode 후 region_index로 1차 필터.",
    }

    outputs = {
        "공중화장실_01_전체레코드.json": records,
        "공중화장실_02_메타정보.json": meta,
        "공중화장실_03_이용자유형_색인.json": indexes["user_type_index"],
        "공중화장실_04_개방시간유형_색인.json": indexes["opening_type_index"],
        "공중화장실_05_지역_색인.json": indexes["region_index"],
        "공중화장실_06_통계요약.json": summaries,
    }

    for filename, payload in outputs.items():
        path = DATA_DIR / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Wrote {path} ({path.stat().st_size:,} bytes)")

    print(f"\nDone. {len(records):,} records processed from {source.name}")


if __name__ == "__main__":
    main()
