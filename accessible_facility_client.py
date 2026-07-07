"""장애인 편의시설 API + 주변 접근성 통합 조회."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from helpers import search_records, search_restrooms_by_query
from kakao_local import geocode_place
from subway_facility import find_subway_facility

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY", "")
DETAIL_URL = (
    "https://apis.data.go.kr/B554287/DisabledPersonConvenientFacility/"
    "getFacInfoOpenApiJpEvalInfoList"
)
LIST_CANDIDATES = (
    "getFacInfoOpenApiListInfoSearch",
    "getFacInfoOpenApiListSearch",
    "getFacInfoOpenApiSearchList",
)


def _require_key() -> str:
    if not SERVICE_KEY:
        raise ValueError("DATA_GO_KR_SERVICE_KEY is not set")
    return SERVICE_KEY


def _parse_detail(xml_text: str) -> dict[str, str] | None:
    root = ET.fromstring(xml_text)
    code = root.findtext(".//resultCode", "")
    if code != "0":
        return None
    serv = root.find(".//servList")
    if serv is None:
        return None
    return {
        "faclNm": (serv.findtext("faclNm") or "").strip(),
        "evalInfo": (serv.findtext("evalInfo") or "").strip(),
        "wfcltId": (serv.findtext("srvInstId") or serv.findtext("wfcltId") or "").strip(),
    }


def _parse_list(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    code = root.findtext(".//resultCode", "")
    if code not in ("0", "00"):
        return []
    rows: list[dict[str, str]] = []
    for serv in root.findall(".//servList"):
        row = {
            "faclNm": (serv.findtext("faclNm") or "").strip(),
            "evalInfo": (serv.findtext("evalInfo") or "").strip(),
            "wfcltId": (serv.findtext("srvInstId") or serv.findtext("wfcltId") or "").strip(),
            "roadNmAddr": (serv.findtext("roadNmAddr") or serv.findtext("lotnoAddr") or "").strip(),
        }
        if row["faclNm"] or row["wfcltId"]:
            rows.append(row)
    return rows


async def _fetch_detail(facility_id: str) -> dict[str, str] | None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            DETAIL_URL,
            params={"serviceKey": _require_key(), "wfcltId": facility_id},
        )
        response.raise_for_status()
        return _parse_detail(response.text)


async def _search_disabled_facilities(
    *,
    place_query: str,
    limit: int,
) -> list[dict[str, str]]:
    tokens = [t for t in place_query.replace(",", " ").split() if len(t) >= 2]
    search_name = tokens[-1] if tokens else place_query
    params_base = {
        "serviceKey": _require_key(),
        "pageNo": 1,
        "numOfRows": min(limit, 20),
        "faclNm": search_name,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        for operation in LIST_CANDIDATES:
            url = f"https://apis.data.go.kr/B554287/DisabledPersonConvenientFacility/{operation}"
            try:
                response = await client.get(url, params=params_base)
            except httpx.HTTPError:
                continue
            if response.status_code != 200 or "not found" in response.text.lower():
                continue
            rows = _parse_list(response.text)
            if rows:
                return rows[:limit]
    return []


async def find_accessible_facility(
    *,
    place_query: str,
    facility_id: str | None = None,
    include_subway: bool = True,
    limit: int = 5,
) -> str:
    if facility_id:
        detail = await _fetch_detail(facility_id)
        if not detail:
            return f"시설 ID `{facility_id}` 정보를 찾지 못했습니다."
        lines = [
            f"## 장애인 편의시설 — {detail.get('faclNm') or facility_id}",
            f"- **시설 ID**: `{detail.get('wfcltId') or facility_id}`",
            f"- **편의시설**: {detail.get('evalInfo') or '정보없음'}",
            "",
            "_출처: 한국사회보장정보원 장애인편의시설_",
        ]
        return "\n".join(lines)

    lines = [f"## 접근성·편의시설 — {place_query}", ""]

    if include_subway and ("역" in place_query or "지하철" in place_query):
        subway_text = find_subway_facility(place_query, facility_type="accessibility", limit=limit)
        if "찾지 못했습니다" not in subway_text:
            lines.append(subway_text)
            lines.append("")

    restrooms, _ = await search_restrooms_by_query(
        place_query,
        radius=800,
        user_type="wheelchair",
        limit=limit,
    )
    if restrooms:
        lines.append(f"### 장애인 이용 가능 공중화장실 ({len(restrooms)}건)")
        for idx, row in enumerate(restrooms, start=1):
            dist = row.get("distance_m")
            dist_text = f" · 약 {dist}m" if dist is not None else ""
            lines.append(f"- **{row['name']}**{dist_text}")
            lines.append(f"  - {row['road_address'] or row['jibun_address']}")
        lines.append("")

    disabled_rows = await _search_disabled_facilities(place_query=place_query, limit=limit)
    if disabled_rows:
        lines.append(f"### 장애인 편의시설 API ({len(disabled_rows)}건)")
        for idx, row in enumerate(disabled_rows, start=1):
            lines.append(f"- **{row.get('faclNm', '시설')}**")
            if row.get("evalInfo"):
                lines.append(f"  - {row['evalInfo']}")
            if row.get("roadNmAddr"):
                lines.append(f"  - {row['roadNmAddr']}")
            if row.get("wfcltId"):
                lines.append(f"  - ID: `{row['wfcltId']}`")
        lines.append("")

    if len(lines) <= 2:
        coords = await geocode_place(place_query)
        if coords:
            lat, lng = coords
            region_rows = search_records(
                latitude=lat,
                longitude=lng,
                radius_m=800,
                user_type="wheelchair",
                limit=limit,
            )
            if region_rows:
                lines.append(f"### 주변 장애인 화장실 ({len(region_rows)}건)")
                for row in region_rows:
                    lines.append(f"- {row['name']} — {row['road_address'] or row['jibun_address']}")
                lines.append("")

    if len(lines) <= 2:
        return (
            f"'{place_query}' 근처 접근성 시설을 찾지 못했습니다.\n"
            "- 지하철역이면 `find_subway_facility`도 시도해 보세요.\n"
            "- 시설 ID를 알면 `facility_id`로 상세 조회 가능합니다."
        )

    lines.append("_출처: 행정안전부 공중화장실 · 지하철 편의시설 · 한국사회보장정보원_")
    return "\n".join(lines).strip()
