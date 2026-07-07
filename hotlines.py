"""긴급·상담 핫라인 — 상황별 전화 안내."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

HOTLINES_FILE = Path(__file__).resolve().parent / "data" / "hotlines" / "hotlines.json"

DISCLAIMER_KO = (
    "⚠️ **면책**: 본 안내는 공식 번호 정보이며 의료 진단·119/112 신고 대행이 아닙니다. "
    "**생명이 위협되면 119**, 범죄·위협이면 **112**를 직접 전화하세요."
)
DISCLAIMER_EN = (
    "⚠️ **Disclaimer**: Information only—not medical advice or emergency dispatch. "
    "Call **119** for life-threatening emergencies, **112** for police."
)

SITUATION_ENUM = frozenset({
    "life_threatening",
    "medical_urgent",
    "restroom_help",
    "foreign_visitor",
    "poison",
    "police",
    "mental_crisis",
    "school_violence",
    "utility_electric",
    "utility_gas",
    "safety_hazard",
    "unsure",
})


@lru_cache(maxsize=1)
def load_hotlines_data() -> dict[str, Any]:
    with HOTLINES_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _hotline_by_id(data: dict[str, Any], hid: str) -> dict[str, Any] | None:
    if hid == "restroom_bell":
        return data.get("restroom_emergency_bell")
    for h in data.get("hotlines", []):
        if h["id"] == hid:
            return h
    return None


def _score_keywords(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    score = 0
    for kw in keywords:
        if kw.lower() in lowered:
            score += 1
    return score


def resolve_situation(
    situation_description: str,
    situation: str | None = None,
) -> str:
    from place_context import normalize_situation_tag

    normalized = normalize_situation_tag(situation)
    if normalized and normalized in SITUATION_ENUM:
        return normalized

    data = load_hotlines_data()
    routing = data.get("situation_routing", {})
    best_key = "unsure"
    best_score = 0
    for key, cfg in routing.items():
        score = _score_keywords(situation_description, cfg.get("keywords_ko", []))
        if score > best_score:
            best_score = score
            best_key = key
    return best_key


def _pick_lang(cfg: dict[str, Any], field: str, language: str) -> str:
    suffix = "_ko" if language == "ko" else "_en"
    return cfg.get(f"{field}{suffix}") or cfg.get(f"{field}_ko", "")


def _format_hotline_block(
    data: dict[str, Any],
    hid: str,
    *,
    language: str,
    priority: int,
) -> list[str]:
    item = _hotline_by_id(data, hid)
    if not item:
        return []

    lines: list[str] = []
    if hid == "restroom_bell":
        name = _pick_lang(item, "name", language)
        desc = _pick_lang(item, "description", language)
        lines.append(f"**{priority}. {name}** (현장 장치 — 전화 아님)")
        lines.append(f"   {desc}")
        no_resp = _pick_lang(item, "when_no_response", language)
        if no_resp:
            lines.append(f"   → {no_resp}")
        return lines

    name = _pick_lang(item, "name", language)
    when = _pick_lang(item, "when", language)
    number = item.get("number", hid)
    lines.append(f"**{priority}. {number}** — {name}")
    if when:
        lines.append(f"   - {when}")
    return lines


def format_emergency_hotlines(
    situation_description: str,
    *,
    situation: str | None = None,
    language: str = "ko",
) -> str:
    data = load_hotlines_data()
    resolved = resolve_situation(situation_description, situation)
    routing = data.get("situation_routing", {}).get(resolved, {})
    if not routing:
        routing = data.get("situation_routing", {}).get("unsure", {})

    headline = _pick_lang(routing, "headline", language)
    action = _pick_lang(routing, "action", language)
    label = _pick_lang(routing, "label", language)

    lines = [
        f"## 이 상황에서 어디에 전화해야 해?",
        "",
        f"**입력**: {situation_description.strip()}",
        f"**분류**: {label} (`{resolved}`)",
        "",
        headline,
        "",
        "### 추천 순서",
    ]

    primary = routing.get("primary", [])
    secondary = routing.get("secondary", [])
    for idx, hid in enumerate(primary, start=1):
        lines.extend(_format_hotline_block(data, hid, language=language, priority=idx))
    for idx, hid in enumerate(secondary, start=len(primary) + 1):
        lines.extend(_format_hotline_block(data, hid, language=language, priority=idx))

    if action:
        lines.extend(["", "### 다음에 할 일", action])

    if resolved == "unsure" and language == "ko":
        trio = data.get("emergency_trio", {})
        if trio.get("summary_ko"):
            lines.extend(["", "### 112 · 119 · 110", trio["summary_ko"]])

    lines.extend(["", DISCLAIMER_KO if language == "ko" else DISCLAIMER_EN])
    return "\n".join(lines)
