"""장애인 편의시설 API + 주변 접근성 통합 조회."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from helpers import haversine_m, search_records, search_restrooms_by_query
from kakao_local import geocode_place
from region_parse import parse_place_query, region_full_prefix
from subway_facility import find_subway_facility

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY", "")
BASE_URL = "https://apis.data.go.kr/B554287/DisabledPersonConvenientFacility"
DETAIL_PATH = "getFacInfoOpenApiJpEvalInfoList"
LIST_PATH = "getDisConvFaclList"


def _require_key() -> str:
    if not SERVICE_KEY:
        raise ValueError("DATA_GO_KR_SERVICE_KEY is not set")
    return SERVICE_KEY


def _parse_detail(xml_text: str) -> dict[str, str] | None:
    root = ET.fromstring(xml_text)
    code = root.findtext(".//resultCode", "")
    if code not in ("0", "00", ""):
        serv = root.find(".//servList")
        if serv is None:
            return None
    else:
        serv = root.find(".//servList")
        if serv is None and code not in ("0", "00", ""):
            return None
    if serv is None:
        return None
    return {
        "faclNm": (serv.findtext("faclNm") or "").strip(),
        "evalInfo": (serv.findtext("evalInfo") or "").strip(),
        "wfcltId": (serv.findtext("srvInstId") or serv.findtext("wfcltId") or "").strip(),
    }


def _parse_list_rows(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    rows: list[dict[str, Any]] = []
    for serv in root.findall(".//servList"):
        lat_raw = serv.findtext("faclLat") or ""
        lng_raw = serv.findtext("faclLng") or ""
        try:
            lat = float(lat_raw) if lat_raw and float(lat_raw) != 0 else None
            lng = float(lng_raw) if lng_raw and float(lng_raw) != 0 else None
        except ValueError:
            lat, lng = None, None
        row = {
            "faclNm": (serv.findtext("faclNm") or "").strip(),
            "faclTyCd": (serv.findtext("faclTyCd") or "").strip(),
            "lcMnad": (serv.findtext("lcMnad") or "").strip(),
            "wfcltId": (serv.findtext("wfcltId") or "").strip(),
            "salStaNm": (serv.findtext("salStaNm") or "").strip(),
            "latitude": lat,
            "longitude": lng,
        }
        if row["faclNm"] or row["wfcltId"]:
            rows.append(row)
    return rows


def _search_name(place_query: str) -> str:
    text = place_query.strip()
    for suffix in ("역", " 지하철역", " subway station"):
        if text.endswith(suffix):
            return text[: -len(suffix)] or text
    tokens = [t for t in text.replace(",", " ").split() if len(t) >= 2]
    return tokens[-1] if tokens else text


def _matches_region(address: str, region_prefix: str) -> bool:
    if not region_prefix:
        return True
    return region_prefix.replace(" ", "") in address.replace(" ", "")


async def _fetch_detail(facility_id: str) -> dict[str, str] | None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/{DETAIL_PATH}",
            params={"serviceKey": _require_key(), "wfcltId": facility_id},
        )
        response.raise_for_status()
        return _parse_detail(response.text)


async def _search_disabled_facilities(
    *,
    place_query: str,
    limit: int,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[dict[str, Any]]:
    sido, sigungu = parse_place_query(place_query)
    region_prefix = region_full_prefix(sido, sigungu)
    search_name = _search_name(place_query)

    params: dict[str, Any] = {
        "serviceKey": _require_key(),
        "pageNo": 1,
        "numOfRows": min(max(limit * 4, 10), 50),
        "faclNm": search_name,
    }
    if sido:
        params["ctpvNm"] = sido

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/{LIST_PATH}", params=params)
        response.raise_for_status()
        rows = _parse_list_rows(response.text)

    if region_prefix:
        filtered = [row for row in rows if _matches_region(row.get("lcMnad", ""), region_prefix)]
        if filtered:
            rows = filtered

    if latitude is not None and longitude is not None:
        for row in rows:
            if row.get("latitude") is not None and row.get("longitude") is not None:
                row["distance_m"] = int(
                    haversine_m(latitude, longitude, row["latitude"], row["longitude"])
                )
            else:
                row["distance_m"] = None
        with_dist = [r for r in rows if r.get("distance_m") is not None]
        if with_dist:
            rows = sorted(with_dist, key=lambda r: r["distance_m"]) + [
                r for r in rows if r.get("distance_m") is None
            ]

    return rows[:limit]


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

    coords = await geocode_place(place_query)
    lat, lng = (coords[0], coords[1]) if coords else (None, None)

    lines = [f"## 접근성·편의시설 — {place_query}", ""]
    if coords:
        lines.append(f"- 기준 좌표: {lat:.6f}, {lng:.6f}")
        lines.append("")

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
        for row in restrooms:
            dist = row.get("distance_m")
            dist_text = f" · 약 {dist}m" if dist is not None else ""
            lines.append(f"- **{row['name']}**{dist_text}")
            lines.append(f"  - {row['road_address'] or row['jibun_address']}")
        lines.append("")

    disabled_rows = await _search_disabled_facilities(
        place_query=place_query,
        limit=limit,
        latitude=lat,
        longitude=lng,
    )
    if disabled_rows:
        lines.append(f"### 장애인 편의시설 ({len(disabled_rows)}건)")
        for row in disabled_rows:
            dist = row.get("distance_m")
            dist_text = f" · 약 {dist}m" if dist is not None else ""
            lines.append(f"- **{row.get('faclNm', '시설')}**{dist_text}")
            if row.get("faclTyCd"):
                lines.append(f"  - 유형: {row['faclTyCd']}")
            if row.get("lcMnad"):
                lines.append(f"  - {row['lcMnad']}")
            if row.get("wfcltId"):
                lines.append(f"  - ID: `{row['wfcltId']}`")
        if disabled_rows[0].get("wfcltId"):
            detail = await _fetch_detail(disabled_rows[0]["wfcltId"])
            if detail and detail.get("evalInfo"):
                lines.append("")
                lines.append(f"**{disabled_rows[0]['faclNm']} 편의시설**: {detail['evalInfo']}")
        lines.append("")

    if len(lines) <= 3:
        if coords:
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

    if len(lines) <= 3:
        return (
            f"'{place_query}' 근처 접근성 시설을 찾지 못했습니다.\n"
            "- 지하철역이면 `find_subway_facility`도 시도해 보세요.\n"
            "- 시설 ID를 알면 `facility_id`로 상세 조회 가능합니다."
        )

    lines.append("_출처: 행정안전부 공중화장실 · 지하철 편의시설 · 한국사회보장정보원_")
    return "\n".join(lines).strip()
