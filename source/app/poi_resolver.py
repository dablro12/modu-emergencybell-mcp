"""Dynamic POI resolution via Kakao Local keyword search (no static landmark table)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from kakao_local import _coords_from_document, extract_admin_from_document, search_keyword
from landmarks import strip_poi_noise
from region_parse import normalize_place_query

_STATION_SUFFIX = re.compile(r"역$")


@dataclass(frozen=True)
class DynamicPoi:
    query: str
    place_name: str
    latitude: float
    longitude: float
    sido: str = ""
    sigungu: str = ""
    dong: str = ""
    road_address: str = ""
    category: str = ""
    source: str = "kakao_poi"


def _normalize_label(text: str) -> str:
    return normalize_place_query(text).strip().lower()


def _score_document(doc: dict[str, Any], query: str) -> float:
    place_name = (doc.get("place_name") or "").strip()
    if not place_name:
        return -1.0

    query_norm = _normalize_label(query)
    place_norm = _normalize_label(place_name)
    if not query_norm:
        return -1.0

    score = 0.0
    if query_norm == place_norm:
        score += 120.0
    elif place_norm.startswith(query_norm):
        score += 90.0
    elif query_norm in place_norm:
        score += 70.0
    elif place_norm in query_norm:
        score += 50.0
    else:
        return -1.0

    category = (doc.get("category_name") or "")
    wants_station = "역" in query or "station" in query_norm
    is_station = "역" in place_name or "지하철" in category
    if wants_station and is_station:
        score += 25.0
    elif not wants_station and is_station and _STATION_SUFFIX.search(place_name):
        score -= 35.0

    if "궁" in query and "궁" in place_name and not _STATION_SUFFIX.search(place_name):
        score += 30.0
    if any(token in category for token in ("관광", "문화", "명소", "유적", "박물관")):
        score += 15.0

    distance = doc.get("distance")
    if distance not in (None, ""):
        try:
            score -= min(float(distance) / 1000.0, 20.0)
        except (TypeError, ValueError):
            pass
    return score


def _looks_like_poi_query(query: str) -> bool:
    text = (query or "").strip()
    if not text or len(text) < 2:
        return False
    if text.endswith(("동", "구", "군", "시", "도")) and "역" not in text:
        return False
    if any(ch.isdigit() for ch in text) and any(
        token in text for token in ("로", "길", "번지", "아파트")
    ):
        return False
    return True


async def resolve_dynamic_poi(query: str) -> DynamicPoi | None:
    """Resolve a landmark/POI name to coordinates using Kakao keyword search."""
    stripped = strip_poi_noise(query) or (query or "").strip()
    if not _looks_like_poi_query(stripped):
        return None

    documents = await search_keyword(stripped, size=10)
    if not documents:
        return None

    scored = [(doc, _score_document(doc, stripped)) for doc in documents]
    scored = [(doc, score) for doc, score in scored if score >= 40.0]
    if not scored:
        return None

    best_doc, _ = max(scored, key=lambda item: item[1])
    coords = _coords_from_document(best_doc)
    if not coords:
        return None

    lat, lng = coords
    sido, sigungu, dong = extract_admin_from_document(best_doc)
    road_address = (best_doc.get("road_address_name") or best_doc.get("address_name") or "").strip()
    return DynamicPoi(
        query=stripped,
        place_name=(best_doc.get("place_name") or stripped).strip(),
        latitude=lat,
        longitude=lng,
        sido=sido,
        sigungu=sigungu,
        dong=dong,
        road_address=road_address,
        category=(best_doc.get("category_name") or "").strip(),
    )
