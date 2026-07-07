"""modu-emergencybell(모두의비상벨) MCP Server — PlayMCP Streamable HTTP."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from helpers import (
    fetch_restrooms,
    format_restroom_list,
    search_restrooms_by_query,
)
from hotlines import format_emergency_hotlines
from nemc_client import (
    find_emergency_rooms_near,
    find_open_clinics_near,
    find_open_pharmacies_near,
)
from phrases import format_phrase_card
from accessible_facility_client import find_accessible_facility
from outdoor_services import find_outdoor_service
from safe182_client import search_safe_places
from safety_bell import find_safety_bells_near
from subway_facility import find_subway_facility
from emergency_guide import emergency_guide
from veteran_hospital import find_veteran_hospitals_near
from intent_routing import classify_and_route, resolve_effective_place
from mcp_prompts import register_prompts
from place_resolver import resolve_place_context
from place_context import (
    infer_user_type_from_text,
    normalize_safe_category,
    normalize_situation_tag,
    normalize_specialty,
)

load_dotenv()

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))

# PlayMCP 식별자 · description 병기 (영문+국문)
SERVICE_DISPLAY = "modu-emergencybell(모두의비상벨)"
MCP_IDENTIFY = "modu-emergencybell"

mcp = FastMCP(MCP_IDENTIFY, host=MCP_HOST, port=MCP_PORT)

register_prompts(mcp)

TOOL_ANNOTATIONS = {
    "title": "",
    "readOnlyHint": True,
    "destructiveHint": False,
    "openWorldHint": True,
    "idempotentHint": True,
}


TOOL_WHEN_MULTI = (
    "Multiple intents or unclear routing → call `classify_emergency_intent` first, "
    "or use `emergency_guide_tool` for combined answers."
)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Classify Intent And Route Tools",
    }
)
async def classify_emergency_intent(
    user_request: str,
    place_query: str | None = None,
) -> str:
    f"""Read-only routing guide for {SERVICE_DISPLAY} — call when unsure which tool to use.

  WHEN TO USE:
  - User message mixes several needs (e.g. restroom + safety + pharmacy).
  - You are about to call a specialized tool but location/intent is ambiguous.
  - PlayMCP picked the wrong tool or left place_query empty.

  WHEN NOT TO USE:
  - Single clear intent with known place → call the specific tool directly.
  - User already answered a clarification question.

  Returns: detected intents, recommended tool names, server-extracted place hint,
  and parameter tips. Does NOT fetch live data.

  Always pass the user's **full original sentence** in user_request.
  Example: user_request="명동성당쪽인데 급똥이야 화장실 알려줘"
  """
    return await classify_and_route(user_request, place_query=place_query)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Emergency Guide (Natural Language)",
    }
)
async def emergency_guide_tool(
    user_request: str,
    place_query: str | None = None,
    language: str = "ko",
) -> str:
    f"""**Recommended first tool** for natural-language emergency help via {SERVICE_DISPLAY}.

    Parses Korean/English requests and chains the right backends automatically:
    hotlines, restrooms, clinics, pharmacies, ER beds, safety bells, subway lockers/ATM,
    accessible facilities, Safe182 places, phrase cards.

    WHEN TO USE: multi-intent or conversational requests (2+ needs in one message).
    WHEN NOT TO USE: single clear task — use the specific tool (faster).

    Examples: `집에서 가스 냄새`, `종로구 창신동 약국`, `연산9동 내과`, `강남역 물품보관함`,
    `명동 휠체어 화장실`, `명동성당쪽 급똥`, `새벽 아이 39도`, `아이 실종 신고`,
    `강남구 밤에 안전할까`, `강남역 버스정류장`.

    user_request: user's **full original message** (required).
    place_query: optional region hint when location is separate from user_request.
    {TOOL_WHEN_MULTI}
    """
    return await emergency_guide(user_request, place_query=place_query, language=language)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Who To Call In This Situation",
    }
)
async def get_emergency_hotlines(
    situation_description: str,
    situation: str | None = None,
    language: str = "ko",
) -> str:
    f"""Tells the user which emergency number to call for their situation via {SERVICE_DISPLAY}.

    Use when the user asks where to call (e.g. 119 vs 1339, restroom wall button vs 119,
    child fever, gas leak). Returns prioritized hotlines and next steps. Does NOT dial.

    situation_description: user's situation in their own words (Korean or English).
    situation: optional pre-classified tag (life_threatening, medical_urgent, restroom_help,
      foreign_visitor, poison, police, mental_crisis, school_violence, utility_electric,
      utility_gas, safety_hazard, unsure).
    language: ko or en for the response text.
    """
    return format_emergency_hotlines(
        situation_description,
        situation=normalize_situation_tag(situation),
        language=language if language in ("ko", "en") else "ko",
    )


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Nearest Restroom",
    }
)
async def find_nearest_restroom(
    place_query: str | None = None,
    user_request: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius: int = 500,
    user_type: str = "general",
    open_now: bool = False,
    limit: int = 5,
) -> str:
    f"""Finds nearest public restrooms via {SERVICE_DISPLAY}.

    WHEN TO USE: restroom / toilet / 급똥 / 배변 — single intent only.
    WHEN NOT TO USE: multi-intent → `emergency_guide_tool`.

    Pass **user_request** with the user's full sentence when possible.
    place_query: landmark or area only (명동성당, 홍대, 강남역) — NOT words like 급똥/화장실.
    Coordinates optional when client has GPS.
    user_type: wheelchair, child, infant_care, elderly_safety, general (auto from text).
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback="",
    )
    combined_text = " ".join(
        part for part in (user_request or "", place_query or "", effective_place) if part
    )
    effective_type = user_type
    if user_type == "general" and combined_text:
        inferred = infer_user_type_from_text(combined_text)
        if inferred:
            effective_type = inferred
    if effective_place and (latitude is None or longitude is None):
        restrooms, coords = await search_restrooms_by_query(
            effective_place,
            radius,
            user_type=effective_type if effective_type != "general" else None,
            open_now=open_now,
            limit=limit,
        )
        display = effective_place or place_query or user_request
        return format_restroom_list(restrooms, query=display, coords_hint=coords)

    if place_query and (latitude is None or longitude is None):
        restrooms, coords = await search_restrooms_by_query(
            place_query,
            radius,
            user_type=effective_type if effective_type != "general" else None,
            open_now=open_now,
            limit=limit,
        )
        return format_restroom_list(restrooms, query=place_query, coords_hint=coords)

    if latitude is None or longitude is None:
        return (
            "화장실을 찾으려면 **장소명** 또는 **user_request(원문)** 를 알려주세요.\n"
            "예: `user_request=\"명동성당쪽 급똥\"` 또는 `place_query=\"강남역\"`.\n"
            "의도가 복합적이면 `emergency_guide_tool` 또는 `classify_emergency_intent`를 사용하세요."
        )

    restrooms = await fetch_restrooms(
        latitude,
        longitude,
        radius,
        user_type=user_type if user_type != "general" else None,
        open_now=open_now,
        limit=limit,
    )
    return format_restroom_list(restrooms, coords_hint=f"{latitude:.6f},{longitude:.6f}")


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Search Restroom By Place",
    }
)
async def search_restroom(
    query: str,
    user_request: str | None = None,
    radius: int = 500,
    user_type: str = "general",
    open_now: bool = False,
    limit: int = 5,
) -> str:
    f"""Searches public restrooms near a place name or district via {SERVICE_DISPLAY}.

    WHEN TO USE: alias of find_nearest_restroom with required query string.
    Pass user_request (full sentence) when query might omit the place name.

    Examples: COEX, Gangnam Station, 마포구, 명동 휠체어 화장실.
    user_type: wheelchair | infant_care | elderly_safety | child | general.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=query,
        user_request=user_request,
        fallback=query,
    )
    combined_text = " ".join(part for part in (user_request or "", query, effective_place) if part)
    effective_type = user_type
    if user_type == "general":
        inferred = infer_user_type_from_text(combined_text)
        if inferred:
            effective_type = inferred
    restrooms, coords = await search_restrooms_by_query(
        effective_place,
        radius,
        user_type=effective_type if effective_type != "general" else None,
        open_now=open_now,
        limit=limit,
    )
    return format_restroom_list(restrooms, query=effective_place, coords_hint=coords)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Open Clinic",
    }
)
async def find_open_clinic(
    place_query: str,
    user_request: str | None = None,
    specialty: str = "pediatric",
    treatment_day: str | None = None,
    limit: int = 5,
) -> str:
    f"""Lists hospitals or clinics open on a given day near a region via {SERVICE_DISPLAY}.

    WHEN TO USE: 병원·의원·진료·소아·내과 (people, not animals).
    WHEN NOT TO USE: 동물병원 → find_outdoor_service_tool(vet_hospital); 보훈 → find_veteran_hospital.

    place_query: 동·역·구. Pass user_request (full sentence) to recover place from text.
    treatment_day: 월~일, 공휴일, 2026-05-05, or omit for today.
    specialty: pediatric, internal, general, veteran.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query,
    )
    specialty = normalize_specialty(specialty)
    if specialty == "veteran":
        return await find_veteran_hospitals_near(place_query=effective_place, limit=limit)
    return await find_open_clinics_near(
        place_query=effective_place,
        specialty=specialty,
        treatment_day=treatment_day,
        limit=limit,
    )


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Veteran Entrusted Hospital",
    }
)
async def find_veteran_hospital(
    place_query: str,
    user_request: str | None = None,
    hospital_type: str | None = None,
    limit: int = 5,
) -> str:
    f"""Finds **보훈의료 위탁병원** (국가보훈부) near a region via {SERVICE_DISPLAY}.

    WHEN TO USE: 국가유공자·보훈·위탁병원 keywords in user message.
    WHEN NOT TO USE: general night clinic → find_open_clinic; do not invent hospital names.

    place_query + optional user_request (full sentence) for place recovery.
    hospital_type optional: 종합병원, 요양병원, 의원.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query,
    )
    return await find_veteran_hospitals_near(
        place_query=effective_place,
        hospital_type=hospital_type,
        limit=limit,
    )


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Emergency Room",
    }
)
async def find_emergency_room(
    place_query: str,
    user_request: str | None = None,
    limit: int = 5,
) -> str:
    f"""Shows ER real-time bed availability by district via {SERVICE_DISPLAY}.

    WHEN TO USE: 응급실·병상·life-threatening symptoms (information only — call 119).
    place_query + user_request for region. NEMC open-data API.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query,
    )
    return await find_emergency_rooms_near(place_query=effective_place, limit=limit)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Open Pharmacy",
    }
)
async def find_open_pharmacy(
    place_query: str,
    user_request: str | None = None,
    treatment_day: str | None = None,
    pharmacy_name: str | None = None,
    limit: int = 5,
) -> str:
    f"""Lists pharmacies open on a given day near a region via {SERVICE_DISPLAY}.

    WHEN TO USE: 약국·심야약국·fever medicine context.
    place_query + user_request. treatment_day: 월~일, 공휴일, or omit for today.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query,
    )
    return await find_open_pharmacies_near(
        place_query=effective_place,
        treatment_day=treatment_day,
        pharmacy_name=pharmacy_name,
        limit=limit,
    )


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Outdoor Safety Bell",
    }
)
async def find_safety_bell(
    place_query: str | None = None,
    user_request: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_m: int = 500,
    place_type: str | None = None,
    limit: int = 5,
) -> str:
    f"""Finds crime-prevention outdoor safety bells near a place via {SERVICE_DISPLAY}.

    WHEN TO USE: 안전비상벨·치안·범죄·야간 안전 (NOT restroom wall buttons).
    Pass user_request (full sentence) and/or place_query. Geocoding is internal.
    Includes regional crime statistics when district resolves.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query or "",
    )
    return await find_safety_bells_near(
        place_query=effective_place or None,
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        place_type=place_type,
        limit=limit,
    )


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Get Phrase Card",
    }
)
async def get_phrase_card(
    scenario: str = "hospital_visit",
    language: str = "en",
) -> str:
    f"""Returns show-to-staff phrase cards for foreign visitors via {SERVICE_DISPLAY}.

    Scenarios: hospital_visit, pharmacy_visit, pharmacy_allergy_check, emergency_symptoms,
    allergy, call_help. Use pharmacy_allergy_check when user asks if a medicine causes allergy.
    Languages: ko, en, ja, zh.
    """
    return format_phrase_card(scenario=scenario, language=language)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Subway Locker And Accessibility",
    }
)
async def find_subway_facility_tool(
    station_query: str,
    user_request: str | None = None,
    facility_type: str = "all",
    limit: int = 5,
) -> str:
    f"""Finds subway coin lockers and accessibility (elevator, wheelchair lift) via {SERVICE_DISPLAY}.

    WHEN TO USE: 물품보관함·짐맡기기·지하철 엘리베이터 at a **station**.
    station_query: 역 이름 (강남역). user_request helps extract station from full sentence.
    facility_type: all | locker | accessibility.
    """
    from place_context import extract_place_from_text

    station = station_query
    if user_request:
        hint = extract_place_from_text(user_request)
        if hint and "역" in hint:
            station = hint
    return find_subway_facility(station, facility_type=facility_type, limit=limit)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find SafeDream Safety Places",
    }
)
async def find_safe_place(
    place_query: str,
    user_request: str | None = None,
    category: str = "child_safety_house",
    radius_m: int = 1000,
    limit: int = 5,
) -> str:
    f"""Finds child safety houses and other Safe182 map facilities via {SERVICE_DISPLAY}.

    WHEN TO USE: 안전지킴이집·쉼터·실종 아동 (also call 112/182).
    place_query + user_request. category: child_safety_house, elderly, youth, all.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query,
    )
    return await search_safe_places(
        place_query=effective_place,
        category=normalize_safe_category(category),
        radius_m=radius_m,
        limit=limit,
    )


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Accessible Facility",
    }
)
async def find_accessible_facility_tool(
    place_query: str,
    user_request: str | None = None,
    facility_id: str | None = None,
    include_subway: bool = True,
    limit: int = 5,
) -> str:
    f"""Finds wheelchair-accessible restrooms, subway lifts, and disabled-access facilities via {SERVICE_DISPLAY}.

    WHEN TO USE: 휠체어·장애인·엘리베이터·접근성 (single area search).
    place_query + user_request. landmarks OK (명동성당, COEX, 홍대).
    facility_id: wfcltId only — NOT wheelchair_restroom / elevator strings.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query,
    )
    return await find_accessible_facility(
        place_query=effective_place,
        facility_id=facility_id,
        include_subway=include_subway,
        limit=limit,
    )


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find ATM WiFi Or Vet Hospital",
    }
)
async def find_outdoor_service_tool(
    place_query: str,
    user_request: str | None = None,
    service: str = "atm",
    station_query: str | None = None,
    wheelchair_accessible: bool = False,
    limit: int = 5,
) -> str:
    f"""Finds subway-station ATM, free WiFi, vet hospitals, or bus stops via {SERVICE_DISPLAY}.

    WHEN TO USE: wifi | atm | bus_stop | vet_hospital — one service per call.
    place_query + user_request (landmarks OK: 홍대, 명동성당).
    service: atm | wifi | vet_hospital | bus_stop (locker → find_subway_facility_tool).
    station_query: station/stop name hint for atm or bus_stop.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query,
    )
    return await find_outdoor_service(
        place_query=effective_place,
        service=service,
        station_query=station_query,
        wheelchair_accessible=wheelchair_accessible,
        limit=limit,
    )


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
