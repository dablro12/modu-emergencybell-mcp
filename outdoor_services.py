"""ATM·무료 WiFi·동물병원 통합 조회."""

from __future__ import annotations

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
    "동물병원": "vet_hospital",
    "와이파이": "wifi",
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
    if kind in ("subway_locker", "locker", "luggage", "luggage_storage", "물품보관함"):
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
        rows = await search_vet_hospitals(place_query=place_query, limit=limit)
        return format_vet_list(rows, query=place_query)

    return (
        f"지원하지 않는 service 값: `{service}`\n"
        "- `atm`: ATM/현금인출\n"
        "- `wifi`: 무료 와이파이\n"
        "- `vet_hospital`: 동물병원"
    )
