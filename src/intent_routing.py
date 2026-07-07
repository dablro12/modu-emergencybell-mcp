"""의도 분류 → MCP Tool 라우팅 · 장소 파라미터 복구."""

from __future__ import annotations

from i18n_support import agent_translation_hint, detect_input_language
from place_context import (
    classify_intents,
    extract_place_from_text,
    infer_specialty,
    infer_user_type_from_text,
    merge_place_inputs,
)


# (intent_tag, tool_name, 한줄 설명)
INTENT_TOOL_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("restroom", "find_nearest_restroom", "공중화장실·급한 배변"),
    ("hotlines", "get_emergency_hotlines", "119/112/1339 등 신고번호 안내"),
    ("crime_stats", "find_safety_bell", "치안·범죄통계·야간 안전(안전비상벨 포함)"),
    ("safety_bell", "find_safety_bell", "범죄예방 안전비상벨 위치"),
    ("health_triage", "health_triage_tool", "증상·중독·오복용·진료과 안내"),
    ("clinic", "find_medical_care", "병원·의원·진료"),
    ("pharmacy", "find_medical_care", "약국·심야약국"),
    ("emergency_room", "find_medical_care", "응급실 병상 현황"),
    ("veteran_hospital", "find_veteran_hospital", "보훈 위탁병원"),
    ("accessible", "find_accessible_facility_tool", "휠체어·장애인 편의시설"),
    ("subway_locker", "find_subway_facility_tool", "지하철 물품보관함"),
    ("atm", "find_outdoor_service_tool", "지하철 ATM (service=atm)"),
    ("wifi", "find_outdoor_service_tool", "무료 WiFi (service=wifi)"),
    ("bus_stop", "find_outdoor_service_tool", "버스정류장 (service=bus_stop)"),
    ("vet", "find_outdoor_service_tool", "동물병원 (service=vet_hospital)"),
    ("vet_pharmacy", "find_outdoor_service_tool", "동물약국 (service=animal_pharmacy)"),
    ("safe_place", "find_safe_place", "아동안전지킴이집·Safe182"),
    ("phrase", "get_phrase_card", "외국인용 문장 카드"),
)

MULTI_INTENT_THRESHOLD = 2


async def resolve_effective_place(
    *,
    place_query: str | None = None,
    user_request: str | None = None,
    fallback: str = "서울",
) -> tuple[str, "PlaceContext"]:
    """LLM place_query + 원문 user_request → 병합 후 PlaceContext 해석."""
    from place_resolver import PlaceContext, resolve_place_context

    merged = merge_place_inputs(place_query, user_request)
    query_for_resolve = merged or fallback
    ctx = await resolve_place_context(query_for_resolve)
    effective = ctx.expanded_query or ctx.query or query_for_resolve
    return effective, ctx


def tools_for_intents(intents: list[str]) -> list[dict[str, str]]:
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for tag in intents:
        for intent, tool, desc in INTENT_TOOL_ROUTES:
            if intent != tag or tool in seen:
                continue
            seen.add(tool)
            rows.append({"intent": intent, "tool": tool, "description": desc})
    return rows


def format_intent_routing(
    user_request: str,
    *,
    place_query: str | None = None,
    merged_place: str = "",
    intents: list[str] | None = None,
) -> str:
    """LLM·운영자용 라우팅 가이드 (read-only)."""
    detected = intents or classify_intents(user_request)
    routes = tools_for_intents(detected)
    extracted = extract_place_from_text(user_request)

    lines = [
        "## 의도 분류 · Tool 라우팅",
        f"- **사용자 문장**: {user_request.strip()}",
    ]
    if place_query:
        lines.append(f"- **전달된 place_query**: {place_query}")
    if extracted:
        lines.append(f"- **서버 추출 장소**: `{extracted}`")
    if merged_place:
        lines.append(f"- **해석 기준 지역**: `{merged_place}`")

    lang = detect_input_language(user_request)
    lines.append(f"- **입력 언어(추정)**: `{lang}`")
    hint = agent_translation_hint(lang)
    if hint:
        lines.append(f"- **에이전트**: {hint}")

    lines.append("")
    lines.append("### 감지된 의도")
    if detected:
        for tag in detected:
            lines.append(f"- `{tag}`")
    else:
        lines.append("- (없음)")

    lines.append("")
    lines.append("### 권장 Tool (우선순위)")
    if len(detected) >= MULTI_INTENT_THRESHOLD:
        lines.append(
            "1. **`emergency_guide_tool`** — 의도가 2개 이상이면 통합 안내를 먼저 호출하세요."
        )
        lines.append("   - `user_request`에 사용자 **원문 전체**를 넣으세요.")
        if merged_place or extracted:
            hint = merged_place or extracted
            lines.append(f"   - 선택: `place_query=\"{hint}\"`")
        lines.append("")

    for idx, row in enumerate(routes, start=1 if len(detected) >= MULTI_INTENT_THRESHOLD else 1):
        prefix = idx + (1 if len(detected) >= MULTI_INTENT_THRESHOLD else 0)
        lines.append(f"{prefix}. **`{row['tool']}`** — {row['description']} (`{row['intent']}`)")

    if not routes:
        lines.append("1. **`get_emergency_hotlines`** — 상황 불명확 시 신고번호부터 안내")

    lines.append("")
    lines.append("### 파라미터 힌트 (MCP best practice)")
    lines.append("- 개별 Tool 호출 시 **`user_request`에 원문 전체** + `place_query`에 장소만 병행 전달.")
    lines.append("- `place_query`만 넣지 말 것: `화장실`, `급똥`, `와이파이` 같은 의도어는 장소가 아님.")
    lines.append("- `find_accessible_facility_tool`의 `facility_id`는 wfcltId 숫자형만 (wheelchair_restroom 금지).")
    lines.append("- 동물병원 → `find_outdoor_service_tool(service=vet_hospital)`, 동물약국 → `service=animal_pharmacy`.")
    lines.append("- 사람 병원·응급실·약국 → `find_medical_care` (care_type: clinic|pharmacy|emergency_room|all).")
    lines.append("- 증상·중독·오복용·진료과 → `health_triage_tool` 먼저.")
    lines.append("- 반려동물(강아지·고양이)에는 `find_medical_care`·`find_veteran_hospital` 사용 금지.")

    specialty = infer_specialty(user_request)
    user_type = infer_user_type_from_text(user_request)
    if specialty != "general":
        lines.append(f"- 추론 specialty: `{specialty}` → `find_medical_care`")
    if user_type:
        lines.append(f"- 추론 restroom user_type: `{user_type}`")

    return "\n".join(lines).strip()


async def classify_and_route(
    user_request: str,
    place_query: str | None = None,
) -> str:
    effective, ctx = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback="",
    )
    intents = classify_intents(user_request)
    body = format_intent_routing(
        user_request,
        place_query=place_query,
        merged_place=effective or ctx.expanded_query or "",
        intents=intents,
    )
    if ctx.warning:
        body += f"\n\n_{ctx.warning}_"
    return body
