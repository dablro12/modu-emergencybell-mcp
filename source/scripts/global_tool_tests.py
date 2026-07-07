#!/usr/bin/env python3
"""글로벌(영·중) Tool 스모크 테스트 — docs/GLOBAL_KAKAOTALK.md."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "source" / "app"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import modu_emergencybell as mcp  # noqa: E402
from mcp.types import CallToolResult  # noqa: E402

# (tool, lang, message, kwargs, expect)
GLOBAL_SCENARIOS: list[tuple[str, str, str, dict, str]] = [
    (
        "health_triage_tool",
        "EN",
        "Swallowed LEGO",
        {"user_request": "My child swallowed a LEGO brick in Mapo — what should I do?"},
        "1339",
    ),
    (
        "emergency_guide_tool",
        "EN",
        "Fever child Mapo",
        {
            "user_request": "My kid has 39°C fever at midnight near Mapo — clinic and pharmacy?",
            "place_query": "Mapo-gu",
        },
        "통합 안내",
    ),
    (
        "get_emergency_hotlines",
        "EN",
        "Gas smell",
        {
            "situation_description": "Smells like gas in my apartment — who do I call in Korea?",
            "situation": "utility_gas",
            "language": "en",
        },
        "1544",
    ),
    (
        "find_nearest_restroom",
        "EN",
        "Myeongdong Cathedral",
        {
            "user_request": "Wheelchair restroom near Myeongdong Cathedral — really urgent",
        },
        "화장실",
    ),
    (
        "find_nearest_restroom",
        "EN",
        "Haeundae diaper",
        {
            "place_query": "Haeundae Beach",
            "user_request": "Need a place to change diapers at Haeundae Beach with my baby",
            "user_type": "infant_care",
            "limit": 3,
        },
        "화장실",
    ),
    (
        "find_medical_care",
        "EN",
        "Yeongdeungpo Saturday",
        {
            "place_query": "Yeongdeungpo-gu",
            "user_request": "Saturday night rash on my arm — any clinic open in Yeongdeungpo?",
            "care_type": "clinic",
            "limit": 3,
        },
        "의원",
    ),
    (
        "find_medical_care",
        "EN",
        "Jongno Sunday",
        {
            "place_query": "Jongno 3-ga",
            "user_request": "Sunday morning headache — pharmacy near Jongno 3-ga?",
            "care_type": "pharmacy",
            "limit": 3,
        },
        "약국",
    ),
    (
        "find_safety_bell",
        "EN",
        "Seongsu night",
        {
            "place_query": "Seongsu",
            "user_request": "Walking alone at Seongsu cafe street at night — safety bells nearby?",
            "limit": 3,
        },
        "비상벨",
    ),
    (
        "find_subway_facility_tool",
        "EN",
        "Seomyeon locker",
        {
            "station_query": "Seomyeon Station",
            "user_request": "Can I store my suitcase at Seomyeon Station Busan? Too heavy",
            "facility_type": "locker",
            "limit": 3,
        },
        "보관",
    ),
    (
        "find_accessible_facility_tool",
        "EN",
        "Yeouido wheelchair",
        {
            "place_query": "Yeouido Park",
            "user_request": "Where is wheelchair accessible restroom in Yeouido Park?",
            "limit": 3,
        },
        "접근",
    ),
    (
        "find_outdoor_service_tool",
        "EN",
        "Itaewon bus",
        {
            "place_query": "Itaewon",
            "user_request": "Where is the bus stop near Itaewon station?",
            "service": "bus_stop",
            "limit": 3,
        },
        "버스",
    ),
    (
        "emergency_guide_tool",
        "ZH",
        "明洞厕所",
        {"user_request": "明洞圣堂附近哪里有厕所？很急！"},
        "화장실",
    ),
    (
        "find_nearest_restroom",
        "ZH",
        "明洞轮椅厕所",
        {"user_request": "明洞圣堂附近哪里有轮椅厕所？很急！"},
        "화장실",
    ),
    (
        "find_medical_care",
        "ZH",
        "江南药店",
        {
            "place_query": "江南",
            "user_request": "江南站附近有药店吗？头疼",
            "care_type": "pharmacy",
            "limit": 3,
        },
        "약국",
    ),
    (
        "find_safety_bell",
        "ZH",
        "海云台安全",
        {
            "place_query": "海云台",
            "user_request": "海云台晚上走路安全吗？有安全铃吗？",
            "limit": 3,
        },
        "비상벨",
    ),
]


def _text(result: object) -> str:
    if isinstance(result, CallToolResult):
        return " ".join(str(block.text) for block in result.content if hasattr(block, "text"))
    return str(result)


def _is_error(result: object) -> bool:
    return isinstance(result, CallToolResult) and bool(result.isError)


async def run_one(name: str, lang: str, message: str, kwargs: dict, expect: str) -> dict:
    fn = getattr(mcp, name)
    try:
        result = await fn(**kwargs)
        text = _text(result)
        ok = expect.lower() in text.lower()
        if _is_error(result) and "찾지 못했습니다" in text:
            ok = False
        return {
            "tool": name,
            "lang": lang,
            "message": message,
            "ok": ok,
            "is_error": _is_error(result),
            "preview": text[:180].replace("\n", " "),
            "error": None,
        }
    except Exception as exc:
        return {
            "tool": name,
            "lang": lang,
            "message": message,
            "ok": False,
            "is_error": True,
            "preview": "",
            "error": f"{exc.__class__.__name__}: {exc}",
        }


async def main() -> int:
    print("=== Global Tool Tests (EN + ZH) ===\n")
    results = []
    for name, lang, message, kwargs, expect in GLOBAL_SCENARIOS:
        row = await run_one(name, lang, message, kwargs, expect)
        results.append(row)
        status = "PASS" if row["ok"] else "FAIL"
        err_flag = " [isError]" if row["is_error"] else ""
        print(f"[{status}]{err_flag} [{lang}] {name}")
        print(f"  💬 {message}")
        if row["error"]:
            print(f"  ERROR: {row['error']}")
        else:
            print(f"  → {row['preview'][:140]}...")
        print()

    passed = sum(1 for r in results if r["ok"])
    print(f"Result: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
