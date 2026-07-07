"""공공데이터포털 JSON API (무료 WiFi, 동물병원)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from kakao_local import geocode_place
from landmarks import resolve_landmark_poi
from region_parse import parse_place_query

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY", "")
WIFI_BASE = "https://apis.data.go.kr/1741000/free_wifi_info/info"
VET_BASE = "https://apis.data.go.kr/1741000/animal_hospitals/info"


def _require_key() -> str:
    if not SERVICE_KEY:
        raise ValueError("DATA_GO_KR_SERVICE_KEY is not set")
    return SERVICE_KEY


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload.get("response", {}).get("body", {})
    items = body.get("items", {})
    if not items:
        return []
    item = items.get("item")
    if item is None:
        return []
    if isinstance(item, list):
        return item
    return [item]


async def _fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params={"serviceKey": _require_key(), **params})
        if response.status_code == 401:
            raise RuntimeError("공공데이터 API 401 — 인증키 또는 활용신청을 확인하세요.")
        response.raise_for_status()
        return response.json()


def _wifi_matches_region(row: dict[str, Any], sido: str, sigungu: str) -> bool:
    addr = str(row.get("LCTN_ROAD_NM_ADDR") or row.get("LCTN_LOTNO_ADDR") or "")
    blob = addr.replace(" ", "")
    if sigungu and sigungu.replace(" ", "") in blob:
        return True
    if sido and sido[:2] in blob:
        return True
    return not sido and not sigungu


async def search_free_wifi(
    *,
    place_query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    from place_resolver import resolve_place_context

    ctx = await resolve_place_context(place_query)
    sido, sigungu = ctx.sido or "", ctx.sigungu or ""
    if not sigungu:
        parsed_sido, parsed_sigungu = parse_place_query(place_query)
        sido = sido or parsed_sido
        sigungu = sigungu or parsed_sigungu

    poi = resolve_landmark_poi(place_query)
    if poi and not sigungu:
        _, region, _ = poi
        parsed_sido, parsed_sigungu = parse_place_query(region)
        sido = sido or parsed_sido
        sigungu = sigungu or parsed_sigungu

    search_terms: list[str] = []
    if sigungu:
        search_terms.append(sigungu)
        short = sigungu.replace("구", "").replace("군", "")
        if short and short != sigungu:
            search_terms.append(short)
    if sido:
        search_terms.append(sido[:2])
    if poi:
        _, _, keyword = poi
        if keyword not in search_terms:
            search_terms.append(keyword)
    if not search_terms:
        search_terms.append(place_query.strip()[:20])

    seen: set[str] = set()
    all_rows: list[dict[str, Any]] = []
    for term in search_terms:
        params: dict[str, Any] = {
            "pageNo": 1,
            "numOfRows": min(max(limit * 4, 20), 100),
            "returnType": "json",
            "cond[LCTN_ROAD_NM_ADDR::LIKE]": term,
        }
        data = await _fetch_json(WIFI_BASE, params)
        for row in _items(data):
            dedupe_key = f"{row.get('INSTL_PLC_NM', '')}|{row.get('LCTN_ROAD_NM_ADDR', '')}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            all_rows.append(row)

    if sido or sigungu:
        filtered = [row for row in all_rows if _wifi_matches_region(row, sido, sigungu)]
        if filtered:
            all_rows = filtered

    return all_rows[:limit]


async def search_vet_hospitals(
    *,
    place_query: str,
    hospital_name: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "pageNo": 1,
        "numOfRows": min(max(limit, 10), 100),
        "returnType": "json",
    }
    data = await _fetch_json(VET_BASE, params)
    items = _items(data)

    tokens = [t.lower() for t in place_query.replace(",", " ").split() if len(t) >= 2]
    if hospital_name:
        tokens.append(hospital_name.lower())

    def matches(row: dict[str, Any]) -> bool:
        blob = " ".join(
            str(row.get(k, ""))
            for k in ("ROAD_NM_ADDR", "LOTNO_ADDR", "BPLC_NM", "TELNO", "LCTN_AREA")
        ).lower()
        if not tokens:
            return True
        return any(tok in blob for tok in tokens)

    filtered = [row for row in items if matches(row)]
    return (filtered or items)[:limit]


def format_wifi_list(rows: list[dict[str, Any]], *, query: str) -> str:
    if not rows:
        return f"'{query}' 근처 무료 와이파이 정보를 찾지 못했습니다."

    lines = [f"## 무료 와이파이 — {query}", ""]
    for idx, row in enumerate(rows, start=1):
        name = row.get("INSTL_PLC_NM") or row.get("INSTL_FCLT_SE_NM") or "시설"
        addr = row.get("LCTN_ROAD_NM_ADDR") or row.get("LCTN_LOTNO_ADDR") or ""
        ssid = row.get("WIFI_SSID") or row.get("WIFI_NM") or "정보없음"
        lines.append(f"### {idx}. {name}")
        lines.append(f"- **주소**: {addr}")
        lines.append(f"- **WiFi**: {ssid}")
        if row.get("OPN_ATMY_GRP_NM"):
            lines.append(f"- **관리**: {row['OPN_ATMY_GRP_NM']}")
        lines.append("")
    lines.append("_출처: 행정안전부 무료와이파이정보_")
    return "\n".join(lines).strip()


def format_vet_list(rows: list[dict[str, Any]], *, query: str) -> str:
    if not rows:
        return f"'{query}' 근처 동물병원을 찾지 못했습니다."

    lines = [
        f"## 동물병원 — {query}",
        "⚠️ 응급·야간 진료 여부는 **병원에 전화 확인**하세요.",
        "",
    ]
    for idx, row in enumerate(rows, start=1):
        name = row.get("BPLC_NM") or row.get("ANIMAL_HSP_NM") or "동물병원"
        addr = row.get("ROAD_NM_ADDR") or row.get("LOTNO_ADDR") or row.get("LCTN_ROAD_NM_ADDR") or ""
        tel = row.get("TELNO") or row.get("ANIMAL_HSP_TLNO") or ""
        lines.append(f"### {idx}. {name}")
        lines.append(f"- **주소**: {addr}")
        if tel:
            lines.append(f"- **전화**: {tel}")
        lines.append("")
    lines.append("_출처: 행정안전부 동물병원 조회서비스_")
    return "\n".join(lines).strip()


async def resolve_coords(place_query: str) -> tuple[float, float] | None:
    try:
        return await geocode_place(place_query)
    except (ValueError, OSError):
        return None
