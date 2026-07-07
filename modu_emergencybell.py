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
from outdoor_services import find_outdoor_service
from odsay_client import find_transit_route
from safety_bell import find_safety_bells_near
from subway_facility import find_subway_facility

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
        situation=situation,
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

    Prefer **place_query** in natural language (e.g. 강남역, 서울 마포구, COEX).
    Coordinates are optional — only when the client already has GPS.
    user_type: wheelchair, child, infant_care, elderly_safety (restroom wall button), general.
    """
    if place_query and (latitude is None or longitude is None):
        restrooms, coords = await search_restrooms_by_query(
            place_query,
            radius,
            user_type=user_type if user_type != "general" else None,
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

    Examples: COEX, Gangnam Station, 마포구. Geocodes the query then searches MOIS data.
    Use user_type=elderly_safety for restrooms with an on-site emergency call button.
    """
    restrooms, coords = await search_restrooms_by_query(
        query,
        radius,
        user_type=user_type if user_type != "general" else None,
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

    Natural-language place_query only (e.g. 대전 유성구, 서울 마포구).
    treatment_day accepts: 월요일~일요일, 공휴일/설/추석, 2026-05-05, or 1-8.
    specialty: pediatric, general, or D-code.
    """
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

    Uses NEMC open-data API. place_query must include 시·군·구 (e.g. 서울 강남구).
    Information only — call 119 for life-threatening emergencies.
    """
    return await find_emergency_rooms_near(place_query=place_query, limit=limit)


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

    Natural-language place_query only (e.g. 서울 종로구, 부산 남구).
    treatment_day: 월요일~일요일, 공휴일/설/추석/어린이날, 2026-05-05, or 1-8.
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
    facility_type: all, locker, accessibility.
    Covers Seoul, Busan, Incheon subway data from local public datasets.
    """
    return find_subway_facility(station_query, facility_type=facility_type, limit=limit)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Public Transit Route",
    }
)
async def find_transit_route_tool(
    origin_query: str,
    destination_query: str,
    optimize: int = 0,
) -> str:
    f"""Public transit directions between two places via {SERVICE_DISPLAY} (ODsay).

    Examples: origin=서울역, destination=강남역. Uses geocoding + ODsay path search.
    optimize: 0=recommended, 1=minimum transfers, 2=minimum walking.
    """
    return await find_transit_route(
        origin_query=origin_query,
        destination_query=destination_query,
        optimize=optimize,
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
    wheelchair_accessible: bool = False,
    limit: int = 5,
) -> str:
    f"""Finds nearby ATM, free public WiFi, or veterinary hospitals via {SERVICE_DISPLAY}.

    place_query: natural language (e.g. 명동, 서울역, 부산 해운대).
    service: atm | wifi | vet_hospital (or 동물병원, 와이파이).
    wheelchair_accessible: for ATM only — filter wheelchair-accessible machines.
    """
    return await find_outdoor_service(
        place_query=place_query,
        service=service,
        wheelchair_accessible=wheelchair_accessible,
        limit=limit,
    )


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
