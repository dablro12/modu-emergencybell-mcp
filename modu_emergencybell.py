"""modu-emergencybell(모두의비상벨) MCP Server — PlayMCP Streamable HTTP."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from helpers import (
    fetch_restrooms,
    format_dataset_info,
    format_restroom_list,
    get_record_by_id,
    search_restrooms_by_query,
)
from hotlines import format_emergency_hotlines
from nemc_client import (
    find_emergency_rooms_near,
    find_open_clinics_near,
    find_open_pharmacies_near,
)
from phrases import format_phrase_card
from safety_bell import find_safety_bells_near

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
    latitude: float,
    longitude: float,
    radius: int = 500,
    user_type: str = "general",
    open_now: bool = False,
    limit: int = 5,
) -> str:
    f"""Finds nearest public restrooms from WGS84 coordinates via {SERVICE_DISPLAY}.

    Data: MOIS public restroom open data. user_type filters: wheelchair, child, infant_care,
    elderly_safety (restroom wall emergency button — on-site staff, NOT 119), general.
    open_now filters by published hours when available. radius in meters (default 500).
    """
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

    Uses NEMC open-data API (national clinic search). place_query: district or landmark
    (e.g. 마포구, 서울 강남구). specialty: pediatric (D013), general, or D-code.
    treatment_day: 1-7 weekday, 8=public holiday (default: today KST).
    Pair with get_emergency_hotlines when unsure ER vs clinic.
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

    Uses NEMC pharmacy open-data API (15000576). place_query: district or landmark
    (e.g. 마포구). treatment_day: 1-7 weekday, 8=public holiday (default: today KST).
    Verify hours by phone — public data may differ from actual hours.
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

    Data: MOIS national safety-bell locations (~72k). NOT restroom wall buttons
    (use search_restroom with user_type=elderly_safety). Does NOT dial 119/112.
    place_query or latitude/longitude required. place_type filters e.g. 공원, 골목길.
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

    Scenarios: hospital_visit, pharmacy_visit, emergency_symptoms, allergy, call_help.
    Languages: ko, en, ja, zh. Pair with get_emergency_hotlines(foreign_visitor).
    """
    return format_phrase_card(scenario=scenario, language=language)


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Get Restroom Detail",
    }
)
async def get_restroom_detail(record_id: str) -> str:
    f"""Returns full detail for one public restroom by MOIS management ID via {SERVICE_DISPLAY}."""
    record = get_record_by_id(record_id)
    if not record:
        return f"Record `{record_id}` not found."
    return format_restroom_list([{**record, "distance_m": None}])


@mcp.tool(
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Dataset Info",
    }
)
async def get_dataset_info() -> str:
    f"""Returns dataset statistics for restroom records used by {SERVICE_DISPLAY}."""
    return format_dataset_info()


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
