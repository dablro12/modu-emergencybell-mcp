#!/usr/bin/env python3
"""MCP Tool·Prompt 상황별 스모크 테스트."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import modu_emergencybell as mcp  # noqa: E402

SCENARIOS: list[tuple[str, str, dict, str]] = [
    (
        "classify_emergency_intent",
        "명동성당 급똥 라우팅",
        {"user_request": "명동성당쪽인데 급똥이야 화장실 알려줘"},
        "find_nearest_restroom",
    ),
    (
        "emergency_guide_tool",
        "집에서 가스 냄새",
        {"user_request": "집에서 가스 냄새가 날 때", "place_query": "서울"},
        "1544",
    ),
    (
        "get_emergency_hotlines",
        "119랑 1339 차이",
        {"situation_description": "119랑 1339 차이? 아이가 열이 나요", "language": "ko"},
        "119",
    ),
    (
        "find_nearest_restroom",
        "user_request만 (명동성당)",
        {
            "user_request": "명동성당쪽인데 급똥이야 화장실",
            "limit": 3,
        },
        "화장실",
    ),
    (
        "find_nearest_restroom",
        "강남역 화장실",
        {"place_query": "강남역", "user_type": "general", "limit": 3},
        "화장실",
    ),
    (
        "search_restroom",
        "명동 휠체어",
        {"query": "명동", "user_type": "wheelchair", "limit": 3},
        "화장실",
    ),
    (
        "find_open_clinic",
        "일요일 밤 마포 소아과",
        {"place_query": "서울 마포구", "specialty": "pediatric", "treatment_day": "일요일"},
        "병원",
    ),
    (
        "find_emergency_room",
        "강남 응급실",
        {"place_query": "서울 강남구", "limit": 3},
        "응급",
    ),
    (
        "find_open_pharmacy",
        "창신동 약국",
        {"place_query": "창신동", "user_request": "종로구 창신동 약국", "limit": 3},
        "약국",
    ),
    (
        "find_safety_bell",
        "이태원 안전비상벨",
        {"place_query": "서울 이태원", "user_request": "이태원 안전비상벨", "radius_m": 500, "limit": 3},
        "비상벨",
    ),
    (
        "get_phrase_card",
        "약 알레르기 영어",
        {"scenario": "pharmacy_allergy_check", "language": "en"},
        "allergic",
    ),
    (
        "find_open_clinic",
        "연산9동 내과",
        {"place_query": "연산9동", "specialty": "internal_medicine", "limit": 3},
        "의원",
    ),
    (
        "find_subway_facility_tool",
        "서울역 엘리베이터",
        {"station_query": "서울역", "facility_type": "elevator", "limit": 3},
        "접근",
    ),
    (
        "find_safe_place",
        "종로 안전지킴이집",
        {"place_query": "서울 종로구", "category": "child_safety_house", "limit": 3},
        "안전",
    ),
    (
        "find_accessible_facility_tool",
        "명동성당 접근성",
        {"place_query": "명동성당", "user_request": "명동성당 휠체어", "include_subway": True, "limit": 3},
        "접근",
    ),
    (
        "find_outdoor_service_tool",
        "홍대 WiFi",
        {"place_query": "홍대", "service": "wifi", "user_request": "홍대 와이파이", "limit": 3},
        "WiFi",
    ),
    (
        "find_outdoor_service_tool",
        "강남역 버스정류장",
        {"place_query": "강남역", "service": "bus_stop", "limit": 3},
        "버스",
    ),
    (
        "find_outdoor_service_tool",
        "동물병원",
        {"place_query": "서울 강남구", "service": "vet_hospital", "limit": 3},
        "동물",
    ),
    (
        "find_veteran_hospital",
        "보훈 위탁병원",
        {"place_query": "강남구", "user_request": "보훈 위탁병원", "limit": 3},
        "보훈",
    ),
]


async def run_one(name: str, label: str, kwargs: dict, expect: str) -> dict:
    fn = getattr(mcp, name)
    try:
        result = await fn(**kwargs)
        ok = expect.lower() in result.lower() or "찾지 못했습니다" not in result[:120]
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
    print("=== modu-emergencybell Tool Smoke Test ===\n")
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
