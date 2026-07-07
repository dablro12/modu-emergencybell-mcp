"""공중화장실 CSV → 구조화 레코드 파싱."""

from __future__ import annotations

import re
from typing import Any

OPENING_TYPE_MAP = {
    "상시": "always",
    "정시": "scheduled",
    "불규칙": "irregular",
    "미개방": "closed",
}


def _int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def _yn(value: str | None) -> bool:
    return (value or "").upper() == "Y"


def parse_region(road_address: str, jibun_address: str) -> dict[str, str]:
    """주소 문자열에서 시도/시군구 추출."""
    address = road_address or jibun_address or ""
    parts = address.split()
    sido = parts[0] if parts else ""
    sigungu = parts[1] if len(parts) > 1 else ""
    return {"sido": sido, "sigungu": sigungu, "full_prefix": f"{sido} {sigungu}".strip()}


def parse_user_types(row: dict[str, str]) -> dict[str, Any]:
    """이용자 유형별 적합 여부."""
    wheelchair_m = _int(row.get("남성용-장애인용대변기수")) + _int(row.get("남성용-장애인용소변기수"))
    wheelchair_f = _int(row.get("여성용-장애인용대변기수"))
    child_m = _int(row.get("남성용-어린이용대변기수")) + _int(row.get("남성용-어린이용소변기수"))
    child_f = _int(row.get("여성용-어린이용대변기수"))
    diaper = _yn(row.get("기저귀교환대유무"))
    emergency = _yn(row.get("비상벨설치여부"))

    wheelchair = wheelchair_m + wheelchair_f > 0
    child = child_m + child_f > 0

    tags: list[str] = ["general"]
    if wheelchair:
        tags.append("wheelchair")
    if child:
        tags.append("child")
    if diaper:
        tags.append("infant_care")
    if emergency:
        tags.append("elderly_safety")

    return {
        "tags": tags,
        "general": True,
        "wheelchair": wheelchair,
        "child": child,
        "infant_care": diaper,
        "elderly_safety": emergency,
        "wheelchair_units": wheelchair_m + wheelchair_f,
        "child_units": child_m + child_f,
    }


def parse_facilities(row: dict[str, str]) -> dict[str, Any]:
    """시설·안전·편의 특징."""
    return {
        "male_stalls": _int(row.get("남성용-대변기수")),
        "male_urinals": _int(row.get("남성용-소변기수")),
        "female_stalls": _int(row.get("여성용-대변기수")),
        "wheelchair_male_stall": _int(row.get("남성용-장애인용대변기수")),
        "wheelchair_male_urinal": _int(row.get("남성용-장애인용소변기수")),
        "wheelchair_female_stall": _int(row.get("여성용-장애인용대변기수")),
        "child_male_stall": _int(row.get("남성용-어린이용대변기수")),
        "child_male_urinal": _int(row.get("남성용-어린이용소변기수")),
        "child_female_stall": _int(row.get("여성용-어린이용대변기수")),
        "emergency_bell": _yn(row.get("비상벨설치여부")),
        "emergency_bell_location": row.get("비상벨설치장소") or "",
        "diaper_station": _yn(row.get("기저귀교환대유무")),
        "diaper_station_location": row.get("기저귀교환대장소") or "",
        "cctv_entrance": _yn(row.get("화장실입구CCTV설치유무")),
        "safety_management_target": _yn(row.get("안전관리시설설치대상여부")),
        "waste_type": row.get("오물처리방식") or "",
        "ownership_type": row.get("화장실소유구분명") or "",
    }


def parse_opening(row: dict[str, str]) -> dict[str, Any]:
    """개방 시간 유형."""
    raw = (row.get("개방시간") or "").strip()
    detail = (row.get("개방시간상세") or "").strip()
    opening_type = OPENING_TYPE_MAP.get(raw, "unknown")

    return {
        "type": opening_type,
        "type_raw": raw or "unknown",
        "detail": detail,
        "is_always_open": opening_type == "always",
        "is_scheduled": opening_type == "scheduled",
        "is_irregular": opening_type == "irregular",
        "is_closed_type": opening_type == "closed",
    }


def is_open_now(opening: dict[str, Any]) -> bool | None:
    """현재 개방 여부 (KST). 상시=True, 미개방=False, 정시/불규칙은 None(상세 필요)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if opening.get("is_always_open"):
        return True
    if opening.get("is_closed_type"):
        return False
    if opening.get("is_irregular"):
        return None

    detail = opening.get("detail") or ""
    if not detail:
        return None

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    weekday = now.weekday()
    time_str = now.strftime("%H:%M")

    if "공휴일" in detail and now.weekday() >= 5:
        if "공휴일 휴관" in detail or "휴관" in detail.split("공휴일")[-1][:10]:
            pass

    ranges = re.findall(r"(\d{2}):(\d{2})~(\d{2}):(\d{2})", detail)
    if not ranges:
        return None

    for start_h, start_m, end_h, end_m in ranges:
        start = f"{start_h}:{start_m}"
        end = f"{end_h}:{end_m}"
        if start <= time_str <= end:
            if weekday < 5 and ("월" in detail or "평일" in detail):
                return True
            if weekday >= 5 and ("토" in detail or "일" in detail or "주말" in detail):
                return True
            if "월-일" in detail or "매일" in detail:
                return True

    if "평일" in detail and weekday < 5:
        for start_h, start_m, end_h, end_m in ranges[:1]:
            if f"{start_h}:{start_m}" <= time_str <= f"{end_h}:{end_m}":
                return True

    return None


def parse_record(row: dict[str, str]) -> dict[str, Any]:
    """CSV 한 행 → 정규화 레코드."""
    road = (row.get("소재지도로명주소") or "").strip()
    jibun = (row.get("소재지지번주소") or "").strip()
    region = parse_region(road, jibun)
    opening = parse_opening(row)

    return {
        "id": row.get("관리번호") or "",
        "local_gov_code": row.get("개방자치단체코드") or "",
        "category": row.get("구분명") or "",
        "name": row.get("화장실명") or "",
        "road_address": road,
        "jibun_address": jibun,
        "search_text": " ".join(filter(None, [row.get("화장실명"), road, jibun])).lower(),
        "region": region,
        "phone": row.get("전화번호") or "",
        "management_agency": row.get("관리기관명") or "",
        "opening": opening,
        "user_types": parse_user_types(row),
        "facilities": parse_facilities(row),
        "installed_at": row.get("설치연월") or "",
        "data_date": row.get("데이터기준일자") or "",
        "updated_at": row.get("최종수정시점") or "",
        "latitude": None,
        "longitude": None,
    }
