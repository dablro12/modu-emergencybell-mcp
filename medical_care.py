"""의원·약국·응급실 통합 조회 (NEMC)."""

from __future__ import annotations

from nemc_client import (
    find_emergency_rooms_near,
    find_open_clinics_near,
    find_open_pharmacies_near,
)
from outdoor_services import find_outdoor_service
from place_context import is_pet_care_query, normalize_specialty


async def find_medical_care(
    *,
    place_query: str,
    user_request: str | None = None,
    care_type: str = "all",
    specialty: str = "general",
    treatment_day: str | None = None,
    pharmacy_name: str | None = None,
    limit: int = 5,
) -> str:
    combined = " ".join(part for part in (user_request or "", place_query) if part)
    if is_pet_care_query(combined):
        return (
            "⚠️ 반려동물 진료는 사람 의료기관이 아닙니다.\n\n"
            + await find_outdoor_service(place_query=place_query, service="vet_hospital", limit=limit)
        )

    kind = (care_type or "all").strip().lower()
    specialty = normalize_specialty(specialty)
    sections: list[str] = [f"## 의료기관 안내 — {place_query}", ""]

    if kind in ("all", "emergency", "emergency_room", "er"):
        sections.append(await find_emergency_rooms_near(place_query=place_query, limit=limit))
    if kind in ("all", "clinic", "hospital"):
        sections.append(
            await find_open_clinics_near(
                place_query=place_query,
                specialty=specialty,
                treatment_day=treatment_day,
                limit=limit,
            )
        )
    if kind in ("all", "pharmacy"):
        sections.append(
            await find_open_pharmacies_near(
                place_query=place_query,
                treatment_day=treatment_day,
                pharmacy_name=pharmacy_name,
                limit=limit,
            )
        )

    return "\n\n---\n\n".join(s for s in sections if s.strip())
