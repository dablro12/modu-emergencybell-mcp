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
PROD_URL = os.getenv("KFTC_FINMAP_PROD_URL", "https://finmapapi.kftc.or.kr").rstrip("/")
TEST_URL = os.getenv("KFTC_FINMAP_TEST_URL", "https://testfinmapapi.kftc.or.kr").rstrip("/")
BASE_URL = os.getenv("KFTC_FINMAP_BASE_URL", PROD_URL).rstrip("/")

_token_cache: dict[str, Any] = {"token": "", "expires_at": 0.0, "base": ""}


def _require_credentials() -> tuple[str, str]:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("KFTC_FINMAP_CLIENT_ID / KFTC_FINMAP_CLIENT_SECRET is not set")
    return CLIENT_ID, CLIENT_SECRET


def _candidate_bases() -> list[str]:
    bases: list[str] = []
    for url in (BASE_URL, PROD_URL, TEST_URL):
        if url and url not in bases:
            bases.append(url)
    return bases


async def _get_access_token() -> tuple[str, str]:
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"], _token_cache["base"]

    client_id, client_secret = _require_credentials()
    last_error = "금융맵 토큰 발급 실패"

    async with httpx.AsyncClient(timeout=20.0) as client:
        for base in _candidate_bases():
            try:
                response = await client.post(
                    f"{base}/oauth/2.0/token",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "scope": "finmap",
                        "grant_type": "client_credentials",
                    },
                )
            except httpx.HTTPError as exc:
                last_error = f"{base} 연결 실패: {exc.__class__.__name__}"
                continue
            if response.status_code >= 400:
                last_error = f"{base} 토큰 오류 ({response.status_code})"
                continue
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                last_error = f"{base} 토큰 응답 없음"
                continue
            expires_in = int(payload.get("expires_in", 3600))
            _token_cache["token"] = token
            _token_cache["expires_at"] = now + expires_in
            _token_cache["base"] = base
            return token, base

    raise RuntimeError(last_error)


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
    try:
        token, base = await _get_access_token()
    except RuntimeError as exc:
        return (
            f"금융맵 API에 연결하지 못했습니다.\n"
            f"- {exc}\n"
            "- KC 네트워크에서 `finmapapi.kftc.or.kr` 접근이 가능한지 확인하세요.\n"
            "- GitHub Secrets의 `KFTC_FINMAP_BASE_URL`을 운영/테스트 URL로 맞춰 주세요."
        )

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

    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(
            f"{base}/v1.0/inquiry/atm_lists",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )

    if response.status_code >= 400:
        return (
            f"금융맵 ATM 조회 오류 ({response.status_code}).\n"
            f"- 사용 URL: {base}\n"
            "- 인증정보·테스트베드 승인 상태를 확인하세요."
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
        f"- API: {base}",
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
