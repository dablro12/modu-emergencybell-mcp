"""ATM·무료 WiFi·동물병원·동물약국 통합 조회."""

from __future__ import annotations

from animal_facility import find_animal_facilities_near, load_index
from bus_stop import find_bus_stops_near
from datago_json_client import (
    format_vet_list,
    format_wifi_list,
    search_free_wifi,
    search_vet_hospitals,
)
from subway_atm import search_subway_atms

SERVICE_ALIASES = {
    "atm": "atm",
    "cash": "atm",
    "bank": "atm",
    "wifi": "wifi",
    "wi-fi": "wifi",
    "internet": "wifi",
    "vet": "vet_hospital",
    "veterinary": "vet_hospital",
    "animal": "vet_hospital",
    "animal_hospital": "vet_hospital",
    "동물병원": "vet_hospital",
    "animal_pharmacy": "animal_pharmacy",
    "vet_pharmacy": "animal_pharmacy",
    "pet_pharmacy": "animal_pharmacy",
    "동물약국": "animal_pharmacy",
    "와이파이": "wifi",
    "bus_stop": "bus_stop",
    "bus": "bus_stop",
    "버스": "bus_stop",
    "버스정류장": "bus_stop",
    "정류장": "bus_stop",
    "정류소": "bus_stop",
    "storage": "locker",
    "luggage_storage": "locker",
    "luggage": "locker",
    "locker": "locker",
    "보관함": "locker",
    "물품보관함": "locker",
    "캐리어": "locker",
}


def normalize_service(value: str) -> str:
    key = value.strip().lower()
    return SERVICE_ALIASES.get(key, key)


async def find_outdoor_service(
    *,
    place_query: str,
    service: str = "atm",
    station_query: str | None = None,
    wheelchair_accessible: bool = False,
    limit: int = 5,
) -> str:
    kind = normalize_service(service)
    if kind == "atm":
        return await search_subway_atms(
            place_query=place_query,
            station_query=station_query,
            limit=limit,
        )
    if kind == "wifi":
        rows = await search_free_wifi(place_query=place_query, limit=limit)
        return format_wifi_list(rows, query=place_query)
    if kind in ("subway_locker", "locker"):
        from place_resolver import resolve_place_context
        from subway_facility import find_subway_facility

        station = station_query or place_query
        ctx = await resolve_place_context(station)
        return find_subway_facility(
            ctx.expanded_query or station,
            facility_type="locker",
            limit=limit,
        )
    if kind == "vet_hospital":
        if (load_index("hospital").get("records") or []):
            return await find_animal_facilities_near(
                place_query=place_query,
                kind="hospital",
                limit=limit,
            )
        rows = await search_vet_hospitals(place_query=place_query, limit=limit)
        return format_vet_list(rows, query=place_query)
    if kind == "animal_pharmacy":
        if (load_index("pharmacy").get("records") or []):
            return await find_animal_facilities_near(
                place_query=place_query,
                kind="pharmacy",
                limit=limit,
            )
        return (
            f"'{place_query}' 근처 동물약국 로컬 색인이 없습니다.\n"
            "- 가까운 **동물병원**(`service=vet_hospital`)에 문의하세요.\n"
            "- 사람 약국은 `find_open_pharmacy`입니다."
        )
    if kind == "bus_stop":
        return await find_bus_stops_near(
            place_query=place_query,
            stop_name=station_query,
            radius_m=800,
            limit=limit,
        )

    return (
        f"지원하지 않는 service 값: `{service}`\n"
        "- `atm`: ATM/현금인출\n"
        "- `wifi`: 무료 와이파이\n"
        "- `vet_hospital`: 동물병원 (강아지·고양이·반려동물 — 사람 응급실 아님)\n"
        "- `animal_pharmacy`: 동물약국\n"
        "- `bus_stop`: 버스정류장"
    )
