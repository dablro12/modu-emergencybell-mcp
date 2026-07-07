"""금융결제원 금융맵 API — ATM·지점 조회."""

from __future__ import annotations

import math
import os
import time
from typing import Any

import httpx

from helpers import haversine_m
from kakao_local import geocode_place

CLIENT_ID = os.getenv("KFTC_FINMAP_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("KFTC_FINMAP_CLIENT_SECRET", "")
BASE_URL = os.getenv("KFTC_FINMAP_BASE_URL", "https://testfinmapapi.kftc.or.kr").rstrip("/")

_token_cache: dict[str, Any] = {"token": "", "expires_at": 0.0}


def _require_credentials() -> tuple[str, str]:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("KFTC_FINMAP_CLIENT_ID / KFTC_FINMAP_CLIENT_SECRET is not set")
    return CLIENT_ID, CLIENT_SECRET


async def _get_access_token() -> str:
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    client_id, client_secret = _require_credentials()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/oauth/2.0/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "finmap",
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()
        payload = response.json()

    token = payload["access_token"]
    expires_in = int(payload.get("expires_in", 3600))
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expires_in
    return token


def _bbox(lat: float, lng: float, radius_m: int) -> dict[str, str]:
    delta_lat = radius_m / 111_000
    cos_lat = max(math.cos(math.radians(lat)), 0.01)
    delta_lng = radius_m / (111_000 * cos_lat)
    return {
        "start_latitude": f"{lat - delta_lat:.6f}",
        "start_longitude": f"{lng - delta_lng:.6f}",
        "end_latitude": f"{lat + delta_lat:.6f}",
        "end_longitude": f"{lng + delta_lng:.6f}",
    }


async def search_atms_near(
    *,
    place_query: str,
    radius_m: int = 1000,
    wheelchair_accessible: bool = False,
    limit: int = 5,
) -> str:
    coords = await geocode_place(place_query)
    if not coords:
        return f"'{place_query}' 위치를 찾지 못했습니다. 역·구 이름으로 다시 시도해 주세요."

    lat, lng = coords
    token = await _get_access_token()
    body = {
        **_bbox(lat, lng, radius_m),
        "mob_cash_card_psb_yn": "N",
        "atm_srch_yn": "Y",
        "atm_cond": {
            "open_yn": "N",
            "whlchr_psb_yn": "Y" if wheelchair_accessible else "N",
            "ptsh_icld_yn": "Y",
            "org_code_srch_yn": "N",
            "prvd_svc_srch_yn": "N",
            "spt_lang_srch_yn": "N",
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/v1.0/inquiry/atm_lists",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )
        if response.status_code >= 400:
            return (
                f"금융맵 API 오류 ({response.status_code}). "
                "테스트베드 접근·인증정보를 확인하세요."
            )
        payload = response.json()

    if payload.get("rsp_code") != "000":
        return f"금융맵 조회 실패: {payload.get('rsp_message', 'unknown error')}"

    atms = payload.get("atm_list") or []
    for atm in atms:
        try:
            atm_lat = float(atm.get("atm_latitude", 0))
            atm_lng = float(atm.get("atm_longitude", 0))
            atm["distance_m"] = int(haversine_m(lat, lng, atm_lat, atm_lng))
        except (TypeError, ValueError):
            atm["distance_m"] = None

    atms.sort(key=lambda row: row.get("distance_m") if row.get("distance_m") is not None else 10**9)
    atms = atms[:limit]

    if not atms:
        filter_note = " (휠체어 접근 가능)" if wheelchair_accessible else ""
        return f"'{place_query}' 반경 {radius_m}m 내 ATM을 찾지 못했습니다{filter_note}."

    lines = [
        f"## ATM — {place_query}",
        f"- 기준 좌표: {lat:.6f}, {lng:.6f}",
        "",
    ]
    for idx, atm in enumerate(atms, start=1):
        name = (atm.get("atm_name") or "").strip()
        dist = atm.get("distance_m")
        dist_text = f" · 약 {dist}m" if dist is not None else ""
        lines.append(f"### {idx}. {name}{dist_text}")
        lines.append(
            f"- **좌표**: {atm.get('atm_latitude')}, {atm.get('atm_longitude')}"
        )
        if atm.get("istl_loc_type_code"):
            lines.append(f"- **설치 유형**: {atm['istl_loc_type_code'].strip()}")
        lines.append("")

    lines.append("_출처: 금융결제원 금융맵 API_")
    return "\n".join(lines).strip()
