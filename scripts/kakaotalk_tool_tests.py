#!/usr/bin/env python3
"""카톡 스타일 Tool별 1건 스모크 테스트 — docs/KAKAOTALK_TOOL_TESTS.md."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import modu_emergencybell as mcp  # noqa: E402
from mcp.types import CallToolResult  # noqa: E402

# (tool, 카톡 한줄, kwargs, 성공 키워드)
KAKAOTALK_SCENARIOS: list[tuple[str, str, dict, str]] = [
    (
        "emergency_guide_tool",
        "혜화 화장실 급함",
        {
            "user_request": "야 나 지금 혜화골목길인데 화장실도 급하고 근처 편의점도 없어 뭐부터 해야돼",
        },
        "화장실",
    ),
    (
        "health_triage_tool",
        "레고 삼킴",
        {
            "user_request": "아이가 레고 블록 삼켰는데 어떻게 하지 서울 마포구",
            "place_query": "마포구",
        },
        "1339",
    ),
    (
        "emergency_guide_tool",
        "익선동 응급+약국",
        {
            "user_request": "엄마 무릎에서 피나는데 익선동 근처야 응급실이랑 약국 좀 알려줘",
            "place_query": "익선동",
        },
        "통합 안내",
    ),
    (
        "get_emergency_hotlines",
        "가스 냄새",
        {
            "situation_description": "옆집에서 매운 냄새? 같은 가스 냄새 나는데 신고 어디로 해야함",
            "situation": "utility_gas",
        },
        "1544",
    ),
    (
        "find_nearest_restroom",
        "코엑스 급똥",
        {"user_request": "ㅋㅋㅋ 코엑스 별관쪽 화장실 급함 진짜 죽겠다"},
        "화장실",
    ),
    (
        "find_nearest_restroom",
        "해운대 기저귀",
        {
            "place_query": "해운대 해수욕장",
            "user_request": "해운대 해수욕장에서 기저귀 갈만한 데 없을까 아가 데리고 왔어",
            "user_type": "infant_care",
            "limit": 3,
        },
        "화장실",
    ),
    (
        "find_medical_care",
        "영등포 토요일 밤",
        {
            "place_query": "영등포구",
            "user_request": "토요일 밤인데 팔에 두드러기 올라서 영등포구 의원 아직 열린 데 있어?",
            "care_type": "clinic",
            "specialty": "general",
            "treatment_day": "토요일",
        },
        "의원",
    ),
    (
        "find_veteran_hospital",
        "서면 보훈",
        {
            "place_query": "부산 서면",
            "user_request": "할아버지 국가유공자신데 부산 서면 쪽 위탁병원 어디 있는지 좀",
            "limit": 3,
        },
        "보훈",
    ),
    (
        "find_medical_care",
        "용산 응급실",
        {
            "place_query": "용산구",
            "user_request": "교통사고 목격했는데 용산구 응급실 자리 있나 지금?",
            "care_type": "emergency_room",
            "limit": 3,
        },
        "응급",
    ),
    (
        "find_medical_care",
        "종로3가 일요일 약국",
        {
            "place_query": "종로3가",
            "user_request": "일요일 아침인데 두통약 살 약국 종로3가 근처 없냐",
            "care_type": "pharmacy",
            "treatment_day": "일요일",
            "limit": 3,
        },
        "약국",
    ),
    (
        "find_safety_bell",
        "성수동 밤길",
        {
            "place_query": "성수동",
            "user_request": "성수동 카페거리 밤에 혼자 걷는데 비상벨 어딨어 무서움",
            "limit": 3,
        },
        "비상벨",
    ),
    (
        "get_phrase_card",
        "약 알레르기 영어",
        {"scenario": "pharmacy_allergy_check", "language": "en"},
        "allergic",
    ),
    (
        "find_subway_facility_tool",
        "서면역 캐리어",
        {
            "station_query": "서면역",
            "user_request": "부산 서면역에서 캐리어 맡을 수 있는 데 있어? 짐 너무 무거워",
            "facility_type": "locker",
            "limit": 3,
        },
        "보관",
    ),
    (
        "find_safe_place",
        "마포 쉼터",
        {
            "place_query": "마포구",
            "user_request": "초등학생 동생이 놀이터에서 못 찾겠다ㅠㅠ 마포구 쉼터 같은 데 있어?",
            "category": "youth",
            "limit": 3,
        },
        "안전",
    ),
    (
        "find_accessible_facility_tool",
        "여의도 휠체어",
        {
            "place_query": "여의도공원",
            "user_request": "여의도공원 휠체어 화장실 어디있는지 아는 사람??",
            "limit": 3,
        },
        "접근",
    ),
    (
        "find_outdoor_service_tool",
        "이태원 버스정류장",
        {
            "place_query": "이태원입구역",
            "user_request": "이태원입구역에서 버스 탈 건데 정류장이 어디있는거임 ㅋㅋ",
            "service": "bus_stop",
            "limit": 3,
        },
        "버스",
    ),
]


def _text(result: object) -> str:
    if isinstance(result, CallToolResult):
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(str(block.text))
        return " ".join(parts)
    return str(result)


def _is_error(result: object) -> bool:
    return isinstance(result, CallToolResult) and bool(result.isError)


async def run_one(name: str, kakao: str, kwargs: dict, expect: str) -> dict:
    fn = getattr(mcp, name)
    try:
        result = await fn(**kwargs)
        text = _text(result)
        ok = expect.lower() in text.lower()
        if _is_error(result) and "찾지 못했습니다" in text:
            ok = False
        return {
            "tool": name,
            "kakao": kakao,
            "ok": ok,
            "is_error": _is_error(result),
            "preview": text[:180].replace("\n", " "),
            "error": None,
        }
    except Exception as exc:
        return {
            "tool": name,
            "kakao": kakao,
            "ok": False,
            "is_error": True,
            "preview": "",
            "error": f"{exc.__class__.__name__}: {exc}",
        }


async def main() -> int:
    print("=== KakaoTalk Style Tool Tests (1 per tool) ===\n")
    results = []
    for name, kakao, kwargs, expect in KAKAOTALK_SCENARIOS:
        row = await run_one(name, kakao, kwargs, expect)
        results.append(row)
        status = "PASS" if row["ok"] else "FAIL"
        err_flag = " [isError]" if row["is_error"] else ""
        print(f"[{status}]{err_flag} {name}")
        print(f"  💬 {kakao}")
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
