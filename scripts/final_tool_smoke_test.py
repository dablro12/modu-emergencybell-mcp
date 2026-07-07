#!/usr/bin/env python3
"""12개 MCP Tool 상황별 스모크 테스트."""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import modu_emergencybell as mcp  # noqa: E402

SCENARIOS: list[tuple[str, str, dict, str]] = [
    (
        "get_emergency_hotlines",
        "119랑 1339 차이? 아이가 열이 나요",
        {"situation_description": "119랑 1339 차이? 아이가 열이 나요", "language": "ko"},
        "119",
    ),
    (
        "find_nearest_restroom",
        "강남역 근처 화장실",
        {"place_query": "강남역", "user_type": "general", "limit": 3},
        "화장실",
    ),
    (
        "search_restroom",
        "명동 휠체어 화장실",
        {"query": "명동", "user_type": "wheelchair", "limit": 3},
        "화장실",
    ),
    (
        "find_open_clinic",
        "일요일 밤 서울 마포구 소아과",
        {"place_query": "서울 마포구", "specialty": "pediatric", "treatment_day": "일요일"},
        "병원",
    ),
    (
        "find_emergency_room",
        "서울 강남구 응급실",
        {"place_query": "서울 강남구", "limit": 3},
        "응급",
    ),
    (
        "find_open_pharmacy",
        "서울 종로구 오늘 약국",
        {"place_query": "서울 종로구", "treatment_day": "월요일", "limit": 3},
        "약국",
    ),
    (
        "find_safety_bell",
        "서울 이태원 안전비상벨",
        {"place_query": "서울 이태원", "radius_m": 500, "limit": 3},
        "비상벨",
    ),
    (
        "get_phrase_card",
        "외국인 병원 문장",
        {"scenario": "hospital_visit", "language": "en"},
        "hospital",
    ),
    (
        "find_subway_facility_tool",
        "강남역 물품보관함",
        {"station_query": "강남역", "facility_type": "all", "limit": 3},
        "물품보관함",
    ),
    (
        "find_safe_place",
        "종로구 아동안전지킴이집",
        {"place_query": "서울 종로구", "category": "child_safety_house", "limit": 3},
        "안전",
    ),
    (
        "find_accessible_facility_tool",
        "서울역 휠체어 접근",
        {"place_query": "서울역", "include_subway": True, "limit": 3},
        "접근성",
    ),
    (
        "find_outdoor_service_tool",
        "강남역 ATM",
        {"place_query": "강남역", "service": "atm", "limit": 3},
        "ATM",
    ),
    (
        "find_outdoor_service_tool",
        "서울 종로 무료 와이파이",
        {"place_query": "서울 종로구", "service": "wifi", "limit": 3},
        "WiFi",
    ),
    (
        "find_outdoor_service_tool",
        "강남 동물병원",
        {"place_query": "서울 강남구", "service": "vet_hospital", "limit": 3},
        "동물",
    ),
]


async def run_one(name: str, label: str, kwargs: dict, expect: str) -> dict:
    fn = getattr(mcp, name)
    try:
        result = await fn(**kwargs)
        ok = expect.lower() in result.lower() or "찾지 못했습니다" not in result[:80]
        return {
            "tool": name,
            "label": label,
            "ok": ok,
            "preview": result[:200].replace("\n", " "),
            "error": None,
        }
    except Exception as exc:
        return {
            "tool": name,
            "label": label,
            "ok": False,
            "preview": "",
            "error": f"{exc.__class__.__name__}: {exc}",
        }


async def main() -> int:
    print("=== modu-emergencybell Final Tool Smoke Test ===\n")
    results = []
    for name, label, kwargs, expect in SCENARIOS:
        row = await run_one(name, label, kwargs, expect)
        results.append(row)
        status = "PASS" if row["ok"] else "FAIL"
        print(f"[{status}] {name} — {label}")
        if row["error"]:
            print(f"       ERROR: {row['error']}")
        else:
            print(f"       {row['preview'][:160]}...")
        print()

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    print(f"Result: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
