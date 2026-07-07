"""국립중앙의료원(NEMC) 공공데이터 API 클라이언트."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from kakao_local import coord_to_region
from helpers import haversine_m
from map_preview import append_overview_map, enrich_result_lines
from region_parse import parse_place_query

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY", "")
SERVICE_KEY_ENCODED = os.getenv("DATA_GO_KR_SERVICE_KEY_ENCODED", "")
CLINIC_BASE = "https://apis.data.go.kr/B552657/HsptlAsembySearchService"
ER_BASE = "https://apis.data.go.kr/B552657/ErmctInfoInqireService"
PHARMACY_BASE = "https://apis.data.go.kr/B552657/ErmctInsttInfoInqireService"

PHARMACY_DISCLAIMER = (
    "⚠️ 공공데이터 영업시간 안내이며 **실제 영업 여부는 약국에 전화 확인**하세요."
)

MEDICAL_DISCLAIMER = (
    "⚠️ **면책**: 공공데이터 안내이며 진단·처방이 아닙니다. "
    "**생명이 위협되면 119**를 직접 전화하세요. 병원 도착 전 **1339** 상담 가능."
)

SPECIALTY_CODES = {
    "general": None,
    "pediatric": "D013",
    "소아": "D013",
    "pediatrics": "D013",
    "internal": "D001",
    "internal_medicine": "D001",
    "내과": "D001",
    "외과": "D002",
    "orthopedic": "D004",
    "obgyn": "D005",
    "emergency": "D024",
}


def _require_key() -> str:
    key = (os.getenv("DATA_GO_KR_SERVICE_KEY") or "").strip()
    if not key:
        raise ValueError("DATA_GO_KR_SERVICE_KEY is not set")
    return key


def _service_keys() -> list[str]:
    keys: list[str] = []
    for env_name in ("DATA_GO_KR_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY_ENCODED"):
        value = (os.getenv(env_name) or "").strip()
        if value and value not in keys:
            keys.append(value)
    return keys


def _parse_xml_items(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    code = root.findtext(".//resultCode", "")
    if code and code != "00":
        msg = root.findtext(".//resultMsg", "API error")
        raise RuntimeError(f"NEMC API error {code}: {msg}")
    items: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        row = {child.tag: (child.text or "").strip() for child in item}
        if row:
            items.append(row)
    return items


async def _get_xml(url: str, params: dict[str, Any]) -> list[dict[str, str]]:
    keys = _service_keys()
    if not keys:
        raise ValueError("DATA_GO_KR_SERVICE_KEY is not set")

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=30.0) as client:
        for key in keys:
            response = await client.get(url, params={"serviceKey": key, **params})
            if response.status_code == 403:
                last_error = RuntimeError("API 403 Forbidden — check data.go.kr 활용신청")
                continue
            response.raise_for_status()
            return _parse_xml_items(response.text)

    if last_error:
        raise last_error
    raise RuntimeError("NEMC API request failed")


def _split_region(region_name: str) -> tuple[str, str]:
    parts = region_name.split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return parts[0], ""
    return "", ""


async def resolve_region(
    *,
    place_query: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> tuple[str, str, float | None, float | None]:
    from place_resolver import resolve_place_context

    lat, lng = latitude, longitude
    if place_query:
        ctx = await resolve_place_context(place_query)
        if lat is None and ctx.latitude is not None:
            lat, lng = ctx.latitude, ctx.longitude
        if ctx.sido and ctx.sigungu:
            return ctx.sido, ctx.sigungu, lat, lng

    if lat is not None and lng is not None:
        try:
            region = await coord_to_region(lng, lat)
            if region and region.get("region_name"):
                sido, sigungu = _split_region(region["region_name"])
                return sido, sigungu, lat, lng
        except (ValueError, OSError, Exception):
            pass

    raise ValueError(
        f"지역을 특정하지 못했습니다: `{place_query}`. "
        "**시·구** 또는 **동·역 이름**을 포함해 주세요 (예: `종로구 창신동`, `연산9동`, `강남역`)."
    )


def _qt_for_today(kst: datetime | None = None) -> str:
    now = kst or datetime.now(ZoneInfo("Asia/Seoul"))
    return str(now.weekday() + 1)


DAY_NAME_MAP: dict[str, str] = {
    "월요일": "1",
    "화요일": "2",
    "수요일": "3",
    "목요일": "4",
    "금요일": "5",
    "토요일": "6",
    "일요일": "7",
    "monday": "1",
    "tuesday": "2",
    "wednesday": "3",
    "thursday": "4",
    "friday": "5",
    "saturday": "6",
    "sunday": "7",
    "mon": "1",
    "tue": "2",
    "wed": "3",
    "thu": "4",
    "fri": "5",
    "sat": "6",
    "sun": "7",
}

HOLIDAY_KEYWORDS = (
    "공휴일",
    "휴일",
    "연휴",
    "설날",
    "설",
    "추석",
    "어린이날",
    "christmas",
    "holiday",
    "public holiday",
)

FIXED_HOLIDAYS = frozenset({
    (1, 1),
    (3, 1),
    (5, 5),
    (6, 6),
    (8, 15),
    (10, 3),
    (10, 9),
    (12, 25),
})

LATE_NIGHT_KEYWORDS = ("새벽", "심야", "밤", "late night", "midnight", "24시", "24h", "야간")


def _parse_korean_date(text: str, kst: datetime) -> datetime | None:
    m = re.search(r"(\d{4})\s*년?\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일?", text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=kst.tzinfo)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text.strip()[:10], fmt).replace(tzinfo=kst.tzinfo)
        except ValueError:
            continue
    return None


def parse_treatment_day(
    value: str | None,
    *,
    kst: datetime | None = None,
) -> tuple[str, str | None]:
    """자연어/날짜 → NEMC QT 코드(1~7, 8=공휴). 두 번째 값은 시간 관련 안내."""
    now = kst or datetime.now(ZoneInfo("Asia/Seoul"))
    if not value or not str(value).strip():
        return _qt_for_today(now), None

    raw = str(value).strip()
    lowered = raw.lower()
    time_note = None
    if any(k in raw or k in lowered for k in LATE_NIGHT_KEYWORDS):
        time_note = (
            "공공데이터는 **요일 단위** 안내만 제공합니다. "
            "새벽·심야 영업은 **365/24/심야** 약국일 수 있으니 **전화 확인**하세요."
        )

    if lowered in DAY_NAME_MAP:
        return DAY_NAME_MAP[lowered], time_note
    if raw in DAY_NAME_MAP:
        return DAY_NAME_MAP[raw], time_note
    for day_name, code in DAY_NAME_MAP.items():
        if day_name in raw or day_name in lowered:
            return code, time_note
    if raw.isdigit() and raw in {"1", "2", "3", "4", "5", "6", "7", "8"}:
        return raw, time_note
    if any(k in raw or k in lowered for k in HOLIDAY_KEYWORDS):
        return "8", time_note

    parsed = _parse_korean_date(raw, now)
    if not parsed:
        parsed = _parse_korean_date(lowered, now)
    if parsed:
        if (parsed.month, parsed.day) in FIXED_HOLIDAYS:
            return "8", time_note
        return str(parsed.weekday() + 1), time_note

    return _qt_for_today(now), time_note


def _sort_pharmacies_for_late_night(pharmacies: list[dict[str, str]]) -> list[dict[str, str]]:
    keywords = ("365", "24", "심야", "열린", "온누리")

    def score(row: dict[str, str]) -> int:
        name = row.get("dutyName", "")
        return sum(1 for k in keywords if k in name)

    return sorted(pharmacies, key=score, reverse=True)


async def fetch_open_clinics(
    *,
    sido: str,
    sigungu: str = "",
    specialty: str = "general",
    treatment_day: str | None = None,
    limit: int = 10,
) -> list[dict[str, str]]:
    params: dict[str, Any] = {
        "Q0": sido,
        "pageNo": 1,
        "numOfRows": min(limit, 100),
        "QT": treatment_day or _qt_for_today(),
    }
    if sigungu:
        params["Q1"] = sigungu
    code = SPECIALTY_CODES.get(specialty.lower(), specialty)
    if code and code.startswith("D"):
        params["QD"] = code

    url = f"{CLINIC_BASE}/getHsptlMdcncListInfoInqire"
    return await _get_xml(url, params)


async def fetch_emergency_rooms(
    *,
    sido: str,
    sigungu: str,
    limit: int = 10,
) -> list[dict[str, str]]:
    url = f"{ER_BASE}/getEmrrmRltmUsefulSckbdInfoInqire"
    items = await _get_xml(
        url,
        {
            "STAGE1": sido,
            "STAGE2": sigungu,
            "pageNo": 1,
            "numOfRows": min(limit, 100),
        },
    )
    return items


def _sort_by_distance(
    items: list[dict[str, str]],
    lat: float | None,
    lng: float | None,
) -> list[dict[str, str]]:
    if lat is None or lng is None:
        return items

    def key(row: dict[str, str]) -> float:
        try:
            rlat = float(row.get("wgs84Lat", "") or row.get("latitude", ""))
            rlng = float(row.get("wgs84Lon", "") or row.get("longitude", ""))
            return haversine_m(lat, lng, rlat, rlng)
        except (TypeError, ValueError):
            return float("inf")

    return sorted(items, key=key)


def _format_er_beds(hvec: str) -> str:
    if not hvec:
        return "정보 없음"
    try:
        n = int(hvec)
        if n < 0:
            return "가용 병상 없음/제한"
        return f"응급실 가용 {n}병상"
    except ValueError:
        return hvec


def _coord_item(row: dict[str, str]) -> dict[str, float]:
    try:
        lat = float(row.get("wgs84Lat", "") or row.get("latitude", ""))
        lng = float(row.get("wgs84Lon", "") or row.get("longitude", ""))
        return {"latitude": lat, "longitude": lng}
    except (TypeError, ValueError):
        return {}


def format_clinic_list(
    clinics: list[dict[str, str]],
    *,
    region_label: str,
    treatment_day: str,
    specialty: str,
    coords_hint: str | None = None,
) -> str:
    if not clinics:
        return (
            f"**{region_label}**에서 조건에 맞는 병·의원을 찾지 못했습니다.\n\n"
            f"- 진료요일 코드 QT={treatment_day} (8=공휴)\n"
            f"- 먼저 `get_emergency_hotlines`로 **1339** 상담을 권장합니다.\n\n{MEDICAL_DISCLAIMER}"
        )

    lines = [
        f"## 야간·휴일 진료 병·의원 — {region_label}",
        f"- 진료요일 QT: **{treatment_day}** (1=월 … 7=일, 8=공휴)",
        f"- 진료과: **{specialty}**",
    ]
    if coords_hint:
        lines.append(f"- 기준: {coords_hint}")
    lines.append("")
    clinic_points = [_coord_item(c) for c in clinics]
    append_overview_map(lines, clinic_points, title=f"{region_label} 병·의원")

    for idx, c in enumerate(clinics, start=1):
        name = c.get("dutyName", "이름 없음")
        addr = c.get("dutyAddr", "")
        tel = c.get("dutyTel1", "")
        div = c.get("dutyDivNam", c.get("dutyDiv", ""))
        etc = c.get("dutyEtc", "")
        dist = c.get("_distance_m")
        dist_txt = f" · 약 {dist}m" if dist is not None else ""
        lines.append(f"### {idx}. {name}{dist_txt}")
        lines.append(f"- **구분**: {div}")
        if addr:
            lines.append(f"- **주소**: {addr}")
        if tel:
            lines.append(f"- **전화**: {tel}")
        if etc:
            lines.append(f"- **비고**: {etc[:120]}")
        enrich_result_lines(lines, name=name, item=_coord_item(c), rank=idx)
        lines.append("")

    lines.append(MEDICAL_DISCLAIMER)
    lines.append("_출처: 국립중앙의료원 전국 병·의원 찾기 (공공데이터)_")
    return "\n".join(lines)


def format_er_list(
    rooms: list[dict[str, str]],
    *,
    region_label: str,
    coords_hint: str | None = None,
) -> str:
    if not rooms:
        return (
            f"**{region_label}** 응급실 정보를 찾지 못했습니다. "
            f"**119** 또는 **1339**에 문의하세요.\n\n{MEDICAL_DISCLAIMER}"
        )

    lines = [f"## 응급실 실시간 병상 — {region_label}"]
    if coords_hint:
        lines.append(f"- 기준: {coords_hint}")
    lines.append("")
    room_points = [_coord_item(r) for r in rooms]
    append_overview_map(lines, room_points, title=f"{region_label} 응급실")

    for idx, r in enumerate(rooms, start=1):
        name = r.get("dutyName", "이름 없음")
        tel = r.get("dutyTel3", r.get("hv1", ""))
        beds = _format_er_beds(r.get("hvec", ""))
        updated = r.get("hvidate", "")
        lines.append(f"### {idx}. {name}")
        if tel:
            lines.append(f"- **응급실 전화**: {tel}")
        lines.append(f"- **병상**: {beds}")
        if updated:
            lines.append(f"- **갱신**: {updated}")
        enrich_result_lines(lines, name=name, item=_coord_item(r), rank=idx)
        lines.append("")

    lines.append(MEDICAL_DISCLAIMER)
    lines.append("_출처: 국립중앙의료원 응급의료기관 정보 (공공데이터)_")
    return "\n".join(lines)


async def find_open_clinics_near(
    *,
    place_query: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    specialty: str = "pediatric",
    treatment_day: str | None = None,
    limit: int = 5,
) -> str:
    from place_context import normalize_specialty

    specialty = normalize_specialty(specialty)
    if specialty == "veteran":
        from veteran_hospital import find_veteran_hospitals_near

        return await find_veteran_hospitals_near(place_query=place_query, limit=limit)
    if specialty == "vet":
        return (
            "동물병원은 `find_outdoor_service_tool`(service=`vet_hospital`) 또는 "
            "`emergency_guide_tool`을 사용하세요. `find_open_clinic`은 사람 병원 전용입니다."
        )

    sido, sigungu, lat, lng = await resolve_region(
        place_query=place_query,
        latitude=latitude,
        longitude=longitude,
    )
    qt, _time_note = parse_treatment_day(treatment_day)
    clinics = await fetch_open_clinics(
        sido=sido,
        sigungu=sigungu,
        specialty=specialty,
        treatment_day=qt,
        limit=limit * 3,
    )
    clinics = _sort_by_distance(clinics, lat, lng)[:limit]
    for c in clinics:
        try:
            if lat is not None and lng is not None:
                c["_distance_m"] = int(
                    haversine_m(lat, lng, float(c["wgs84Lat"]), float(c["wgs84Lon"]))
                )
        except (KeyError, ValueError):
            pass

    region_label = f"{sido} {sigungu}".strip()
    coords_hint = None
    if lat is not None and lng is not None:
        coords_hint = f"{lat:.6f},{lng:.6f}"
    elif place_query:
        coords_hint = place_query

    return format_clinic_list(
        clinics,
        region_label=region_label,
        treatment_day=qt,
        specialty=specialty,
        coords_hint=coords_hint,
    )


async def fetch_open_pharmacies(
    *,
    sido: str,
    sigungu: str = "",
    treatment_day: str | None = None,
    pharmacy_name: str | None = None,
    limit: int = 10,
) -> list[dict[str, str]]:
    params: dict[str, Any] = {
        "Q0": sido,
        "pageNo": 1,
        "numOfRows": min(limit, 100),
        "QT": treatment_day or _qt_for_today(),
    }
    if sigungu:
        params["Q1"] = sigungu
    if pharmacy_name:
        params["QN"] = pharmacy_name

    url = f"{PHARMACY_BASE}/getParmacyListInfoInqire"
    return await _get_xml(url, params)


def format_pharmacy_list(
    pharmacies: list[dict[str, str]],
    *,
    region_label: str,
    treatment_day: str,
    coords_hint: str | None = None,
    time_note: str | None = None,
) -> str:
    if not pharmacies:
        return (
            f"**{region_label}**에서 조건에 맞는 약국을 찾지 못했습니다.\n\n"
            f"- 진료요일 코드 QT={treatment_day} (8=공휴)\n"
            f"- `get_emergency_hotlines`로 **1339** 상담을 권장합니다.\n\n"
            f"{PHARMACY_DISCLAIMER}\n\n{MEDICAL_DISCLAIMER}"
        )

    lines = [
        f"## 약국 안내 — {region_label}",
        f"- 진료요일 QT: **{treatment_day}** (1=월 … 7=일, 8=공휴)",
    ]
    if coords_hint:
        lines.append(f"- 기준: {coords_hint}")
    if time_note:
        lines.append(f"- ⏰ {time_note}")
    lines.append("")
    pharmacy_points = [_coord_item(p) for p in pharmacies]
    append_overview_map(lines, pharmacy_points, title=f"{region_label} 약국")

    for idx, p in enumerate(pharmacies, start=1):
        name = p.get("dutyName", "이름 없음")
        addr = p.get("dutyAddr", "")
        tel = p.get("dutyTel1", "")
        dist = p.get("_distance_m")
        dist_txt = f" · 약 {dist}m" if dist is not None else ""
        lines.append(f"### {idx}. {name}{dist_txt}")
        if addr:
            lines.append(f"- **주소**: {addr}")
        if tel:
            lines.append(f"- **전화**: {tel}")
        enrich_result_lines(lines, name=name, item=_coord_item(p), rank=idx)
        lines.append("")

    lines.append(PHARMACY_DISCLAIMER)
    lines.append(MEDICAL_DISCLAIMER)
    lines.append("_출처: 국립중앙의료원 전국 약국 정보 (공공데이터 15000576)_")
    return "\n".join(lines)


async def find_open_pharmacies_near(
    *,
    place_query: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    treatment_day: str | None = None,
    pharmacy_name: str | None = None,
    limit: int = 5,
) -> str:
    sido, sigungu, lat, lng = await resolve_region(
        place_query=place_query,
        latitude=latitude,
        longitude=longitude,
    )
    qt, time_note = parse_treatment_day(treatment_day)
    try:
        pharmacies = await fetch_open_pharmacies(
            sido=sido,
            sigungu=sigungu,
            treatment_day=qt,
            pharmacy_name=pharmacy_name,
            limit=limit * 3,
        )
    except RuntimeError as exc:
        return (
            f"약국 API 호출 실패: {exc}\n\n"
            "공공데이터포털에서 **15000576 전국 약국 정보** 활용신청을 확인하세요.\n\n"
            f"{MEDICAL_DISCLAIMER}"
        )

    pharmacies = _sort_pharmacies_for_late_night(pharmacies)
    pharmacies = _sort_by_distance(pharmacies, lat, lng)[:limit]
    for p in pharmacies:
        try:
            if lat is not None and lng is not None:
                p["_distance_m"] = int(
                    haversine_m(lat, lng, float(p["wgs84Lat"]), float(p["wgs84Lon"]))
                )
        except (KeyError, ValueError):
            pass

    region_label = f"{sido} {sigungu}".strip()
    coords_hint = None
    if lat is not None and lng is not None:
        coords_hint = f"{lat:.6f},{lng:.6f}"
    elif place_query:
        coords_hint = place_query

    return format_pharmacy_list(
        pharmacies,
        region_label=region_label,
        treatment_day=qt,
        coords_hint=coords_hint,
        time_note=time_note,
    )


async def find_emergency_rooms_near(
    *,
    place_query: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    limit: int = 5,
) -> str:
    sido, sigungu, lat, lng = await resolve_region(
        place_query=place_query,
        latitude=latitude,
        longitude=longitude,
    )
    if not sigungu:
        return (
            f"시·군·구를 특정하지 못했습니다. `place_query`에 **구/군**까지 넣어 주세요 "
            f"(예: '서울 강남구').\n\n{MEDICAL_DISCLAIMER}"
        )

    rooms = await fetch_emergency_rooms(sido=sido, sigungu=sigungu, limit=limit)
    region_label = f"{sido} {sigungu}".strip()
    coords_hint = place_query or (f"{lat:.6f},{lng:.6f}" if lat and lng else None)
    return format_er_list(rooms, region_label=region_label, coords_hint=coords_hint)
