"""외국인·병원 방문용 문장 카드 (정적 JSON)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from runtime_paths import data_path

DATA_FILE = data_path("phrases", "phrases.json")

SCENARIO_ALIASES = {
    "hospital": "hospital_visit",
    "clinic": "hospital_visit",
    "pharmacy": "pharmacy_visit",
    "emergency": "emergency_symptoms",
    "er": "emergency_symptoms",
    "allergy": "allergy",
    "pharmacy_allergy_check": "pharmacy_allergy_check",
    "pharmacy_allergy_inquiry": "pharmacy_allergy_check",
    "medicine_allergy": "pharmacy_allergy_check",
    "help": "call_help",
    "foreign": "call_help",
    "general": "call_help",
}


@lru_cache(maxsize=1)
def load_phrases() -> dict:
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _resolve_scenario(scenario: str) -> str:
    key = scenario.strip().lower()
    return SCENARIO_ALIASES.get(key, key)


def format_phrase_card(
    scenario: str = "hospital_visit",
    language: str = "en",
) -> str:
    data = load_phrases()
    scenarios = data["scenarios"]
    resolved = _resolve_scenario(scenario)

    if resolved not in scenarios:
        available = ", ".join(sorted(scenarios.keys()))
        return (
            f"Unknown scenario `{scenario}`. Available: {available}\n\n"
            "Use get_emergency_hotlines(situation=foreign_visitor) for hotline numbers first."
        )

    block = scenarios[resolved]
    lang = language if language in ("ko", "en", "ja", "zh") else "en"
    title = block.get(f"title_{lang}") or block.get("title_en", resolved)

    lines = [
        f"## Phrase card — {title}",
        f"_Show this screen to staff. {data.get('disclaimer_en', '')}_",
        "",
    ]

    for idx, phrase in enumerate(block["phrases"], start=1):
        primary = phrase.get(lang) or phrase.get("en", "")
        ko = phrase.get("ko", "")
        lines.append(f"### {idx}.")
        lines.append(f"**{lang.upper()}**: {primary}")
        if lang != "ko" and ko:
            lines.append(f"**한국어 (Korean)**: {ko}")
        for extra in ("ja", "zh"):
            if extra != lang and phrase.get(extra):
                lines.append(f"**{extra.upper()}**: {phrase[extra]}")
        lines.append("")

    reminder = data.get("hotlines_reminder", {})
    if lang == "ko":
        lines.append(f"**긴급번호**: {reminder.get('ko', '')}")
        lines.append(data.get("disclaimer_ko", ""))
    else:
        lines.append(f"**Hotlines**: {reminder.get('en', '')}")
        lines.append(data.get("disclaimer_en", ""))

    lines.append("_modu-emergencybell(모두의비상벨) — phrase card only, no translation service._")
    return "\n".join(lines)
