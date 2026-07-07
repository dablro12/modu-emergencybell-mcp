#!/usr/bin/env python3
"""경찰청 범죄 발생 지역별 통계 CSV → 로컬 검색용 JSON."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "emergencybell"
OUT_FILE = DATA_DIR / "crime_stats_index.json"

SHORT_SIDO_TO_FULL: dict[str, str] = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "제주": "제주특별자치도",
}

SAFETY_SUBCATEGORIES = (
    "살인기수",
    "살인미수등",
    "강도",
    "강간",
    "유사강간",
    "강제추행",
    "기타 강간/강제추행등",
    "절도범죄",
    "폭행",
    "상해",
    "협박",
)

SAFETY_MAJORS = ("강력범죄", "절도범죄", "폭력범죄")


def find_source_csv() -> Path:
    matches = sorted(DATA_DIR.glob("*20241231*.csv"))
    if not matches:
        matches = sorted(DATA_DIR.glob("*범죄*.csv"))
    if not matches:
        raise FileNotFoundError(f"No crime stats CSV in {DATA_DIR}")
    return matches[0]


def parse_region_column(column: str) -> tuple[str, str] | None:
    text = (column or "").strip()
    if not text or text.startswith("외국 "):
        return None
    if text == "세종시":
        return "세종특별자치시", "세종시"
    if text.startswith("경기도 "):
        return "경기도", text.removeprefix("경기도 ").strip()
    if text.startswith("강원특별자치도 "):
        return "강원특별자치도", text.removeprefix("강원특별자치도 ").strip()
    if text.startswith("충청북도 "):
        return "충청북도", text.removeprefix("충청북도 ").strip()
    if text.startswith("충청남도 "):
        return "충청남도", text.removeprefix("충청남도 ").strip()
    if text.startswith("전북특별자치도 "):
        return "전북특별자치도", text.removeprefix("전북특별자치도 ").strip()
    if text.startswith("전라남도 "):
        return "전라남도", text.removeprefix("전라남도 ").strip()
    if text.startswith("경상북도 "):
        return "경상북도", text.removeprefix("경상북도 ").strip()
    if text.startswith("경상남도 "):
        return "경상남도", text.removeprefix("경상남도 ").strip()
    if text.startswith("제주 "):
        return "제주특별자치도", text.removeprefix("제주 ").strip()

    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return None
    short_sido, sigungu = parts
    full_sido = SHORT_SIDO_TO_FULL.get(short_sido, short_sido)
    return full_sido, sigungu


def region_key(sido: str, sigungu: str) -> str:
    return f"{sido}|{sigungu}"


def build_index(rows: list[dict[str, str]], region_columns: list[str]) -> dict:
    parsed_columns: dict[str, tuple[str, str]] = {}
    for column in region_columns:
        parsed = parse_region_column(column)
        if parsed:
            parsed_columns[column] = parsed

    regions: dict[str, dict] = {}
    for column, (sido, sigungu) in parsed_columns.items():
        key = region_key(sido, sigungu)
        by_major: dict[str, int] = defaultdict(int)
        by_sub: dict[str, int] = defaultdict(int)
        total = 0
        for row in rows:
            count = int((row.get(column) or "0").strip() or 0)
            total += count
            major = (row.get("범죄대분류") or "").strip()
            sub = (row.get("범죄중분류") or "").strip()
            if major:
                by_major[major] += count
            if sub:
                by_sub[sub] += count

        safety_total = sum(by_major.get(major, 0) for major in SAFETY_MAJORS)
        safety_detail = {name: by_sub.get(name, 0) for name in SAFETY_SUBCATEGORIES if by_sub.get(name, 0)}

        regions[key] = {
            "column": column,
            "sido": sido,
            "sigungu": sigungu,
            "total": total,
            "by_major": dict(sorted(by_major.items(), key=lambda item: -item[1])),
            "safety_total": safety_total,
            "safety_detail": safety_detail,
        }

    for sido in {entry["sido"] for entry in regions.values()}:
        sido_entries = [entry for entry in regions.values() if entry["sido"] == sido]
        for metric in ("total", "safety_total"):
            ranked = sorted(sido_entries, key=lambda item: item[metric], reverse=True)
            for rank, entry in enumerate(ranked, start=1):
                regions[region_key(entry["sido"], entry["sigungu"])][f"sido_rank_{metric}"] = rank
                regions[region_key(entry["sido"], entry["sigungu"])][f"sido_count"] = len(sido_entries)

    lookup: dict[str, str] = {}
    for key, entry in regions.items():
        lookup[entry["column"]] = key
        lookup[region_key(entry["sido"], entry["sigungu"])] = key
        lookup[f"{entry['sido']} {entry['sigungu']}"] = key

    return {
        "meta": {
            "source": "경찰청 범죄 발생 지역별 통계",
            "as_of": "20241231",
            "region_count": len(regions),
            "note": "발생 건수(검거·인지 포함). 실시간 위험도가 아닙니다.",
        },
        "regions": regions,
        "lookup": lookup,
    }


def main() -> None:
    source = find_source_csv()
    with source.open(encoding="cp949", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        region_columns = [column for column in reader.fieldnames or [] if column not in ("범죄대분류", "범죄중분류")]

    index = build_index(rows, region_columns)
    OUT_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_FILE} ({index['meta']['region_count']} regions)")


if __name__ == "__main__":
    main()
