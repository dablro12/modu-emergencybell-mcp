"""ODsay LAB 대중교통 길찾기 API."""

from __future__ import annotations

import os
from typing import Any
import httpx

from kakao_local import geocode_place

ODSAY_API_KEY = os.getenv("ODSAY_API_KEY", "")
ODSAY_BASE = "https://api.odsay.com/v1/api/searchPubTransPathT"


def _require_key() -> str:
    if not ODSAY_API_KEY:
        raise ValueError("ODSAY_API_KEY is not set")
    return ODSAY_API_KEY


def _format_minutes(seconds: int | float | None) -> str:
    if not seconds:
        return "?"
    minutes = int(float(seconds) // 60)
    return f"{minutes}분"


def _summarize_path(path: dict[str, Any]) -> list[str]:
    info = path.get("info") or {}
    lines = [
        f"- **총 소요**: {_format_minutes(info.get('totalTime'))} · "
        f"환승 {info.get('busTransitCount', 0) + info.get('subwayTransitCount', 0)}회 · "
        f"요금 약 {info.get('payment', '?')}원",
    ]
    for sub in path.get("subPath") or []:
        traffic = sub.get("trafficType")
        if traffic == 1:
            lane = (sub.get("lane") or [{}])[0]
            lines.append(f"  - 🚇 {lane.get('name', '지하철')} {sub.get('startName', '')} → {sub.get('endName', '')}")
        elif traffic == 2:
            lane = (sub.get("lane") or [{}])[0]
            lines.append(f"  - 🚌 {lane.get('busNo', '버스')} {sub.get('startName', '')} → {sub.get('endName', '')}")
        elif traffic == 3:
            lines.append(f"  - 🚶 도보 {_format_minutes(sub.get('sectionTime'))}")
    return lines


async def find_transit_route(
    *,
    origin_query: str,
    destination_query: str,
    optimize: int = 0,
) -> str:
    origin = await geocode_place(origin_query)
    destination = await geocode_place(destination_query)
    if not origin or not destination:
        missing = []
        if not origin:
            missing.append(f"출발지 '{origin_query}'")
        if not destination:
            missing.append(f"도착지 '{destination_query}'")
        return " · ".join(missing) + " 좌표를 찾지 못했습니다."

    sx, sy = origin[1], origin[0]
    ex, ey = destination[1], destination[0]
    params = {
        "apiKey": _require_key(),
        "SX": sx,
        "SY": sy,
        "EX": ex,
        "EY": ey,
        "OPT": optimize,
        "SearchType": 0,
        "SearchPathType": 0,
        "lang": 0,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ODSAY_BASE, params=params)
        response.raise_for_status()
        payload = response.json()

    errors = payload.get("error") or []
    if errors:
        message = errors[0].get("message", "ODsay API error")
        if "ApiKeyAuthFailed" in message:
            return (
                f"ODsay 인증 실패: {message}\n"
                "- MCP 서버 IP를 ODsay 애플리케이션 **Server IP**에 등록했는지 확인하세요.\n"
                "- 백엔드 호출에는 **Server 키**가 필요합니다 (Web 키 불가)."
            )
        return f"ODsay API 오류: {message}"

    paths = (payload.get("result") or {}).get("path") or []
    if not paths:
        return f"'{origin_query}' → '{destination_query}' 대중교통 경로를 찾지 못했습니다."

    lines = [
        f"## 대중교통 — {origin_query} → {destination_query}",
        "",
        "### 추천 경로",
    ]
    lines.extend(_summarize_path(paths[0]))

    if len(paths) > 1:
        lines.append("")
        lines.append("### 다른 경로")
        for alt in paths[1:3]:
            lines.extend(_summarize_path(alt))
            lines.append("")

    lines.append("")
    lines.append("_출처: ODsay LAB_")
    return "\n".join(lines).strip()
