"""금융결제원 금융맵 API — ATM·지점 조회."""

from __future__ import annotations

import math
import os
import time
from typing import Any

import httpx

from helpers import haversine_m
from kakao_local import geocode_place

CLIENT_ID = os.getenv("KFTC_FINMAP_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("KFTC_FINMAP_CLIENT_SECRET", "").strip()
PROD_URL = os.getenv("KFTC_FINMAP_PROD_URL", "https://finmapapi.kftc.or.kr").rstrip("/")
TEST_URL = os.getenv("KFTC_FINMAP_TEST_URL", "https://testfinmapapi.kftc.or.kr").rstrip("/")
BASE_URL = os.getenv("KFTC_FINMAP_BASE_URL", TEST_URL).rstrip("/")

FINMAP_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=UTF-8",
}

_token_cache: dict[str, Any] = {"token": "", "expires_at": 0.0, "base": ""}


def _parse_finmap_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200] or f"HTTP {response.status_code}"
    code = payload.get("rsp_code", "")
    message = payload.get("rsp_message", "")
    if code or message:
        return f"rsp_code={code} {message}".strip()
    return response.text[:200] or f"HTTP {response.status_code}"


def _finmap_error_hint(rsp_code: str) -> str:
    hints = {
        "163": (
            "인증 실패입니다. (1) Swagger 예시 키가 아닌 본인 API Key를 사용했는지, "
            "(2) 금융 맵 서비스에 API Key 등록이 '완료'인지, "
            "(3) 테스트베드는 testfinmapapi.kftc.or.kr / 운영은 별도 이용계약이 필요한지 확인하세요."
        ),
        "211": "Access Token이 없습니다. 먼저 /oauth/2.0/token 으로 토큰을 발급하세요.",
        "212": "요청 헤더 형식이 잘못되었습니다. Content-Type을 확인하세요.",
    }
    return hints.get(rsp_code, "")


def _require_credentials() -> tuple[str, str]:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("KFTC_FINMAP_CLIENT_ID / KFTC_FINMAP_CLIENT_SECRET is not set")
    return CLIENT_ID, CLIENT_SECRET


def _candidate_bases() -> list[str]:
    """테스트베드 URL을 운영보다 먼저 시도합니다."""
    bases: list[str] = []
    for url in (BASE_URL, TEST_URL, PROD_URL):
        if url and url not in bases:
            bases.append(url)
    return bases


async def _request_token(client: httpx.AsyncClient, base: str, client_id: str, client_secret: str) -> httpx.Response:
    return await client.post(
        f"{base}/oauth/2.0/token",
        headers={"Accept": "application/json"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "finmap",
            "grant_type": "client_credentials",
        },
    )


async def _get_access_token() -> tuple[str, str]:
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"], _token_cache["base"]

    client_id, client_secret = _require_credentials()
    last_error = "금융맵 토큰 발급 실패"

    async with httpx.AsyncClient(timeout=20.0) as client:
        for base in _candidate_bases():
            try:
                response = await _request_token(client, base, client_id, client_secret)
            except httpx.HTTPError as exc:
                last_error = f"{base} 연결 실패: {exc.__class__.__name__}"
                continue
            if response.status_code >= 400:
                detail = _parse_finmap_error(response)
                hint = ""
                try:
                    hint = _finmap_error_hint(str(response.json().get("rsp_code", "")))
                except ValueError:
                    pass
                last_error = f"{base} 토큰 오류 ({response.status_code}): {detail}"
                if hint:
                    last_error += f" — {hint}"
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
            "- 개발자 포털 **도구 → 금융MAP → Authorize** 에서 본인 Client ID/Secret으로 토큰 발급을 먼저 확인하세요.\n"
            "- Swagger 예시 키(`88d4270a-...`)가 아닌 **마이페이지 API Key** 를 사용해야 합니다.\n"
            "- 테스트: `KFTC_FINMAP_BASE_URL=https://testfinmapapi.kftc.or.kr`\n"
            "- Callback URL 등록이 실패하면 `finmap@kftc.or.kr` 로 client_credentials 전용 이용 문의하세요."
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
            headers={**FINMAP_HEADERS, "Authorization": f"Bearer {token}"},
            json=body,
        )

    if response.status_code >= 400:
        detail = _parse_finmap_error(response)
        return (
            f"금융맵 ATM 조회 오류 ({response.status_code}).\n"
            f"- 사용 URL: {base}\n"
            f"- {detail}"
        )

    payload = response.json()
    if payload.get("rsp_code") != "000":
        code = str(payload.get("rsp_code", ""))
        hint = _finmap_error_hint(code)
        message = payload.get("rsp_message", "unknown error")
        extra = f"\n- {hint}" if hint else ""
        return f"금융맵 조회 실패: {message} (rsp_code={code}){extra}"

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
