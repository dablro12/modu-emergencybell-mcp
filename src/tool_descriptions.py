"""PlayMCP Tool description 공통 블록 (CHAINS WITH / NEVER)."""

from __future__ import annotations

SERVICE_NAME = "모두의비상벨: 급할 때 필요한 생활 정보를 찾는 도우미"

TOOL_CHAIN_FOOTER = """
PARAMETERS:
- user_request = user's **full original sentence** (Korean/English).
- place_query = landmark or district ONLY (명동역, 서울 마포구), NOT symptoms.

IF 2+ intents in one message → use `emergency_guide_tool` instead.
""".strip()

CHAINS = {
    "emergency_guide_tool": """
USE FIRST when: 2+ intents OR 급똥+안전, 열+약국+응급실, 실종+신고, 증상+어디가+약.
Replaces manual chains of hotlines + restroom + pharmacy + ER + safety_bell + health triage.
NEVER: single clear task — use the specific tool (faster).
""".strip(),
    "health_triage_tool": """
USE FIRST when: poison/ingestion (레고·본드·오복용), wrong drug, symptom→which department,
  fever+which hospital, headache+sore throat after exercise, what medicine to take.
CHAINS WITH: get_emergency_hotlines (119 vs 1339), find_medical_care (nearby clinics).
NEVER: diagnosis or prescription — triage + public data only.
""".strip(),
    "get_emergency_hotlines": """
CHAINS WITH: find_emergency_room (fall, chest pain), find_medical_care (fever unsure),
  find_safe_place (missing child), find_nearest_restroom user_type=elderly_safety (wall bell).
NEVER: replaces location search — hotlines only tell WHO to call.
""".strip(),
    "find_medical_care": """
CHAINS WITH: get_emergency_hotlines when symptoms severe or 119 vs 1339 confusion;
  health_triage_tool when symptom→department mapping needed first.
care_type: clinic | pharmacy | emergency_room | all (default all for fever/night).
NEVER: animals → find_outdoor_service_tool(vet_hospital); 보훈 → find_veteran_hospital.
""".strip(),
    "find_nearest_restroom": """
CHAINS WITH: get_emergency_hotlines if 비상벨/벽 버튼/119 confusion.
user_type: wheelchair | infant_care | elderly_safety (wall bell, NOT outdoor safety bell).
NEVER: find_safety_bell — that is street crime-prevention bell.
""".strip(),
    "find_safety_bell": """
CHAINS WITH: crime_stats included when district resolves.
NEVER: restroom wall button → find_nearest_restroom elderly_safety.
""".strip(),
    "find_outdoor_service_tool": """
CHAINS WITH: get_emergency_hotlines for pet emergency.
service=vet_hospital | animal_pharmacy for pets.
NEVER: find_medical_care or find_emergency_room for animals.
""".strip(),
    "find_veteran_hospital": """
USE for: 국가보훈부 위탁병원 / 보훈병원 / 국가유공자 병원.
NEVER: 반려동물 → find_outdoor_service_tool(vet_hospital).
""".strip(),
    "get_phrase_card": """
USE for: 외국인·관광객 병원/응급 상황에서 직원에게 보여줄 다국어 문구 카드.
""".strip(),
    "find_subway_facility_tool": """
USE for: 지하철역 물품보관함·엘리베이터·휠체어리프트·교통약자 편의시설.
""".strip(),
    "find_safe_place": """
USE for: 안전드림센터 / 아동안전지킴이집 / 실종·위기 아동 보호시설.
CHAINS WITH: get_emergency_hotlines when missing child.
""".strip(),
    "find_accessible_facility_tool": """
USE for: 휠체어 화장실·장애인 편의시설·무장애 시설 검색.
""".strip(),
}

TOOL_BASE_KO: dict[str, str] = {
    "emergency_guide_tool": "복합 응급·생활 요청을 한 번에 분류하고 필요한 툴을 자동 연결하는 오케스트레이션 툴입니다.",
    "health_triage_tool": "증상·오복용·오용약·진료과 선택을 공공 데이터로 안내하는 건강 트리아지 툴입니다.",
    "get_emergency_hotlines": "상황별 응급 전화번호(119·112·1339 등)와 신고 요령을 안내합니다.",
    "find_nearest_restroom": "주변 공중화장실을 검색합니다. 휠체어·기저귀교환대·노인 비상벨 옵션을 지원합니다.",
    "find_medical_care": "근처 의원·약국·응급실(병상) 정보를 NEMC 등 공공 API로 조회합니다.",
    "find_veteran_hospital": "국가보훈부 위탁병원(보훈병원)을 지역 기준으로 검색합니다.",
    "find_safety_bell": "범죄예방용 옥외 비상벨 위치를 검색합니다.",
    "get_phrase_card": "외국인 관광객이 병원·응급 상황에서 보여줄 다국어 문구 카드를 제공합니다.",
    "find_subway_facility_tool": "지하철역 물품보관함·엘리베이터·교통약자 편의시설을 검색합니다.",
    "find_safe_place": "안전드림센터·아동안전지킴이집 등 Safe182 보호시설을 검색합니다.",
    "find_accessible_facility_tool": "휠체어 화장실·장애인 편의시설·무장애 시설을 검색합니다.",
    "find_outdoor_service_tool": "ATM·무료WiFi·동물병원·동물약국·버스정류장 등 옥외 서비스를 검색합니다.",
}


def tool_description(base: str, chain_key: str) -> str:
    chain = CHAINS.get(chain_key, "")
    parts = [base.strip()]
    if chain:
        parts.append(chain)
    parts.append(TOOL_CHAIN_FOOTER)
    return "\n\n".join(parts)


def mcp_description(chain_key: str) -> str:
    """PlayMCP 마켓·심사 UI용 — 한 줄 기능 설명만 노출."""
    base = TOOL_BASE_KO.get(chain_key, chain_key).strip()
    return f"{SERVICE_NAME} - {base}"


def agent_tool_guide(chain_key: str) -> str:
    """에이전트 라우팅용 상세 가이드 (MCP description에는 넣지 않음)."""
    base = TOOL_BASE_KO.get(chain_key, chain_key)
    return tool_description(base, chain_key)
