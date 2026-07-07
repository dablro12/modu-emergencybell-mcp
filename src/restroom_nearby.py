"""Kakao Local 근접 검색 + 공공데이터 화장실 레코드 매칭."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from helpers import (
    _matches_open_now,
    _matches_user_type,
    _normalize_user_type,
    haversine_m,
    load_records,
)
from kakao_local import (
    _coords_from_document,
    extract_admin_from_document,
    search_keyword,
)
from region_parse import region_full_prefix, regions_match

_SEARCH_KEYWORDS = ("화장실", "공중화장실", "public toilet", "restroom")
_TOILET_NOISE = re.compile(
    r"(개방)?화장실|공중화장실|화장실\(.*?\)|\d+(?:,\d+)?층|지하\d+층|옥외|실내",
    re.IGNORECASE,
)
_NAME_NOISE = frozenset({"개방", "화장실", "공중", "층", "지하", "옥외", "실내", "남자", "여자", "장애인"})
_MIN_MATCH_SCORE = 55


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip().lower())


def _place_core(place_name: str) -> str:
    return _TOILET_NOISE.sub("", place_name or "").strip(" -·")


def _record_region_prefix(record: dict[str, Any]) -> str:
    region = record.get("region") or {}
    return (region.get("full_prefix") or "").strip()


@lru_cache(maxsize=1)
def _records_by_sigungu() -> dict[str, tuple[dict[str, Any], ...]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for record in load_records():
        prefix = _record_region_prefix(record)
        if not prefix:
            continue
        buckets.setdefault(prefix, []).append(dict(record))
    return {key: tuple(items) for key, items in buckets.items()}


def _candidate_records(*, sido: str = "", sigungu: str = "") -> list[dict[str, Any]]:
    prefix = region_full_prefix(sido, sigungu)
    if not prefix:
        return [dict(record) for record in load_records()]

    matches: list[dict[str, Any]] = []
    for region_prefix, items in _records_by_sigungu().items():
        if regions_match(region_prefix, prefix):
            matches.extend(dict(item) for item in items)
    return matches


def _address_score(doc_road: str, record: dict[str, Any]) -> int:
    norm_doc = _normalize_key(doc_road)
    if not norm_doc:
        return 0

    norm_road = _normalize_key(record.get("road_address") or "")
    norm_jibun = _normalize_key(record.get("jibun_address") or "")

    if norm_doc == norm_road or norm_doc == norm_jibun:
        return 95

    for candidate in (norm_road, norm_jibun):
        if not candidate or len(candidate) < 8:
            continue
        if norm_doc in candidate or candidate in norm_doc:
            return 75
    return 0


def _name_score(place_name: str, record_name: str) -> int:
    core = _place_core(place_name)
    if not core or not record_name:
        return 0

    norm_core = _normalize_key(core)
    norm_rec = _normalize_key(record_name)
    if not norm_core or not norm_rec:
        return 0

    if norm_core == norm_rec:
        return 100
    if norm_core in norm_rec or norm_rec in norm_core:
        shorter = min(len(norm_core), len(norm_rec))
        if shorter >= 4:
            return 85

    core_tokens = {
        token
        for token in re.findall(r"[\w가-힣]+", core)
        if len(token) >= 2 and token not in _NAME_NOISE
    }
    rec_tokens = {
        token
        for token in re.findall(r"[\w가-힣]+", record_name)
        if len(token) >= 2 and token not in _NAME_NOISE
    }
    overlap = core_tokens & rec_tokens
    if overlap:
        return 55 + min(25, 10 * len(overlap))
    return 0


def _match_score(doc: dict[str, Any], record: dict[str, Any]) -> int:
    road = (doc.get("road_address_name") or doc.get("address_name") or "").strip()
    place = (doc.get("place_name") or "").strip()
    return max(_address_score(road, record), _name_score(place, record.get("name") or ""))


def record_from_kakao_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """공공데이터에 없을 때 Kakao POI를 최소 레코드로 변환."""
    road = (doc.get("road_address_name") or "").strip()
    jibun = (doc.get("address_name") or "").strip()
    sido, sigungu, _ = extract_admin_from_document(doc)
    coords = _coords_from_document(doc)
    place = (doc.get("place_name") or "화장실").strip()
    region = {
        "sido": sido,
        "sigungu": sigungu,
        "full_prefix": region_full_prefix(sido, sigungu),
    }
    return {
        "id": f"kakao:{doc.get('id') or place}",
        "local_gov_code": "",
        "category": "kakao_local",
        "name": place,
        "road_address": road,
        "jibun_address": jibun,
        "search_text": " ".join(filter(None, [place, road, jibun])).lower(),
        "region": region,
        "phone": (doc.get("phone") or "").strip(),
        "management_agency": "",
        "opening": {
            "type": "unknown",
            "type_raw": "정보없음",
            "detail": "",
            "is_always_open": False,
            "is_scheduled": False,
            "is_irregular": False,
            "is_closed_type": False,
        },
        "user_types": {
            "tags": ["general"],
            "general": True,
            "wheelchair": False,
            "child": False,
            "infant_care": False,
            "elderly_safety": False,
            "wheelchair_units": 0,
            "child_units": 0,
        },
        "facilities": {
            "male_stalls": 0,
            "male_urinals": 0,
            "female_stalls": 0,
            "wheelchair_male_stall": 0,
            "wheelchair_male_urinal": 0,
            "wheelchair_female_stall": 0,
            "child_male_stall": 0,
            "child_male_urinal": 0,
            "child_female_stall": 0,
            "emergency_bell": False,
            "emergency_bell_location": "",
            "diaper_station": False,
            "diaper_station_location": "",
            "cctv_entrance": False,
            "safety_management_target": False,
            "waste_type": "",
            "ownership_type": "",
        },
        "installed_at": "",
        "data_date": "",
        "updated_at": "",
        "latitude": coords[0] if coords else None,
        "longitude": coords[1] if coords else None,
        "source": "kakao_local",
    }


def match_local_record(
    doc: dict[str, Any],
    *,
    sido: str = "",
    sigungu: str = "",
) -> dict[str, Any] | None:
    """Kakao POI document → 로컬 공중화장실 레코드 (점수 기반)."""
    doc_sido, doc_sigungu, _ = extract_admin_from_document(doc)
    use_sido = doc_sido or sido
    use_sigungu = doc_sigungu or sigungu
    candidates = _candidate_records(sido=use_sido, sigungu=use_sigungu)

    best: dict[str, Any] | None = None
    best_score = 0
    for record in candidates:
        score = _match_score(doc, record)
        if score > best_score:
            best = record
            best_score = score

    if best_score >= _MIN_MATCH_SCORE:
        return best
    return None


def _distance_from_doc(
    doc: dict[str, Any],
    *,
    latitude: float,
    longitude: float,
) -> int | None:
    raw = doc.get("distance")
    if raw not in (None, ""):
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            pass
    coords = _coords_from_document(doc)
    if coords:
        return int(haversine_m(latitude, longitude, coords[0], coords[1]))
    return None


async def search_restrooms_nearby(
    latitude: float,
    longitude: float,
    *,
    radius: int = 500,
    user_type: str | None = None,
    open_now: bool = False,
    limit: int = 10,
    sido: str = "",
    sigungu: str = "",
) -> list[dict[str, Any]]:
    """Kakao keyword 반경 검색 후 공공데이터 레코드와 병합."""
    user_type = _normalize_user_type(user_type)
    docs: list[dict[str, Any]] = []
    for keyword in _SEARCH_KEYWORDS:
        docs = await search_keyword(
            keyword,
            x=longitude,
            y=latitude,
            radius=radius,
            size=15,
        )
        if docs:
            break

    if not docs:
        return []

    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for doc in docs:
        local = match_local_record(doc, sido=sido, sigungu=sigungu)
        record = dict(local) if local else record_from_kakao_doc(doc)
        record_id = str(record.get("id") or "")
        if record_id and record_id in seen_ids:
            continue
        if not _matches_user_type(record, user_type):
            continue
        if not _matches_open_now(record, open_now):
            continue
        distance = _distance_from_doc(doc, latitude=latitude, longitude=longitude)
        if distance is not None:
            record["distance_m"] = distance
        seen_ids.add(record_id)
        results.append(record)

    results.sort(key=lambda item: item.get("distance_m") if item.get("distance_m") is not None else 10**9)
    return results[:limit]
