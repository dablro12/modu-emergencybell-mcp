"""자연어 통합 비상 안내 — 의도 분류·지역 보정·다중 Tool 연계."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from accessible_facility_client import find_accessible_facility
from helpers import format_restroom_list, search_restrooms_by_query
from hotlines import format_emergency_hotlines
from nemc_client import (
    find_emergency_rooms_near,
    find_open_clinics_near,
    find_open_pharmacies_near,
    parse_treatment_day,
)
from crime_stats import crime_stats_for_place
from veteran_hospital import find_veteran_hospitals_near
from outdoor_services import find_outdoor_service
from place_context import (
    classify_intents,
    infer_specialty,
    infer_user_type_from_text,
    normalize_situation_tag,
)
from intent_routing import resolve_effective_place
from phrases import format_phrase_card
from safe182_client import search_safe_places
from safety_bell import find_safety_bells_near
from health_triage import health_triage
from subway_facility import find_subway_facility

GUIDE_HEADER = (
    "## 모두의비상벨 통합 안내\n"
    "_자연어 질문을 분석해 아래 도구를 자동 연결했습니다. "
    "세부 조회는 개별 Tool도 사용할 수 있습니다._\n"
)


async def _resolve_place(user_request: str, place_query: str | None) -> "PlaceContext":
    from place_resolver import PlaceContext

    _effective, ctx = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback="서울",
    )
    return ctx


async def emergency_guide(
    user_request: str,
    place_query: str | None = None,
    language: str = "ko",
) -> str:
    """자연어 요청을 해석해 적절한 비상·생활 안내를 한 번에 반환."""
    place_ctx = await _resolve_place(user_request, place_query)
    place = place_ctx.expanded_query or place_ctx.query
    intents = classify_intents(user_request)
    sections: list[str] = [GUIDE_HEADER, f"**질문**: {user_request.strip()}", f"**기준 지역**: {place}", ""]
    if place_ctx.warning:
        sections.append(f"_{place_ctx.warning}_")
        sections.append("")

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    qt, time_note = parse_treatment_day(None, kst=now)

    if "hotlines" in intents or any(
        k in user_request for k in ("실종", "가스", "119", "112", "신고")
    ):
        situation = None
        if "실종" in user_request:
            situation = "police"
        elif "가스" in user_request:
            situation = "utility_gas"
        sections.append(
            format_emergency_hotlines(
                user_request,
                situation=normalize_situation_tag(situation),
                language=language if language in ("ko", "en") else "ko",
            )
        )

    if "restroom" in intents:
        user_type = infer_user_type_from_text(user_request) or "general"
        rows, coords = await search_restrooms_by_query(
            query=place,
            radius=500,
            user_type=user_type if user_type != "general" else None,
            open_now=False,
            limit=5,
        )
        sections.append(format_restroom_list(rows, query=place, coords_hint=coords))

    if "crime_stats" in intents:
        crime_text = await crime_stats_for_place(
            place_query=place,
            sido=place_ctx.sido,
            sigungu=place_ctx.sigungu,
        )
        if crime_text:
            sections.append(crime_text)
        else:
            sections.append(
                f"**{place}** 지역의 범죄 통계를 찾지 못했습니다.\n"
                "- **시·군·구** 단위로 다시 말씀해 주세요 (예: `서울 강남구`, `부산 해운대구`)."
            )

    if "veteran_hospital" in intents:
        sections.append(await find_veteran_hospitals_near(place_query=place, limit=5))

    if "safety_bell" in intents:
        sections.append(await find_safety_bells_near(place_query=place, radius_m=500, limit=5))

    if "health_triage" in intents:
        sections.append(await health_triage(user_request, place_query=place, language=language))

    if "clinic" in intents and "health_triage" not in intents:
        specialty = infer_specialty(user_request)
        if specialty == "vet":
            sections.append(
                await find_outdoor_service(place_query=place, service="vet_hospital", limit=5)
            )
        elif specialty == "veteran":
            sections.append(await find_veteran_hospitals_near(place_query=place, limit=5))
        else:
            clinic_text = await find_open_clinics_near(
                place_query=place,
                specialty=specialty,
                treatment_day=qt,
                limit=5,
            )
            sections.append(clinic_text)
            if time_note:
                sections.append(f"_{time_note}_")

    if ("pharmacy" in intents or (
        "clinic" in intents and any(k in user_request for k in ("39도", "열", "fever"))
    )) and "health_triage" not in intents:
        sections.append(
            await find_open_pharmacies_near(
                place_query=place,
                treatment_day=qt,
                limit=5,
            )
        )

    if ("emergency_room" in intents or (
        "clinic" in intents and any(k in user_request for k in ("39도", "응급", "emergency"))
    )) and "health_triage" not in intents:
        sections.append(await find_emergency_rooms_near(place_query=place, limit=5))

    if "subway_locker" in intents:
        station = place if "역" in place else f"{place.split()[-1]}역" if place else place
        sections.append(find_subway_facility(station, facility_type="locker", limit=5))

    if "accessible" in intents:
        sections.append(
            await find_accessible_facility(
                place_query=place,
                facility_id=None,
                include_subway=True,
                limit=5,
            )
        )

    if "atm" in intents:
        station_q = place if "역" in place else None
        sections.append(
            await find_outdoor_service(
                place_query=place,
                service="atm",
                station_query=station_q,
                limit=5,
            )
        )

    if "wifi" in intents:
        sections.append(await find_outdoor_service(place_query=place, service="wifi", limit=5))

    if "bus_stop" in intents:
        stop_hint = None
        for token in ("정류장", "정류소"):
            if token in user_request:
                stop_hint = user_request
                break
        sections.append(
            await find_outdoor_service(
                place_query=place,
                service="bus_stop",
                station_query=stop_hint,
                limit=5,
            )
        )

    if "vet" in intents and "clinic" not in intents:
        sections.append(
            await find_outdoor_service(place_query=place, service="vet_hospital", limit=5)
        )
    if "vet_pharmacy" in intents:
        sections.append(
            await find_outdoor_service(place_query=place, service="animal_pharmacy", limit=5)
        )

    if "safe_place" in intents or "실종" in user_request:
        category = "child_safety_house"
        if "청소년" in user_request or "쉼터" in user_request:
            category = "youth"
        sections.append(
            await search_safe_places(
                place_query=place,
                category=category,
                radius_m=1000,
                limit=5,
            )
        )

    if "phrase" in intents:
        sections.append(format_phrase_card(scenario="hospital", language="en"))

    body = "\n\n---\n\n".join(s for s in sections if s and s.strip())
    if len(sections) <= 4:
        body += (
            "\n\n---\n\n_구체적 조회가 필요하면 `find_nearest_restroom`, "
            "`find_medical_care`, `health_triage_tool`, `find_subway_facility_tool` 등 개별 Tool을 사용하세요._"
        )
    return body
