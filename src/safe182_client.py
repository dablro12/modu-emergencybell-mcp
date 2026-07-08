"""경찰청 안전Dream Open API — 안전지도."""

from __future__ import annotations

import os
from math import cos, radians
from typing import Any
from urllib.parse import urlencode

import httpx

from helpers import haversine_m
from kakao_local import geocode_place

AUTH_ID = os.getenv("SAFE182_AUTH_ID", "")
AUTH_KEY = os.getenv("SAFE182_AUTH_KEY", "")
SAFE_MAP_URL = "https://www.safe182.go.kr/api/lcm/safeMap.do"

CATEGORY_ALIASES = {
    "child_safety_house": "09",
    "아동안전지킴이집": "09",
    "child": "09",
    "elderly": "23",
    "노인보호시설": "23",
    "child_welfare": "22",
    "아동보호시설": "22",
    "crime_area": "20",
    "우범지역": "20",
    "youth": "17",
    "청소년지원시설": "17",
    "youth_shelter": "17",
    "청소년쉼터": "17",
    "violence_support": "18",
    "원스톱지원센터": "18",
    "all": "09,17,22,23",
}


def _require_auth() -> tuple[str, str]:
    auth_id = os.getenv("SAFE182_AUTH_ID", AUTH_ID)
    auth_key = os.getenv("SAFE182_AUTH_KEY", AUTH_KEY)
    if not auth_id or not auth_key:
        raise ValueError("SAFE182_AUTH_ID / SAFE182_AUTH_KEY is not set")
    return auth_id, auth_key


def normalize_category(value: str) -> list[str]:
    key = value.strip()
    mapped = CATEGORY_ALIASES.get(key, CATEGORY_ALIASES.get(key.lower(), key))
    if mapped == "09,17,22,23":
        return ["09", "17", "22", "23"]
    return [mapped]


def _bbox(lat: float, lng: float, radius_m: int = 1000) -> dict[str, str]:
    delta = radius_m / 111_000
    cos_lat = max(abs(cos(radians(lat))), 0.01)
    delta_lng = radius_m / (111_000 * cos_lat)
    return {
        "minY": f"{lat - delta:.6f}",
        "maxY": f"{lat + delta:.6f}",
        "minX": f"{lng - delta_lng:.6f}",
        "maxX": f"{lng + delta_lng:.6f}",
    }


def _admin_center_query(place_query: str) -> str | None:
    text = (place_query or "").strip()
    if not text:
        return None

    if text in {"서울", "서울시", "서울특별시"}:
        return "서울시청"
    if text in {"부산", "부산시", "부산광역시"}:
        return "부산시청"

    parts = text.split()
    last = parts[-1]
    if len(parts) > 1 and parts[1].endswith(("구", "군", "시")):
        sido = parts[0]
        if sido.endswith(("특별시", "광역시", "특별자치시", "특별자치도")):
            sido = sido[:2]
        return f"{sido} {parts[1]}청"

    if last.endswith(("구", "군")):
        if len(parts) > 1:
            sido = parts[0]
            if sido.endswith(("특별시", "광역시", "특별자치시", "특별자치도")):
                sido = sido[:2]
            return f"{sido} {last}청"
        return f"{last}청"
    if last.endswith("시"):
        return f"{last}청"
    return None


async def search_safe_places(
    *,
    place_query: str,
    category: str = "child_safety_house",
    radius_m: int = 1000,
    limit: int = 5,
) -> str:
    coords = await geocode_place(place_query)
    if not coords:
        fallback_query = _admin_center_query(place_query)
        if fallback_query:
            coords = await geocode_place(fallback_query)

    if not coords:
        return f"'{place_query}' 위치를 찾지 못했습니다. 역·구 이름으로 다시 시도해 주세요."

    lat, lng = coords
    auth_id, auth_key = _require_auth()
    categories = normalize_category(category)

    data: list[tuple[str, str]] = [
        ("esntlId", auth_id),
        ("authKey", auth_key),
        ("pageIndex", "1"),
        ("pageUnit", str(min(limit, 100))),
    ]
    for code in categories:
        data.append(("clArray", code))
    for key, value in _bbox(lat, lng, radius_m).items():
        data.append((key, value))

    form = urlencode(data, doseq=True)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SAFE_MAP_URL,
            content=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        payload = response.json()

    items = payload.get("list") or []
    for item in items:
        try:
            item_lat = float(item.get("lcinfoLa", 0))
            item_lng = float(item.get("lcinfoLo", 0))
            item["distance_m"] = int(haversine_m(lat, lng, item_lat, item_lng))
        except (TypeError, ValueError):
            item["distance_m"] = None

    items.sort(key=lambda row: row.get("distance_m") if row.get("distance_m") is not None else 10**9)
    items = items[:limit]

    if not items:
        return (
            f"'{place_query}' 반경 {radius_m}m 내 안전시설을 찾지 못했습니다.\n"
            "- category: child_safety_house, elderly, youth, child_welfare, crime_area, violence_support, all"
        )

    lines = [
        f"## 안전Dream 안전지도 — {place_query}",
        f"- 기준 좌표: {lat:.6f}, {lng:.6f}",
        "⚠️ 실종·위급 상황은 **112** 또는 **안전Dream 182**로 직접 신고하세요.",
        "",
    ]
    for idx, item in enumerate(items, start=1):
        name = item.get("bsshNm") or "시설"
        dist = item.get("distance_m")
        dist_text = f" · 약 {dist}m" if dist is not None else ""
        lines.append(f"### {idx}. {name}{dist_text}")
        lines.append(f"- **유형**: {item.get('clNm', item.get('cl', ''))}")
        lines.append(f"- **주소**: {item.get('adres', '')}")
        if item.get("telno"):
            lines.append(f"- **전화**: {item['telno']}")
        lines.append("")

    lines.append("_출처: 경찰청 안전Dream_")
    return "\n".join(lines).strip()
