"""MCP Prompt 템플릿 — 시나리오별 Tool 호출 가이드 (위키독스 2_Prompts 패턴)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """PlayMCP·Claude 등 prompts/list 지원 클라이언트용 시나리오 템플릿."""

    @mcp.prompt(
        name="urgent_restroom",
        title="급한 화장실 (급똥·배변)",
        description="명동성당·홍대 등 랜드마크 + 급한 화장실. find_nearest_restroom 호출 가이드.",
    )
    def urgent_restroom(user_message: str, place: str = "") -> str:
        """user_message: 사용자 원문 전체. place: 장소 힌트(선택)."""
        return (
            f"사용자: {user_message}\n\n"
            "다음 순서로 modu-emergencybell Tool을 호출하세요:\n"
            "1. `find_nearest_restroom` — **user_request**에 위 원문 전체, "
            "**place_query**에는 장소만 (예: 명동성당, 강남역, 홍대). "
            "'급똥'·'화장실'은 place_query에 넣지 마세요.\n"
            f"   예: user_request=\"{user_message}\", place_query=\"{place or '명동성당'}\"\n"
            "2. 휠체어·기저귀·비상벨 키워드가 있으면 user_type을 지정하거나 general로 두세요(자동 추론).\n"
            "3. 의도가 복합적이면 `emergency_guide_tool`을 대신 사용하세요."
        )

    @mcp.prompt(
        name="gas_leak_emergency",
        title="가스 누새·가스 냄새",
        description="1544 가스·119 안내. get_emergency_hotlines 우선.",
    )
    def gas_leak_emergency(user_message: str, place: str = "집") -> str:
        return (
            f"사용자: {user_message} (장소: {place})\n\n"
            "1. `get_emergency_hotlines` — situation_description에 원문, situation=`utility_gas` 권장.\n"
            "2. 필요 시 `emergency_guide_tool` — user_request=원문, place_query=장소.\n"
            "전화 연결·신고 대행은 하지 마세요. 안내 문구만 전달하세요."
        )

    @mcp.prompt(
        name="child_fever_night",
        title="새벽 아이 발열·39도",
        description="응급실·약국·소아과 복합. emergency_guide_tool 권장.",
    )
    def child_fever_night(user_message: str, place: str = "서울 마포구") -> str:
        return (
            f"사용자: {user_message}\n"
            f"기준 지역: {place}\n\n"
            "1. **`emergency_guide_tool`** — user_request=원문 전체, place_query=구·동·역.\n"
            "   (약국+소아과+응급실+119 안내를 한 번에 연결)\n"
            "또는 개별 호출:\n"
            f"- `find_open_pharmacy`(place_query=\"{place}\", user_request=원문)\n"
            f"- `find_open_clinic`(place_query=\"{place}\", specialty=pediatric, user_request=원문)\n"
            f"- `find_emergency_room`(place_query=\"{place}\", user_request=원문)\n"
            "생명 위협이면 119 우선 안내."
        )

    @mcp.prompt(
        name="missing_child",
        title="아이 실종·실종 신고",
        description="112·182·안전지킴이집. get_emergency_hotlines + find_safe_place.",
    )
    def missing_child(user_message: str, place: str = "서울") -> str:
        return (
            f"사용자: {user_message}\n\n"
            "1. `get_emergency_hotlines` — situation=`police` 또는 원문에 '실종' 포함.\n"
            f"2. `find_safe_place` — place_query=\"{place}\", category=child_safety_house, user_request=원문.\n"
            "3. 복합 안내: `emergency_guide_tool`(user_request=원문).\n"
            "112·182 즉시 신고를 강조하세요."
        )

    @mcp.prompt(
        name="wheelchair_access",
        title="휠체어·장애인 화장실·접근성",
        description="find_accessible_facility_tool — facility_id에 wheelchair_restroom 금지.",
    )
    def wheelchair_access(user_message: str, place: str = "서울역") -> str:
        return (
            f"사용자: {user_message}\n\n"
            f"1. `find_accessible_facility_tool` — place_query=\"{place}\", user_request=원문.\n"
            "   **facility_id**에 elevator·wheelchair_restroom 문자열을 넣지 마세요.\n"
            f"2. 화장실만: `find_nearest_restroom`(user_request=원문, user_type=wheelchair).\n"
            f"3. 지하철 역: `find_subway_facility_tool`(station_query=\"{place}\", facility_type=accessibility)."
        )

    @mcp.prompt(
        name="night_safety_crime",
        title="밤길 치안·범죄·안전비상벨",
        description="find_safety_bell + 범죄통계. emergency_guide도 가능.",
    )
    def night_safety_crime(user_message: str, place: str = "강남구") -> str:
        return (
            f"사용자: {user_message}\n\n"
            f"1. `find_safety_bell` — place_query=\"{place}\", user_request=원문 (길가 범죄예방 비상벨).\n"
            "2. 화장실 벽 비상벨이면 `find_nearest_restroom`(user_type=elderly_safety).\n"
            "3. `emergency_guide_tool` — 치안 통계+비상벨 한 번에.\n"
            "4. 불명확하면 `classify_emergency_intent`(user_request=원문)으로 라우팅 확인."
        )

    @mcp.prompt(
        name="foreign_tourist_help",
        title="외국인 관광객 병원·약국",
        description="get_phrase_card + find_open_clinic/pharmacy.",
    )
    def foreign_tourist_help(user_message: str, place: str = "Myeongdong") -> str:
        return (
            f"User: {user_message}\nPlace: {place}\n\n"
            "1. `get_phrase_card` — scenario=hospital_visit or pharmacy_visit, language=en.\n"
            "   Allergy question → scenario=pharmacy_allergy_check.\n"
            f"2. `find_nearest_restroom` or `find_open_clinic` — place_query=\"{place}\", user_request=원문.\n"
            "3. `emergency_guide_tool` for combined help."
        )

    @mcp.prompt(
        name="subway_locker",
        title="지하철 물품보관함·짐 맡기기",
        description="find_subway_facility_tool (locker). find_outdoor_service locker 아님.",
    )
    def subway_locker(user_message: str, station: str = "강남역") -> str:
        return (
            f"사용자: {user_message}\n\n"
            f"`find_subway_facility_tool` — station_query=\"{station}\", facility_type=locker, "
            "user_request=원문.\n"
            "물품보관함은 find_outdoor_service_tool이 아니라 **find_subway_facility_tool** 입니다."
        )

    @mcp.prompt(
        name="dong_only_pharmacy",
        title="동 이름만 — 약국·병원",
        description="창신동·연산9동 → 시·구 자동 보정.",
    )
    def dong_only_pharmacy(user_message: str, dong: str = "창신동") -> str:
        return (
            f"사용자: {user_message}\n\n"
            f"`find_open_pharmacy` — place_query=\"{dong}\", user_request=원문.\n"
            f"`find_open_clinic` — place_query=\"{dong}\", specialty=general, user_request=원문.\n"
            "동 이름만 넣어도 서버가 종로구·연제구 등으로 자동 확장합니다."
        )

    @mcp.prompt(
        name="wifi_bus_vet",
        title="WiFi·버스정류장·동물병원",
        description="find_outdoor_service_tool service 분기.",
    )
    def wifi_bus_vet(user_message: str, place: str = "홍대", service: str = "wifi") -> str:
        return (
            f"사용자: {user_message}\n\n"
            f"`find_outdoor_service_tool` — place_query=\"{place}\", service=\"{service}\", "
            "user_request=원문.\n"
            "service 값: wifi | bus_stop | vet_hospital | atm\n"
            "- 사람 병원 → find_open_clinic (동물병원 아님)\n"
            "- 보훈병원 → find_veteran_hospital"
        )

    @mcp.prompt(
        name="veteran_hospital",
        title="보훈·국가유공자 위탁병원",
        description="find_veteran_hospital. 병원명 환각 금지.",
    )
    def veteran_hospital(user_message: str, place: str = "강남구") -> str:
        return (
            f"사용자: {user_message}\n\n"
            f"`find_veteran_hospital` — place_query=\"{place}\", user_request=원문.\n"
            "인덱스에 없는 병원명(세브란스 등)을 지어내지 마세요. API 결과만 인용하세요."
        )

    @mcp.prompt(
        name="classify_before_call",
        title="Tool 선택이 애매할 때",
        description="classify_emergency_intent → 권장 Tool 확인 후 호출.",
    )
    def classify_before_call(user_message: str) -> str:
        return (
            f"사용자: {user_message}\n\n"
            "1. `classify_emergency_intent` — user_request=원문 전체 (read-only 라우팅).\n"
            "2. 응답의 **권장 Tool** 목록대로 파라미터 호출.\n"
            "3. 의도 2개 이상이면 `emergency_guide_tool` 우선.\n"
            "place_query에는 의도어(화장실·와이파이)가 아닌 **장소명만** 넣으세요."
        )
