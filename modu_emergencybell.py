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

TOOL_ANNOTATIONS = {
    "title": "",
    "readOnlyHint": True,
    "destructiveHint": False,
    "openWorldHint": True,
    "idempotentHint": True,
}


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

    Examples: `집에서 가스 냄새`, `종로구 창신동 약국`, `연산9동 내과`, `강남역 물품보관함`,
    `명동 휠체어 화장실`, `새벽 아이 39도`, `아이 실종 신고`.

    place_query: optional region hint when not in user_request (동·역·구 이름 OK).
    Dong-only names like 창신동, 연산9동 are expanded to 시·구 automatically.
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
    latitude: float | None = None,
    longitude: float | None = None,
    radius: int = 500,
    user_type: str = "general",
    open_now: bool = False,
    limit: int = 5,
) -> str:
    f"""Finds nearest public restrooms via {SERVICE_DISPLAY}.

    Prefer **place_query** in natural language (e.g. 강남역, 창신동, 연산9동, 서울 마포구).
    Coordinates are optional — only when the client already has GPS.
    user_type: wheelchair, child, infant_care, elderly_safety (restroom wall button), general.
    If user_type is general, keywords in place_query (휠체어/기저귀/비상벨) are auto-detected.
    """
    effective_type = user_type
    if user_type == "general" and place_query:
        inferred = infer_user_type_from_text(place_query)
        if inferred:
            effective_type = inferred
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
            "화장실을 찾으려면 **장소명**을 알려주세요 "
            "(예: `강남역`, `서울 마포구`, `부산 서면`).\n"
            "또는 `search_restroom`을 사용하세요."
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
    radius: int = 500,
    user_type: str = "general",
    open_now: bool = False,
    limit: int = 5,
) -> str:
    f"""Searches public restrooms near a place name or district via {SERVICE_DISPLAY}.

    Examples: COEX, Gangnam Station, 마포구, 명동 휠체어 화장실.
    user_type: wheelchair | infant_care | elderly_safety | child | general (auto-inferred from query).
    """
    effective_type = user_type
    if user_type == "general":
        inferred = infer_user_type_from_text(query)
        if inferred:
            effective_type = inferred
    restrooms, coords = await search_restrooms_by_query(
        query,
        radius,
        user_type=effective_type if effective_type != "general" else None,
        open_now=open_now,
        limit=limit,
    )
    return format_restroom_list(restrooms, query=query, coords_hint=coords)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Open Clinic",
    }
)
async def find_open_clinic(
    place_query: str,
    specialty: str = "pediatric",
    treatment_day: str | None = None,
    limit: int = 5,
) -> str:
    f"""Lists hospitals or clinics open on a given day near a region via {SERVICE_DISPLAY}.

    Natural-language place_query (동·역·구 OK — e.g. 창신동, 연산9동, 서울 마포구).
    treatment_day: 월요일~일요일, sunday/tuesday, 공휴일, 2026-05-05, or omit for today.
    specialty: pediatric, internal, general (aliases: internal_medicine, 내과).
    For veterinary use find_outdoor_service_tool(service=vet_hospital).
    """
    specialty = normalize_specialty(specialty)
    return await find_open_clinics_near(
        place_query=place_query,
        specialty=specialty,
        treatment_day=treatment_day,
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
    limit: int = 5,
) -> str:
    f"""Shows ER real-time bed availability by district via {SERVICE_DISPLAY}.

    Uses NEMC open-data API. place_query: 시·군·구 or 동·역 (e.g. 창신동, 강남구).
    Information only — call 119 for life-threatening emergencies.
    """
    return await find_emergency_rooms_near(
        place_query=place_query, limit=limit
    )


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Open Pharmacy",
    }
)
async def find_open_pharmacy(
    place_query: str,
    treatment_day: str | None = None,
    pharmacy_name: str | None = None,
    limit: int = 5,
) -> str:
    f"""Lists pharmacies open on a given day near a region via {SERVICE_DISPLAY}.

    Natural-language place_query (동·역·구 OK — e.g. 창신동, 종로구 창신동).
    treatment_day: 월요일~일요일, sunday/tuesday, 공휴일/설/추석/어린이날, 2026-05-05, or omit for today.
    For late-night (새벽/심야), results prioritize 365/24/심야 pharmacies — verify by phone.
    """
    return await find_open_pharmacies_near(
        place_query=place_query,
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
    latitude: float | None = None,
    longitude: float | None = None,
    radius_m: int = 500,
    place_type: str | None = None,
    limit: int = 5,
) -> str:
    f"""Finds crime-prevention outdoor safety bells near a place via {SERVICE_DISPLAY}.

    Use **place_query in natural language only** (e.g. 서울 이태원, 부산 광안리, 한강공원 여의도).
    Do NOT ask the user for coordinates — geocoding is internal.
    NOT restroom wall buttons (use search_restroom user_type=elderly_safety).
    place_type optional filter: 골목길, 공원, etc.
    """
    return await find_safety_bells_near(
        place_query=place_query,
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
    facility_type: str = "all",
    limit: int = 5,
) -> str:
    f"""Finds subway coin lockers and accessibility (elevator, wheelchair lift) via {SERVICE_DISPLAY}.

    Natural-language station name only (e.g. 강남역, 서울역, 부산 서면, 인천 계양).
    facility_type: all | locker | accessibility (aliases: elevator, luggage_storage).
    Use this for subway lockers — NOT find_outdoor_service_tool.
    """
    return find_subway_facility(station_query, facility_type=facility_type, limit=limit)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find SafeDream Safety Places",
    }
)
async def find_safe_place(
    place_query: str,
    category: str = "child_safety_house",
    radius_m: int = 1000,
    limit: int = 5,
) -> str:
    f"""Finds child safety houses and other Safe182 map facilities via {SERVICE_DISPLAY}.

    Natural-language place_query only (e.g. 종로구, 강남역, 명동).
    category: child_safety_house, elderly, youth (alias: youth_shelter), child_welfare, all.
    For missing child emergencies, also call 112 / Safe182 182.
    """
    return await search_safe_places(
        place_query=place_query,
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
    facility_id: str | None = None,
    include_subway: bool = True,
    limit: int = 5,
) -> str:
    f"""Finds wheelchair-accessible restrooms, subway lifts, and disabled-access facilities via {SERVICE_DISPLAY}.

    Natural-language place_query (e.g. 서울역, COEX, 부산 서면).
    Optional facility_id for 한국사회보장정보원 장애인편의시설 상세 조회.
    """
    return await find_accessible_facility(
        place_query=place_query,
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
    service: str = "atm",
    station_query: str | None = None,
    wheelchair_accessible: bool = False,
    limit: int = 5,
) -> str:
    f"""Finds subway-station ATM info, free public WiFi, or veterinary hospitals via {SERVICE_DISPLAY}.

    For ATM: set `station_query` to the station name when possible (e.g. 강남역, 서울역).
    `place_query` is a location hint used when the station name is unclear.
    service: atm | wifi | vet_hospital | locker (물품보관함 — subway only).
    For lockers prefer find_subway_facility_tool. For vet use vet_hospital not find_open_clinic.
    """
    return await find_outdoor_service(
        place_query=place_query,
        service=service,
        station_query=station_query,
        wheelchair_accessible=wheelchair_accessible,
        limit=limit,
    )


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
