#!/usr/bin/env python3
"""동물병원·동물약국 CSV → 그리드 색인 JSON (근접 검색용)."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from coords_transform import tm5179_to_wgs84

ANIMAL_DIR = ROOT / "data" / "animal"
OUT_HOSPITAL = ANIMAL_DIR / "animal_hospital_index.json"
OUT_PHARMACY = ANIMAL_DIR / "animal_pharmacy_index.json"

OPEN_STATUS = frozenset({"영업/정상", "영업", "정상"})
OPEN_CODES = frozenset({"01"})


def grid_key(lat: float, lng: float) -> str:
    return f"{int(lat * 100)}:{int(lng * 100)}"


def _parse_float(value: str) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _is_open(row: dict[str, str]) -> bool:
    status = (row.get("영업상태명") or "").strip()
    code = (row.get("영업상태코드") or "").strip()
    if status in OPEN_STATUS or "정상" in status:
        return True
    return code in OPEN_CODES


def _city_from_address(addr: str) -> str:
    parts = (addr or "").split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return parts[0] if parts else ""


def _normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return digits


def normalize_record(row: dict[str, str], *, kind: str) -> dict[str, Any] | None:
    if not _is_open(row):
        return None
    name = (row.get("사업장명") or "").strip()
    road = (row.get("도로명주소") or "").strip()
    lot = (row.get("지번주소") or "").strip()
    if not name or not (road or lot):
        return None

    x = _parse_float(row.get("좌표정보(X)", ""))
    y = _parse_float(row.get("좌표정보(Y)", ""))
    if x is None or y is None:
        return None
    coords = tm5179_to_wgs84(x, y)
    if coords is None:
        return None
    lat, lng = coords

    mgmt = (row.get("관리번호") or "").strip()
    return {
        "id": f"{kind}:{mgmt}" if mgmt else f"{kind}:{name}:{road}",
        "name": name,
        "road_addr": road,
        "lot_addr": lot,
        "phone": _normalize_phone(row.get("전화번호", "")),
        "lat": lat,
        "lng": lng,
        "city": _city_from_address(road or lot),
        "status": (row.get("영업상태명") or "").strip(),
        "kind": kind,
    }


def _find_csv(kind: str) -> Path:
    candidates = sorted(ANIMAL_DIR.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No CSV files in {ANIMAL_DIR}")
    if kind == "hospital":
        for path in candidates:
            if "병원" in path.name or "병원" in path.name:
                return path
    if kind == "pharmacy":
        for path in candidates:
            if "약국" in path.name or "약국" in path.name:
                return path
    raise FileNotFoundError(f"No CSV for {kind} in {ANIMAL_DIR}")


def build_index(*, kind: str) -> dict[str, Any]:
    csv_path = _find_csv(kind)
    records: list[dict[str, Any]] = []
    grid: dict[str, list[int]] = defaultdict(list)
    city_index: dict[str, list[int]] = defaultdict(list)

    with csv_path.open(encoding="cp949") as handle:
        for row in csv.DictReader(handle):
            record = normalize_record(row, kind=kind)
            if record is None:
                continue
            idx = len(records)
            records.append(record)
            grid[grid_key(record["lat"], record["lng"])].append(idx)
            city = record.get("city") or ""
            if city:
                city_index[city].append(idx)

    return {
        "meta": {
            "source": csv_path.name,
            "kind": kind,
            "record_count": len(records),
        },
        "records": records,
        "grid": dict(grid),
        "city_index": dict(city_index),
    }


def main() -> None:
    try:
        from pyproj import Transformer  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "pyproj required: pip install pyproj (or run in Docker build step)"
        ) from exc

    ANIMAL_DIR.mkdir(parents=True, exist_ok=True)
    hospital = build_index(kind="hospital")
    pharmacy = build_index(kind="pharmacy")

    with OUT_HOSPITAL.open("w", encoding="utf-8") as handle:
        json.dump(hospital, handle, ensure_ascii=False)
    with OUT_PHARMACY.open("w", encoding="utf-8") as handle:
        json.dump(pharmacy, handle, ensure_ascii=False)

    print(
        f"Wrote {OUT_HOSPITAL.name} ({hospital['meta']['record_count']} records), "
        f"{OUT_PHARMACY.name} ({pharmacy['meta']['record_count']} records)"
    )


if __name__ == "__main__":
    main()
