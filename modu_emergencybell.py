"""modu-emergencybell(모두의비상벨) MCP Server — PlayMCP Streamable HTTP."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

_APP_DIR = Path(__file__).resolve().parent / "src"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from helpers import (
    fetch_restrooms,
    format_restroom_list,
    search_restrooms_by_query,
)
from hotlines import format_emergency_hotlines
from health_triage import health_triage
from medical_care import find_medical_care as find_medical_care_near
from phrases import format_phrase_card
from accessible_facility_client import find_accessible_facility
from outdoor_services import find_outdoor_service
from safe182_client import search_safe_places
from safety_bell import find_safety_bells_near
from subway_facility import find_subway_facility
from emergency_guide import emergency_guide
from veteran_hospital import find_veteran_hospitals_near
from intent_routing import resolve_effective_place
from mcp_prompts import register_prompts
from mcp_tool_result import install_tool_error_wrapping
from place_context import (
    infer_specialty,
    infer_user_type_from_text,
    is_pet_care_query,
    normalize_safe_category,
    normalize_situation_tag,
    normalize_specialty,
)
from tool_descriptions import mcp_description, tool_description
from map_preview import register_map_routes

load_dotenv()

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))

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

UserRequest = Annotated[
    str,
    Field(description="사용자가 보낸 원문 전체입니다. 증상, 긴급도, 장소, 복합 요청을 생략하지 말고 그대로 넣습니다."),
]
OptionalUserRequest = Annotated[
    str | None,
    Field(description="사용자가 보낸 원문 전체입니다. place_query만으로 부족할 때 위치·상황·필터 단서를 보존합니다."),
]
PlaceQuery = Annotated[
    str,
    Field(description="장소명, 랜드마크, 역명, 행정구역만 넣습니다. 증상·요청 문장·시설 종류는 넣지 않습니다."),
]
OptionalPlaceQuery = Annotated[
    str | None,
    Field(description="장소명, 랜드마크, 역명, 행정구역만 넣습니다. 모르면 user_request 원문으로 보완합니다."),
]
Language = Annotated[
    str,
    Field(description="응답 언어 힌트입니다. 기본값은 ko이며, 다국어 사용자 입력에는 en, zh, ja 등을 사용합니다."),
]
Limit = Annotated[int, Field(description="반환할 최대 결과 수입니다. 카카오톡 응답에서는 보통 3~5개를 권장합니다.")]
Latitude = Annotated[float | None, Field(description="현재 위치의 위도입니다. 좌표가 있을 때만 사용하고, 장소명이 있으면 place_query를 우선합니다.")]
Longitude = Annotated[float | None, Field(description="현재 위치의 경도입니다. 좌표가 있을 때만 사용하고, 장소명이 있으면 place_query를 우선합니다.")]
Radius = Annotated[int, Field(description="검색 반경(미터)입니다. 기본 500m이며 너무 넓히면 결과 관련성이 떨어질 수 있습니다.")]
RadiusM = Annotated[int, Field(description="검색 반경(미터)입니다. 기본 500~1000m를 권장합니다.")]


@mcp.tool(
    description=mcp_description("emergency_guide_tool"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Emergency Guide (Start Here)",
    }
)
async def emergency_guide_tool(
    user_request: UserRequest,
    place_query: OptionalPlaceQuery = None,
    language: Language = "ko",
) -> str:
    f"""Primary orchestration tool for multi-intent requests in {SERVICE_DISPLAY}.

    USE FIRST when one message includes 2+ needs (e.g. symptom+hospital+pharmacy,
    restroom+safety, missing child+hotline, pet emergency+nearest vet).
    It automatically classifies intent and chains the right tools.

    Examples: `명동성당 급똥+밤에 안전`, `새벽 아이 39도`, `레고 삼켰어`, `신설동역 축구 후 두통`.
    """
    return await emergency_guide(user_request, place_query=place_query, language=language)


@mcp.tool(
    description=mcp_description("health_triage_tool"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Health Triage And Specialty Guide",
    }
)
async def health_triage_tool(
    user_request: UserRequest,
    place_query: OptionalPlaceQuery = None,
    language: Language = "ko",
) -> str:
    f"""Symptom·poison·wrong-drug triage via {SERVICE_DISPLAY} (HIRA disease + MFDS e약은요 + NEMC).

    USE for: child swallowed LEGO/glue, wrong medication, which department/hospital,
    headache+sore throat after exercise, what medicine (public info only — not prescription).
    If users also ask for nearby facilities/hotlines together, prefer `emergency_guide_tool`.
    """
    return await health_triage(user_request, place_query=place_query, language=language)


@mcp.tool(
    description=mcp_description("get_emergency_hotlines"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Who To Call In This Situation",
    }
)
async def get_emergency_hotlines(
    situation_description: Annotated[
        str,
        Field(description="사용자가 설명한 위급 상황 원문입니다. 예: 가스 냄새, 실종, 119/1339 문의."),
    ],
    situation: Annotated[
        str | None,
        Field(description="상황 태그 힌트입니다. 예: medical_urgent, police, utility_gas, poison. 모르면 비워둡니다."),
    ] = None,
    language: Language = "ko",
) -> str:
    f"""Emergency numbers (119/112/1339) for one clear situation via {SERVICE_DISPLAY}.

    For mixed intents with location/facility lookup, prefer `emergency_guide_tool`.
    """
    return format_emergency_hotlines(
        situation_description,
        situation=normalize_situation_tag(situation),
        language=language if language in ("ko", "en") else "ko",
    )


@mcp.tool(
    description=mcp_description("find_nearest_restroom"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Nearest Restroom",
    }
)
async def find_nearest_restroom(
    place_query: OptionalPlaceQuery = None,
    user_request: OptionalUserRequest = None,
    latitude: Latitude = None,
    longitude: Longitude = None,
    radius: Radius = 500,
    user_type: Annotated[
        str,
        Field(description="화장실 이용자 유형입니다. general, wheelchair, infant_care, elderly_safety 중 하나를 권장합니다."),
    ] = "general",
    open_now: Annotated[bool, Field(description="현재 이용 가능 여부를 우선할지 여부입니다. 데이터 한계가 있어 참고용으로 사용합니다.")] = False,
    limit: Limit = 5,
) -> str:
    f"""Public restroom lookup via {SERVICE_DISPLAY}. Replaces deprecated search_restroom.

    Single-intent tool. If the request also includes safety/medical/hotline needs,
    use `emergency_guide_tool` for composite tool chaining.
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
            "복합 질문은 `emergency_guide_tool`을 사용하세요."
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
    description=mcp_description("find_medical_care"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Clinic Pharmacy Or ER",
    }
)
async def find_medical_care(
    place_query: PlaceQuery,
    user_request: OptionalUserRequest = None,
    care_type: Annotated[
        str,
        Field(description="조회할 의료 자원입니다. all, clinic, pharmacy, emergency_room 중 하나를 권장합니다."),
    ] = "all",
    specialty: Annotated[
        str,
        Field(description="진료과 힌트입니다. general, internal, pediatric, orthopedic 등을 사용하며 모르면 general입니다."),
    ] = "general",
    treatment_day: Annotated[
        str | None,
        Field(description="요일 필터입니다. 예: 월요일, 토요일, 일요일, 공휴일. 모르면 현재 날짜 기준으로 판단합니다."),
    ] = None,
    pharmacy_name: Annotated[
        str | None,
        Field(description="특정 약국명을 찾을 때만 사용합니다. 일반 주변 약국 검색이면 비워둡니다."),
    ] = None,
    limit: Limit = 5,
) -> str:
    f"""Clinics, pharmacies, or ER beds near a region via {SERVICE_DISPLAY} (NEMC).

    Merges find_open_clinic + find_open_pharmacy + find_emergency_room in one call.
    care_type: all | clinic | pharmacy | emergency_room.
    For complex natural-language requests, prefer `emergency_guide_tool`.
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query,
    )
    combined = " ".join(part for part in (user_request or "", place_query, effective_place) if part)
    inferred = infer_specialty(combined) if specialty == "general" else specialty
    return await find_medical_care_near(
        place_query=effective_place,
        user_request=user_request,
        care_type=care_type,
        specialty=normalize_specialty(inferred),
        treatment_day=treatment_day,
        pharmacy_name=pharmacy_name,
        limit=limit,
    )


@mcp.tool(
    description=mcp_description("find_veteran_hospital"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Veteran Entrusted Hospital",
    }
)
async def find_veteran_hospital(
    place_query: PlaceQuery,
    user_request: OptionalUserRequest = None,
    hospital_type: Annotated[
        str | None,
        Field(description="보훈 위탁병원 유형 힌트입니다. 반려동물·동물병원 요청에는 사용하지 않습니다."),
    ] = None,
    limit: Limit = 5,
) -> str:
    f"""국가보훈부 위탁병원 near a region via {SERVICE_DISPLAY}.

    NEVER use for pet care. Pet/vet requests should call `find_outdoor_service_tool`
    with `service=vet_hospital` (or use `emergency_guide_tool`).
    """
    effective_place, _ = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback=place_query,
    )
    combined = " ".join(part for part in (user_request or "", place_query, effective_place) if part)
    if hospital_type and "animal" in hospital_type.lower():
        return (
            "⚠️ 동물병원은 `find_outdoor_service_tool(service=vet_hospital)`을 사용하세요.\n\n"
            + await find_outdoor_service(
                place_query=effective_place,
                service="vet_hospital",
                limit=limit,
            )
        )
    if is_pet_care_query(combined):
        return (
            "⚠️ 반려동물은 보훈 위탁병원이 아닙니다.\n\n"
            + await find_outdoor_service(
                place_query=effective_place,
                service="vet_hospital",
                limit=limit,
            )
        )
    return await find_veteran_hospitals_near(
        place_query=effective_place,
        hospital_type=hospital_type,
        limit=limit,
    )


@mcp.tool(
    description=mcp_description("find_safety_bell"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Outdoor Safety Bell",
    }
)
async def find_safety_bell(
    place_query: OptionalPlaceQuery = None,
    user_request: OptionalUserRequest = None,
    latitude: Latitude = None,
    longitude: Longitude = None,
    radius_m: RadiusM = 500,
    place_type: Annotated[
        str | None,
        Field(description="비상벨 설치 장소 유형 힌트입니다. 예: 공원, 골목, 학교 주변. 모르면 비워둡니다."),
    ] = None,
    limit: Limit = 5,
) -> str:
    f"""Crime-prevention outdoor safety bells via {SERVICE_DISPLAY}.

    This is for street/public safety bells, not restroom wall emergency buttons.
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
    description=mcp_description("get_phrase_card"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Get Phrase Card",
    }
)
async def get_phrase_card(
    scenario: Annotated[
        str,
        Field(description="보여줄 문장 카드 상황입니다. 예: hospital_visit, pharmacy_allergy_check, emergency_help."),
    ] = "hospital_visit",
    language: Language = "en",
) -> str:
    f"""Show-to-staff phrase cards for foreign visitors via {SERVICE_DISPLAY}."""
    return format_phrase_card(scenario=scenario, language=language)


@mcp.tool(
    description=mcp_description("find_subway_facility_tool"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Subway Locker And Accessibility",
    }
)
async def find_subway_facility_tool(
    station_query: Annotated[
        str,
        Field(description="지하철역 이름만 넣습니다. 예: 강남역, 서울역, 서면역."),
    ],
    user_request: OptionalUserRequest = None,
    facility_type: Annotated[
        str,
        Field(description="찾을 지하철 시설입니다. all, locker, accessibility, elevator, wheelchair_lift 등을 권장합니다."),
    ] = "all",
    limit: Limit = 5,
) -> str:
    f"""Subway lockers and accessibility (elevator, wheelchair lift) via {SERVICE_DISPLAY}.

    For broader multi-intent travel/emergency requests, prefer `emergency_guide_tool`.
    """
    from i18n_support import resolve_foreign_station
    from place_context import extract_place_from_text

    station = resolve_foreign_station(station_query) or station_query
    if user_request:
        hint = resolve_foreign_station(user_request) or extract_place_from_text(user_request)
        if hint and "역" in hint:
            station = hint
    return find_subway_facility(station, facility_type=facility_type, limit=limit)


@mcp.tool(
    description=mcp_description("find_safe_place"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find SafeDream Safety Places",
    }
)
async def find_safe_place(
    place_query: PlaceQuery,
    user_request: OptionalUserRequest = None,
    category: Annotated[
        str,
        Field(description="Safe182 보호시설 유형입니다. child_safety_house 또는 youth를 권장합니다."),
    ] = "child_safety_house",
    radius_m: RadiusM = 1000,
    limit: Limit = 5,
) -> str:
    f"""Safe182 child safety houses and shelters via {SERVICE_DISPLAY}."""
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
    description=mcp_description("find_accessible_facility_tool"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find Accessible Facility",
    }
)
async def find_accessible_facility_tool(
    place_query: PlaceQuery,
    user_request: OptionalUserRequest = None,
    facility_id: Annotated[
        str | None,
        Field(description="장애인 편의시설 유형 ID입니다. 모르면 비워두세요. 휠체어 화장실은 user_request/place_query로 표현해도 됩니다."),
    ] = None,
    include_subway: Annotated[bool, Field(description="주변 지하철 접근성 시설도 함께 포함할지 여부입니다.")] = True,
    limit: Limit = 5,
) -> str:
    f"""Wheelchair restrooms and disabled-access facilities via {SERVICE_DISPLAY}.

    Single-intent accessibility tool. For mixed requests with medical/safety intents,
    use `emergency_guide_tool`.
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
    description=mcp_description("find_outdoor_service_tool"),
    annotations={
        **TOOL_ANNOTATIONS,
        "title": "Find ATM WiFi Or Vet Hospital",
    }
)
async def find_outdoor_service_tool(
    place_query: PlaceQuery,
    user_request: OptionalUserRequest = None,
    service: Annotated[
        str,
        Field(description="찾을 생활 편의 서비스입니다. atm, wifi, vet_hospital, animal_pharmacy, bus_stop 중 하나를 권장합니다."),
    ] = "atm",
    station_query: Annotated[
        str | None,
        Field(description="역 기반 서비스가 필요할 때만 역명 또는 정류장 힌트를 넣습니다. 예: 강남역, 서울역."),
    ] = None,
    wheelchair_accessible: Annotated[bool, Field(description="휠체어 접근 가능 시설을 우선할지 여부입니다.")] = False,
    limit: Limit = 5,
) -> str:
    f"""ATM, WiFi, vet hospitals, animal pharmacies, bus stops via {SERVICE_DISPLAY}.

    Use `service=vet_hospital` for animal emergency. For mixed intents, use
    `emergency_guide_tool` to orchestrate multiple tools.
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


register_map_routes(mcp)
install_tool_error_wrapping(mcp)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
