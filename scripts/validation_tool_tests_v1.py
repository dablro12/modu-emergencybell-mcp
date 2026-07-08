#!/usr/bin/env python3
"""모두의비상벨 MCP live validation — 12 tools x 10 examples.

The goal is call-quality validation: each case uses realistic MCP arguments from
easy to complex and verifies that the tool returns a non-error response.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import modu_emergencybell as mcp  # noqa: E402
from mcp.types import CallToolResult  # noqa: E402

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@dataclass(frozen=True)
class Case:
    level: str
    name: str
    tool: str
    kwargs: dict[str, Any]
    expect: tuple[str, ...] = ()


def _text(result: object) -> str:
    if isinstance(result, CallToolResult):
        return " ".join(str(block.text) for block in result.content if hasattr(block, "text"))
    return str(result)


def _is_error(result: object) -> bool:
    return isinstance(result, CallToolResult) and bool(result.isError)


def _bad_response(text: str) -> bool:
    return "서비스 오류:" in text or "Traceback" in text


async def run_case(case: Case) -> dict[str, Any]:
    fn = getattr(mcp, case.tool)
    try:
        result = await fn(**case.kwargs)
        text = _text(result)
        ok = bool(text.strip()) and not _is_error(result) and not _bad_response(text)
        if case.expect:
            ok = ok and any(marker.lower() in text.lower() for marker in case.expect)
        return {
            "tool": case.tool,
            "level": case.level,
            "name": case.name,
            "status": "OK" if ok else "FAIL",
            "preview": text.replace("\n", " ")[:180],
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "tool": case.tool,
            "level": case.level,
            "name": case.name,
            "status": "FAIL",
            "preview": "",
            "error": f"{exc.__class__.__name__}: {exc}",
        }


CASES: dict[str, list[Case]] = {
    "emergency_guide_tool": [
        Case("easy", "급한 화장실", "emergency_guide_tool", {"user_request": "명동성당 쪽인데 화장실 급해"}, ("통합 안내",)),
        Case("easy", "약국+위치", "emergency_guide_tool", {"user_request": "종로3가 일요일 아침 약국 어디 있어?", "place_query": "종로3가"}, ("통합 안내",)),
        Case("medium", "응급실+약국", "emergency_guide_tool", {"user_request": "익선동인데 엄마 무릎에서 피 나 응급실이랑 약국 알려줘", "place_query": "익선동"}, ("응급", "약국")),
        Case("medium", "아동 발열", "emergency_guide_tool", {"user_request": "새벽에 아이 39도인데 마포구 소아과랑 약국", "place_query": "마포구"}, ("통합 안내",)),
        Case("medium", "밤길 안전", "emergency_guide_tool", {"user_request": "성수동 카페거리 밤에 혼자 걷는데 비상벨 어딨어", "place_query": "성수동"}, ("비상벨",)),
        Case("medium", "실종+쉼터", "emergency_guide_tool", {"user_request": "마포구에서 초등학생 동생을 못 찾겠어 신고랑 쉼터 알려줘", "place_query": "마포구"}, ("112", "안전")),
        Case("hard", "외국인 약국", "emergency_guide_tool", {"user_request": "English help: pharmacy near Myeongdong for allergy medicine", "place_query": "Myeongdong", "language": "en"}, ("통합 안내",)),
        Case("hard", "접근성+화장실", "emergency_guide_tool", {"user_request": "강남역 근처 휠체어 화장실이랑 엘리베이터", "place_query": "강남역"}, ("접근", "화장실")),
        Case("hard", "반려동물 응급", "emergency_guide_tool", {"user_request": "홍대 근처 강아지가 아파 동물병원 어디야", "place_query": "홍대"}, ("동물", "병원")),
        Case("hard", "복합 이동", "emergency_guide_tool", {"user_request": "서울역 캐리어 맡기고 근처 약국도 찾아줘", "place_query": "서울역"}, ("통합 안내",)),
    ],
    "health_triage_tool": [
        Case("easy", "레고 삼킴", "health_triage_tool", {"user_request": "아이가 레고 블록을 삼켰어 어떻게 하지", "place_query": "마포구"}, ("건강 트리아지",)),
        Case("easy", "본드 삼킴", "health_triage_tool", {"user_request": "아이가 본드를 조금 삼킨 것 같아", "place_query": "강남구"}, ("119", "1339")),
        Case("easy", "오복용", "health_triage_tool", {"user_request": "약을 잘못 먹었는데 어떻게 해야 해", "place_query": "종로구"}, ("건강 트리아지",)),
        Case("medium", "동물약 오복용", "health_triage_tool", {"user_request": "강아지 약을 내 약인 줄 알고 먹었어", "place_query": "서울"}, ("119", "1339")),
        Case("medium", "운동 후 두통", "health_triage_tool", {"user_request": "축구 후 목이 쑤시고 머리가 아파 신설동역 근처", "place_query": "신설동역"}, ("건강 트리아지",)),
        Case("medium", "고열", "health_triage_tool", {"user_request": "아이가 39도 열이 나는데 어느 병원으로 가야 해", "place_query": "마포구"}, ("소아", "1339")),
        Case("medium", "두드러기", "health_triage_tool", {"user_request": "팔에 두드러기 올라서 어디 과 가야 해", "place_query": "영등포구"}, ("진료과",)),
        Case("hard", "약 추천 문의", "health_triage_tool", {"user_request": "목 아프고 두통 있는데 무슨 약 먹어야 해", "place_query": "종로구"}, ("처방", "1339")),
        Case("hard", "가슴 통증", "health_triage_tool", {"user_request": "가슴이 답답하고 숨쉬기 힘들어", "place_query": "강남구"}, ("119",)),
        Case("hard", "반려동물 분기", "health_triage_tool", {"user_request": "고양이가 토하는데 근처 병원", "place_query": "홍대"}, ("반려동물", "동물")),
    ],
    "get_emergency_hotlines": [
        Case("easy", "가스 냄새", "get_emergency_hotlines", {"situation_description": "집에서 가스 냄새가 나", "situation": "utility_gas"}, ("1544",)),
        Case("easy", "화재", "get_emergency_hotlines", {"situation_description": "건물에서 연기가 나고 불이 난 것 같아"}, ("119",)),
        Case("easy", "실종", "get_emergency_hotlines", {"situation_description": "아이가 실종됐어요", "situation": "police"}, ("112",)),
        Case("medium", "의료 상담", "get_emergency_hotlines", {"situation_description": "밤에 아이가 열이 나는데 119인지 1339인지 모르겠어"}, ("1339", "119")),
        Case("medium", "범죄 신고", "get_emergency_hotlines", {"situation_description": "누가 따라오는 것 같고 위험해요"}, ("112",)),
        Case("medium", "약 오복용", "get_emergency_hotlines", {"situation_description": "약을 잘못 먹었어 어떻게 문의해", "situation": "poison"}, ("1339", "119")),
        Case("medium", "외국인 도움", "get_emergency_hotlines", {"situation_description": "foreign tourist emergency help", "language": "en"}, ("119",)),
        Case("hard", "화장실 비상벨", "get_emergency_hotlines", {"situation_description": "화장실 안 비상벨 누르면 119로 가나요"}, ("비상벨",)),
        Case("hard", "교통사고", "get_emergency_hotlines", {"situation_description": "교통사고를 목격했는데 어디 전화해"}, ("119", "112")),
        Case("hard", "가스 영어", "get_emergency_hotlines", {"situation_description": "Smells like gas in my apartment", "situation": "utility_gas", "language": "en"}, ("1544",)),
    ],
    "find_nearest_restroom": [
        Case("easy", "명동성당", "find_nearest_restroom", {"place_query": "명동성당", "limit": 3}, ("화장실",)),
        Case("easy", "강남역", "find_nearest_restroom", {"place_query": "강남역", "limit": 3}, ("화장실",)),
        Case("easy", "해운대", "find_nearest_restroom", {"place_query": "해운대 해수욕장", "limit": 3}, ("화장실",)),
        Case("medium", "휠체어", "find_nearest_restroom", {"place_query": "여의도공원", "user_request": "휠체어 화장실", "user_type": "wheelchair", "limit": 3}, ("화장실",)),
        Case("medium", "기저귀", "find_nearest_restroom", {"place_query": "코엑스", "user_request": "기저귀 교환대", "user_type": "infant_care", "limit": 3}, ("화장실",)),
        Case("medium", "좌표 검색", "find_nearest_restroom", {"latitude": 37.5665, "longitude": 126.9780, "limit": 3}, ("화장실",)),
        Case("medium", "open_now", "find_nearest_restroom", {"place_query": "서울역", "open_now": True, "limit": 3}, ("화장실",)),
        Case("hard", "영문 입력", "find_nearest_restroom", {"user_request": "Wheelchair restroom near Myeongdong Cathedral", "limit": 3}, ("화장실",)),
        Case("hard", "원문만", "find_nearest_restroom", {"user_request": "홍대입구역 근처 화장실 급해", "limit": 3}, ("화장실",)),
        Case("hard", "노인 비상벨", "find_nearest_restroom", {"place_query": "강남역", "user_request": "어르신 화장실 비상벨", "user_type": "elderly_safety", "limit": 3}, ("화장실",)),
    ],
    "find_medical_care": [
        Case("easy", "마포 약국", "find_medical_care", {"place_query": "마포구", "care_type": "pharmacy", "limit": 3}, ("의료기관 안내", "약국")),
        Case("easy", "강남 의원", "find_medical_care", {"place_query": "강남구", "care_type": "clinic", "limit": 3}, ("의료기관 안내", "의원")),
        Case("easy", "용산 응급실", "find_medical_care", {"place_query": "용산구", "care_type": "emergency_room", "limit": 3}, ("응급",)),
        Case("medium", "일요일 약국", "find_medical_care", {"place_query": "종로3가", "care_type": "pharmacy", "treatment_day": "일요일", "limit": 3}, ("약국",)),
        Case("medium", "토요일 진료", "find_medical_care", {"place_query": "영등포구", "care_type": "clinic", "treatment_day": "토요일", "limit": 3}, ("의원",)),
        Case("medium", "소아과", "find_medical_care", {"place_query": "마포구", "care_type": "clinic", "specialty": "pediatric", "limit": 3}, ("의료기관 안내",)),
        Case("medium", "정형외과", "find_medical_care", {"place_query": "강남구", "care_type": "clinic", "specialty": "orthopedic", "limit": 3}, ("의료기관 안내",)),
        Case("hard", "all", "find_medical_care", {"place_query": "서울역", "user_request": "약국이랑 응급실 둘 다", "care_type": "all", "limit": 3}, ("의료기관 안내",)),
        Case("hard", "영문 지역", "find_medical_care", {"place_query": "Jongno-gu", "user_request": "Sunday pharmacy near Jongno", "care_type": "pharmacy", "limit": 3}, ("약국",)),
        Case("hard", "동물 분기 방지", "find_medical_care", {"place_query": "홍대", "user_request": "사람 병원 말고 두통 약국", "care_type": "pharmacy", "limit": 3}, ("약국",)),
    ],
    "find_veteran_hospital": [
        Case("easy", "강남구", "find_veteran_hospital", {"place_query": "강남구", "limit": 3}, ("보훈",)),
        Case("easy", "부산 서면", "find_veteran_hospital", {"place_query": "부산 서면", "limit": 3}, ("보훈",)),
        Case("easy", "마포구", "find_veteran_hospital", {"place_query": "마포구", "limit": 3}, ("보훈",)),
        Case("medium", "대전", "find_veteran_hospital", {"place_query": "대전 서구", "limit": 3}, ("보훈",)),
        Case("medium", "대구", "find_veteran_hospital", {"place_query": "대구 중구", "limit": 3}, ("보훈",)),
        Case("medium", "광주", "find_veteran_hospital", {"place_query": "광주 동구", "limit": 3}, ("보훈",)),
        Case("hard", "국가유공자 원문", "find_veteran_hospital", {"place_query": "부산진구", "user_request": "국가유공자 위탁병원", "limit": 3}, ("보훈",)),
        Case("hard", "hospital_type", "find_veteran_hospital", {"place_query": "서울 강남구", "hospital_type": "의원", "limit": 3}, ("보훈",)),
        Case("hard", "반려동물 오입력", "find_veteran_hospital", {"place_query": "강남구", "user_request": "강아지 병원", "limit": 3}, ("동물병원", "반려동물")),
        Case("hard", "넓은 지역", "find_veteran_hospital", {"place_query": "서울", "limit": 3}, ("보훈",)),
    ],
    "find_safety_bell": [
        Case("easy", "성수동", "find_safety_bell", {"place_query": "성수동", "limit": 3}, ("비상벨",)),
        Case("easy", "강남구", "find_safety_bell", {"place_query": "강남구", "limit": 3}, ("비상벨",)),
        Case("easy", "해운대", "find_safety_bell", {"place_query": "해운대", "limit": 3}, ("비상벨",)),
        Case("medium", "밤길 원문", "find_safety_bell", {"place_query": "이태원", "user_request": "밤에 혼자 걷는데 안전비상벨", "limit": 3}, ("비상벨",)),
        Case("medium", "공원", "find_safety_bell", {"place_query": "여의도공원", "place_type": "공원", "limit": 3}, ("비상벨",)),
        Case("medium", "좌표", "find_safety_bell", {"latitude": 37.5665, "longitude": 126.9780, "limit": 3}, ("비상벨",)),
        Case("hard", "범죄통계", "find_safety_bell", {"place_query": "강남구", "user_request": "강남구 밤에 안전할까", "limit": 3}, ("비상벨",)),
        Case("hard", "영문", "find_safety_bell", {"place_query": "Seongsu", "user_request": "safety bell near Seongsu at night", "limit": 3}, ("비상벨",)),
        Case("hard", "골목", "find_safety_bell", {"place_query": "혜화동", "place_type": "골목", "limit": 3}, ("비상벨",)),
        Case("hard", "화장실 벽 비상벨 혼동", "find_safety_bell", {"place_query": "강남역", "user_request": "길가 범죄예방 비상벨", "limit": 3}, ("비상벨",)),
    ],
    "get_phrase_card": [
        Case("easy", "hospital en", "get_phrase_card", {"scenario": "hospital_visit", "language": "en"}, ("Phrase card",)),
        Case("easy", "pharmacy en", "get_phrase_card", {"scenario": "pharmacy_visit", "language": "en"}, ("Phrase card",)),
        Case("easy", "allergy en", "get_phrase_card", {"scenario": "pharmacy_allergy_check", "language": "en"}, ("allergic", "Phrase card")),
        Case("medium", "emergency ja", "get_phrase_card", {"scenario": "emergency_symptoms", "language": "ja"}, ("Phrase card",)),
        Case("medium", "help zh", "get_phrase_card", {"scenario": "call_help", "language": "zh"}, ("Phrase card",)),
        Case("medium", "alias hospital", "get_phrase_card", {"scenario": "hospital", "language": "en"}, ("Phrase card",)),
        Case("hard", "alias allergy", "get_phrase_card", {"scenario": "allergy", "language": "en"}, ("Phrase card",)),
        Case("hard", "ko", "get_phrase_card", {"scenario": "pharmacy_visit", "language": "ko"}, ("긴급번호",)),
        Case("hard", "unknown", "get_phrase_card", {"scenario": "unknown_case", "language": "en"}, ("Unknown scenario",)),
        Case("hard", "unsupported language", "get_phrase_card", {"scenario": "hospital_visit", "language": "fr"}, ("Phrase card",)),
    ],
    "find_subway_facility_tool": [
        Case("easy", "강남역 전체", "find_subway_facility_tool", {"station_query": "강남역", "limit": 3}, ("지하철 시설",)),
        Case("easy", "서면 보관함", "find_subway_facility_tool", {"station_query": "서면역", "facility_type": "locker", "limit": 3}, ("보관",)),
        Case("easy", "서울역 접근성", "find_subway_facility_tool", {"station_query": "서울역", "facility_type": "accessibility", "limit": 3}, ("지하철 시설",)),
        Case("medium", "엘리베이터", "find_subway_facility_tool", {"station_query": "홍대입구역", "facility_type": "elevator", "limit": 3}, ("지하철 시설",)),
        Case("medium", "원문 역 추출", "find_subway_facility_tool", {"station_query": "강남", "user_request": "강남역 캐리어 맡길 보관함", "facility_type": "locker", "limit": 3}, ("보관",)),
        Case("medium", "부산", "find_subway_facility_tool", {"station_query": "해운대역", "facility_type": "all", "limit": 3}, ("지하철 시설",)),
        Case("hard", "영문 station", "find_subway_facility_tool", {"station_query": "Seomyeon Station", "facility_type": "locker", "limit": 3}, ("지하철 시설", "보관")),
        Case("hard", "wheelchair lift", "find_subway_facility_tool", {"station_query": "서울역", "facility_type": "wheelchair_lift", "limit": 3}, ("지하철 시설",)),
        Case("hard", "없는 역", "find_subway_facility_tool", {"station_query": "없는역", "limit": 3}, ("찾지 못했습니다",)),
        Case("hard", "명동역", "find_subway_facility_tool", {"station_query": "명동역", "facility_type": "all", "limit": 3}, ("지하철 시설",)),
    ],
    "find_safe_place": [
        Case("easy", "마포 아동안전", "find_safe_place", {"place_query": "마포구", "category": "child_safety_house", "limit": 3}, ("안전",)),
        Case("easy", "강남 youth", "find_safe_place", {"place_query": "강남구", "category": "youth", "limit": 3}, ("안전",)),
        Case("easy", "종로", "find_safe_place", {"place_query": "종로구", "limit": 3}, ("안전",)),
        Case("medium", "실종 원문", "find_safe_place", {"place_query": "마포구", "user_request": "아이를 못 찾겠어", "category": "child_safety_house", "limit": 3}, ("안전",)),
        Case("medium", "부산", "find_safe_place", {"place_query": "부산 해운대구", "category": "youth", "limit": 3}, ("안전",)),
        Case("medium", "radius 1500", "find_safe_place", {"place_query": "서울역", "radius_m": 1500, "limit": 3}, ("안전",)),
        Case("hard", "청소년 쉼터", "find_safe_place", {"place_query": "마포구", "user_request": "청소년 쉼터", "category": "youth", "limit": 3}, ("안전",)),
        Case("hard", "영문", "find_safe_place", {"place_query": "Mapo-gu", "user_request": "child safe place", "limit": 3}, ("안전",)),
        Case("hard", "넓은 범위", "find_safe_place", {"place_query": "강남역", "radius_m": 2000, "limit": 3}, ("안전",)),
        Case("hard", "서울", "find_safe_place", {"place_query": "서울", "limit": 3}, ("안전",)),
    ],
    "find_accessible_facility_tool": [
        Case("easy", "여의도", "find_accessible_facility_tool", {"place_query": "여의도공원", "limit": 3}, ("접근성",)),
        Case("easy", "강남역", "find_accessible_facility_tool", {"place_query": "강남역", "limit": 3}, ("접근성",)),
        Case("easy", "서울역", "find_accessible_facility_tool", {"place_query": "서울역", "limit": 3}, ("접근성",)),
        Case("medium", "휠체어 원문", "find_accessible_facility_tool", {"place_query": "명동성당", "user_request": "휠체어 화장실", "limit": 3}, ("접근성",)),
        Case("medium", "include subway false", "find_accessible_facility_tool", {"place_query": "여의도", "include_subway": False, "limit": 3}, ("접근성",)),
        Case("medium", "부산", "find_accessible_facility_tool", {"place_query": "부산 서면", "limit": 3}, ("접근성",)),
        Case("hard", "영문", "find_accessible_facility_tool", {"place_query": "Yeouido Park", "user_request": "wheelchair restroom", "limit": 3}, ("접근성",)),
        Case("hard", "facility id empty", "find_accessible_facility_tool", {"place_query": "강남구", "facility_id": None, "limit": 3}, ("접근성",)),
        Case("hard", "엘리베이터", "find_accessible_facility_tool", {"place_query": "서울역", "user_request": "엘리베이터 무장애", "limit": 3}, ("접근성",)),
        Case("hard", "명동", "find_accessible_facility_tool", {"place_query": "명동", "limit": 3}, ("접근성",)),
    ],
    "find_outdoor_service_tool": [
        Case("easy", "ATM", "find_outdoor_service_tool", {"place_query": "명동", "service": "atm", "limit": 3}, ("ATM",)),
        Case("easy", "WiFi", "find_outdoor_service_tool", {"place_query": "홍대", "service": "wifi", "limit": 3}, ("WiFi", "와이파이")),
        Case("easy", "동물병원", "find_outdoor_service_tool", {"place_query": "강남구", "service": "vet_hospital", "limit": 3}, ("동물",)),
        Case("easy", "버스정류장", "find_outdoor_service_tool", {"place_query": "이태원", "service": "bus_stop", "limit": 3}, ("버스",)),
        Case("medium", "동물약국", "find_outdoor_service_tool", {"place_query": "마포구", "service": "animal_pharmacy", "limit": 3}, ("동물", "약국")),
        Case("medium", "station ATM", "find_outdoor_service_tool", {"place_query": "서울역", "station_query": "서울역", "service": "atm", "limit": 3}, ("ATM",)),
        Case("medium", "wheelchair", "find_outdoor_service_tool", {"place_query": "강남역", "service": "bus_stop", "wheelchair_accessible": True, "limit": 3}, ("버스",)),
        Case("hard", "반려동물 원문", "find_outdoor_service_tool", {"place_query": "홍대", "user_request": "강아지가 아파 동물병원", "service": "vet_hospital", "limit": 3}, ("동물",)),
        Case("hard", "영문 bus", "find_outdoor_service_tool", {"place_query": "Itaewon", "user_request": "bus stop near Itaewon", "service": "bus_stop", "limit": 3}, ("버스",)),
        Case("hard", "부산 와이파이", "find_outdoor_service_tool", {"place_query": "해운대", "service": "wifi", "limit": 3}, ("WiFi", "와이파이")),
    ],
}


async def main() -> int:
    total = passed = 0
    failures: list[dict[str, Any]] = []

    for tool, cases in CASES.items():
        if len(cases) != 10:
            failures.append({"tool": tool, "status": "FAIL", "error": f"expected 10 cases, got {len(cases)}"})
            continue
        print(f"\n## {tool}")
        for case in cases:
            row = await run_case(case)
            total += 1
            if row["status"] == "OK":
                passed += 1
            else:
                failures.append(row)
            print(f"[{row['status']}] {case.level} · {case.name} — {row['preview'][:120]}")

    print(f"\nResult: {passed}/{total} passed")
    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
