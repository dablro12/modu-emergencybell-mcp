"""공공데이터포털 API 공통 HTTP·XML·JSON 파서."""

from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from typing import Any

import httpx

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY", "")
SERVICE_KEY_ENCODED = os.getenv("DATA_GO_KR_SERVICE_KEY_ENCODED", "")


def service_keys() -> list[str]:
    keys: list[str] = []
    for env_name in ("DATA_GO_KR_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY_ENCODED"):
        value = (os.getenv(env_name) or "").strip()
        if value and value not in keys:
            keys.append(value)
    return keys


def require_service_key() -> str:
    keys = service_keys()
    if not keys:
        raise ValueError("DATA_GO_KR_SERVICE_KEY is not set")
    return keys[0]


def parse_xml_items(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    code = root.findtext(".//resultCode", "")
    if code and code not in ("00", "0"):
        msg = root.findtext(".//resultMsg", "API error")
        raise RuntimeError(f"API error {code}: {msg}")
    items: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        row = {child.tag: (child.text or "").strip() for child in item}
        if row:
            items.append(row)
    return items


def parse_json_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload.get("body") or payload.get("response", {}).get("body", {})
    items = body.get("items")
    if not items:
        return []
    item = items.get("item")
    if item is None:
        return []
    if isinstance(item, list):
        return item
    return [item]


async def fetch_datago(
    url: str,
    params: dict[str, Any],
    *,
    response_format: str = "xml",
) -> list[dict[str, Any]]:
    keys = service_keys()
    if not keys:
        raise ValueError("DATA_GO_KR_SERVICE_KEY is not set")

    last_error: Exception | None = None
    for key in keys:
        merged = {"serviceKey": key, **params}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=merged)
                if response.status_code in (401, 403):
                    last_error = RuntimeError(
                        f"HTTP {response.status_code} — API 활용신청·인증키를 확인하세요."
                    )
                    continue
                response.raise_for_status()
                if response_format == "json" or params.get("type") == "json":
                    payload = response.json()
                    header = payload.get("header") or payload.get("response", {}).get("header", {})
                    code = str(header.get("resultCode", "00"))
                    if code not in ("00", "0"):
                        msg = header.get("resultMsg", "API error")
                        raise RuntimeError(f"API error {code}: {msg}")
                    return parse_json_items(payload)
                return parse_xml_items(response.text)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error:
        raise last_error
    return []
