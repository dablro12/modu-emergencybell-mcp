#!/usr/bin/env python3
"""금융맵 API 연결 진단 — 토큰 발급 후 ATM 조회까지 확인."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finmap_client import _candidate_bases, _parse_finmap_error, _request_token, search_atms_near


async def probe_tokens() -> bool:
    client_id = os.getenv("KFTC_FINMAP_CLIENT_ID", "").strip()
    client_secret = os.getenv("KFTC_FINMAP_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print("FAIL: KFTC_FINMAP_CLIENT_ID / KFTC_FINMAP_CLIENT_SECRET 이 비어 있습니다.")
        return False

    print(f"Client ID: {client_id[:8]}...{client_id[-4:]}")
    print("Candidate bases:", ", ".join(_candidate_bases()))
    print()

    import httpx

    ok = False
    async with httpx.AsyncClient(timeout=25.0) as client:
        for base in _candidate_bases():
            print(f"=== TOKEN {base} ===")
            try:
                response = await _request_token(client, base, client_id, client_secret)
            except httpx.HTTPError as exc:
                print(f"FAIL: 연결 오류 — {exc.__class__.__name__}: {exc}")
                print()
                continue
            print(f"HTTP {response.status_code}")
            print(response.text[:400])
            if response.status_code < 400:
                token = response.json().get("access_token")
                if token:
                    print("OK: access_token 발급 성공")
                    ok = True
            else:
                print("FAIL:", _parse_finmap_error(response))
            print()
    return ok


async def probe_atm() -> bool:
    print("=== ATM search (명동) ===")
    text = await search_atms_near(place_query="명동", limit=2)
    print(text)
    print()
    return text.startswith("## ATM")


async def main() -> int:
    token_ok = await probe_tokens()
    atm_ok = await probe_atm()
    if atm_ok:
        print("RESULT: ATM 조회 성공")
        return 0
    if token_ok:
        print("RESULT: 토큰은 성공했으나 ATM 조회 실패 — 좌표/파라미터 확인")
        return 1
    print("RESULT: 토큰 발급 실패")
    print()
    print("체크리스트:")
    print("  1. developers.kftc.or.kr → 도구 → 금융MAP → Authorize 에 본인 키 입력")
    print("  2. Swagger 예시 키(88d4270a-...) 사용 금지")
    print("  3. 금융 맵 서비스 API Key 등록 = 완료")
    print("  4. BASE_URL = https://testfinmapapi.kftc.or.kr (테스트베드)")
    print("  5. Callback URL 등록 실패 시 finmap@kftc.or.kr 문의")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
