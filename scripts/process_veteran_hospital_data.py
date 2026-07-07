#!/usr/bin/env python3
"""국가보훈부 보훈의료 위탁병원 API → 로컬 검색용 JSON."""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "medical"
OUT_FILE = OUT_DIR / "veteran_hospital_index.json"

# 최신: 20260101
VETERAN_HOSPITAL_PATH = (
    "https://api.odcloud.kr/api/15081917/v1/uddi:ef6dfd60-fe3b-4986-8e22-b1bb3cb3063a"
)
PER_PAGE = 1000


def _service_keys() -> list[str]:
    keys: list[str] = []
    for name in (
        "ODCLOUD_SERVICE_KEY",
        "ODCLOUD_SERVICE_KEY_ENCODED",
        "DATA_GO_KR_SERVICE_KEY",
        "DATA_GO_KR_SERVICE_KEY_ENCODED",
    ):
        value = os.getenv(name, "").strip()
        if value and value not in keys:
            keys.append(value)
    return keys


def _parse_float(value: str) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def region_key(sido: str, sigungu: str) -> str:
    return f"{sido}|{sigungu}"


def normalize_record(row: dict[str, Any]) -> dict[str, Any] | None:
    lat = _parse_float(str(row.get("위도", "")))
    lng = _parse_float(str(row.get("경도", "")))
    name = (row.get("위탁병원명") or "").strip()
    if lat is None or lng is None or not name:
        return None
    return {
        "name": name,
        "lat": lat,
        "lng": lng,
        "sido": (row.get("광역시도명") or "").strip(),
        "sigungu": (row.get("시군구명") or "").strip(),
        "address": (row.get("상세주소") or "").strip(),
        "phone": (row.get("전화번호") or "").strip(),
        "type": (row.get("종별") or "").strip(),
        "beds": int(row.get("병상수") or 0),
        "departments": int(row.get("진료과수") or 0),
        "as_of": (row.get("기준일") or "").strip(),
        "seq": int(row.get("연번") or 0),
    }


async def fetch_all_rows(*, keys: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    total = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            payload = None
            last_error: Exception | None = None
            for key in keys:
                try:
                    response = await client.get(
                        VETERAN_HOSPITAL_PATH,
                        params={"page": page, "perPage": PER_PAGE},
                        headers={"Authorization": f"Infuser {key}"},
                    )
                    if response.status_code == 401:
                        response = await client.get(
                            VETERAN_HOSPITAL_PATH,
                            params={"page": page, "perPage": PER_PAGE, "serviceKey": key},
                        )
                    response.raise_for_status()
                    payload = response.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
            if payload is None:
                raise RuntimeError(f"보훈 위탁병원 API 호출 실패 (page={page}): {last_error}")

            if total is None:
                total = int(payload.get("totalCount") or 0)
                print(f"totalCount={total}")

            batch = payload.get("data") or []
            if not batch:
                break
            rows.extend(batch)
            print(f"page {page}: +{len(batch)} ({len(rows)}/{total})")
            if len(rows) >= total:
                break
            page += 1

    return rows


def build_index(raw_rows: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    region_index: dict[str, list[int]] = defaultdict(list)
    sido_index: dict[str, list[int]] = defaultdict(list)

    for row in raw_rows:
        record = normalize_record(row)
        if not record:
            continue
        idx = len(records)
        records.append(record)
        if record["sido"]:
            sido_index[record["sido"]].append(idx)
        if record["sido"] and record["sigungu"]:
            region_index[region_key(record["sido"], record["sigungu"])].append(idx)

    return {
        "meta": {
            "source": "국가보훈부_보훈의료 위탁병원 현황",
            "as_of": records[0]["as_of"] if records else "20260101",
            "record_count": len(records),
        },
        "records": records,
        "region_index": dict(region_index),
        "sido_index": dict(sido_index),
    }


def write_mini_fixture() -> None:
    samples = [
        {
            "name": "강남세브란스병원",
            "lat": 37.492989,
            "lng": 127.046729,
            "sido": "서울특별시",
            "sigungu": "강남구",
            "address": "테스트주소 1",
            "phone": "02-000-0000",
            "type": "종합병원",
            "beds": 100,
            "departments": 10,
            "as_of": "2026-01-01",
            "seq": 1,
        },
        {
            "name": "서울테스트요양병원",
            "lat": 37.5665,
            "lng": 126.978,
            "sido": "서울특별시",
            "sigungu": "중구",
            "address": "테스트주소 2",
            "phone": "02-111-1111",
            "type": "요양병원",
            "beds": 20,
            "departments": 2,
            "as_of": "2026-01-01",
            "seq": 2,
        },
    ]
    region_index = {
        "서울특별시|강남구": [0],
        "서울특별시|중구": [1],
    }
    payload = {
        "meta": {"source": "fixture", "as_of": "20260101", "record_count": len(samples)},
        "records": samples,
        "region_index": region_index,
        "sido_index": {"서울특별시": [0, 1]},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote fixture {OUT_FILE}")


async def main_async() -> None:
    keys = _service_keys()
    if not keys:
        print("No ODCLOUD/DATA_GO_KR key — writing mini fixture", file=sys.stderr)
        write_mini_fixture()
        return

    import asyncio

    raw_rows = await fetch_all_rows(keys=keys)
    index = build_index(raw_rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_FILE} ({index['meta']['record_count']} records)")


def main() -> None:
    import asyncio

    asyncio.run(main_async())


if __name__ == "__main__":
    main()
