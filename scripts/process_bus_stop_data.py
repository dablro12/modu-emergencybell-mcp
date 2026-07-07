#!/usr/bin/env python3
"""국토교통부 전국 버스정류장 API → 그리드 색인 JSON (로컬 근접 검색)."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "bus"
OUT_FILE = OUT_DIR / "bus_stop_index.json"

# 최신: 20251031
BUS_STOP_PATH = (
    "https://api.odcloud.kr/api/15067528/v1/uddi:f74b9799-9db1-4754-a5d0-b66e2ae705f3"
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


def grid_key(lat: float, lng: float) -> str:
    return f"{int(lat * 100)}:{int(lng * 100)}"


def normalize_record(row: dict[str, Any]) -> dict[str, Any] | None:
    lat = _parse_float(str(row.get("위도", "")))
    lng = _parse_float(str(row.get("경도", "")))
    if lat is None or lng is None:
        return None
    name = (row.get("정류장명") or "").strip()
    stop_id = (row.get("정류장번호") or "").strip()
    if not name or not stop_id:
        return None
    mobile = row.get("모바일단축번호")
    return {
        "id": stop_id,
        "name": name,
        "lat": lat,
        "lng": lng,
        "city": (row.get("도시명") or "").strip(),
        "mgmt_city": (row.get("관리도시명") or "").strip(),
        "mobile": int(mobile) if mobile not in (None, "") else None,
        "collected_at": (row.get("정보수집일") or "").strip(),
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
                        BUS_STOP_PATH,
                        params={"page": page, "perPage": PER_PAGE},
                        headers={"Authorization": f"Infuser {key}"},
                    )
                    if response.status_code == 401:
                        response = await client.get(
                            BUS_STOP_PATH,
                            params={"page": page, "perPage": PER_PAGE, "serviceKey": key},
                        )
                    response.raise_for_status()
                    payload = response.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
            if payload is None:
                raise RuntimeError(f"버스정류장 API 호출 실패 (page={page}): {last_error}")

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
            time.sleep(0.05)

    return rows


def build_index(raw_rows: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    grid: dict[str, list[int]] = defaultdict(list)
    city_index: dict[str, list[int]] = defaultdict(list)

    for row in raw_rows:
        record = normalize_record(row)
        if not record:
            continue
        idx = len(records)
        records.append(record)
        grid[grid_key(record["lat"], record["lng"])].append(idx)
        city_key = record["city"] or record["mgmt_city"]
        if city_key:
            city_index[city_key].append(idx)

    return {
        "meta": {
            "source": "국토교통부_전국 버스정류장 위치정보",
            "as_of": "20251031",
            "record_count": len(records),
            "grid_cells": len(grid),
        },
        "records": records,
        "grid": {key: value for key, value in grid.items()},
        "city_index": {key: value for key, value in city_index.items()},
    }


def write_mini_fixture() -> None:
    """테스트용 소규모 샘플 (API 키 없을 때)."""
    samples = [
        {
            "id": "TEST001",
            "name": "강남역.GC",
            "lat": 37.497942,
            "lng": 127.027621,
            "city": "서울특별시",
            "mgmt_city": "서울BIS",
            "mobile": 100001,
            "collected_at": "2025-10-31",
        },
        {
            "id": "TEST002",
            "name": "강남역.신분당",
            "lat": 37.4975,
            "lng": 127.0285,
            "city": "서울특별시",
            "mgmt_city": "서울BIS",
            "mobile": 100002,
            "collected_at": "2025-10-31",
        },
        {
            "id": "TEST003",
            "name": "창신동",
            "lat": 37.5752,
            "lng": 127.0128,
            "city": "서울특별시",
            "mgmt_city": "서울BIS",
            "mobile": 100003,
            "collected_at": "2025-10-31",
        },
    ]
    grid: dict[str, list[int]] = defaultdict(list)
    for idx, record in enumerate(samples):
        grid[grid_key(record["lat"], record["lng"])].append(idx)
    payload = {
        "meta": {
            "source": "fixture",
            "as_of": "20251031",
            "record_count": len(samples),
            "grid_cells": len(grid),
        },
        "records": samples,
        "grid": dict(grid),
        "city_index": {"서울특별시": list(range(len(samples)))},
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
    OUT_FILE.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_FILE} ({index['meta']['record_count']} records)")


def main() -> None:
    import asyncio

    asyncio.run(main_async())


if __name__ == "__main__":
    main()
