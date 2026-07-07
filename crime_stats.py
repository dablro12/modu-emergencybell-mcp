"""경찰청 지역별 범죄 발생 통계 — 안전비상벨·통합 안내 보조."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from region_parse import region_full_prefix

DATA_FILE = Path(__file__).resolve().parent / "data" / "emergencybell" / "crime_stats_index.json"

CRIME_DISCLAIMER = (
    "_출처: 경찰청 범죄 발생 지역별 통계(2024년). "
    "발생 건수 기준이며 **실시간 위험·범죄 예측이 아닙니다**. "
    "위급 시 **112**에 신고하세요._"
)

SAFETY_LABELS = {
    "살인기수": "살인(기수)",
    "살인미수등": "살인(미수 등)",
    "강도": "강도",
    "강간": "강간",
    "유사강간": "유사강간",
    "강제추행": "강제추행",
    "기타 강간/강제추행등": "기타 성범죄",
    "절도범죄": "절도",
    "폭행": "폭행",
    "상해": "상해",
    "협박": "협박",
}


@lru_cache(maxsize=1)
def load_index() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {"meta": {}, "regions": {}, "lookup": {}}
    with DATA_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def lookup_region(*, sido: str = "", sigungu: str = "", column: str = "") -> dict[str, Any] | None:
    index = load_index()
    lookup = index.get("lookup", {})
    regions = index.get("regions", {})

    candidates: list[str] = []
    if column:
        candidates.append(column)
    if sido and sigungu:
        candidates.append(f"{sido}|{sigungu}")
        candidates.append(f"{sido} {sigungu}")
    if sigungu and not sido:
        candidates.append(sigungu)

    for candidate in candidates:
        key = lookup.get(candidate)
        if key and key in regions:
            return regions[key]
    return None


def lookup_from_place(*, sido: str = "", sigungu: str = "", query: str = "") -> dict[str, Any] | None:
    region = lookup_region(sido=sido, sigungu=sigungu)
    if region:
        return region
    if query:
        from region_parse import parse_place_query

        parsed_sido, parsed_sigungu = parse_place_query(query)
        return lookup_region(sido=parsed_sido or sido, sigungu=parsed_sigungu or sigungu)
    return None


def _format_count(value: int) -> str:
    return f"{value:,}"


def _top_safety_lines(region: dict[str, Any], *, limit: int = 4) -> list[str]:
    detail = region.get("safety_detail") or {}
    ranked = sorted(
        ((name, count) for name, count in detail.items() if count > 0),
        key=lambda item: -item[1],
    )
    lines: list[str] = []
    for name, count in ranked[:limit]:
        label = SAFETY_LABELS.get(name, name)
        lines.append(f"{label} {_format_count(count)}건")
    return lines


def format_crime_stats_brief(region: dict[str, Any]) -> str:
    label = region_full_prefix(region.get("sido", ""), region.get("sigungu", ""))
    safety_total = int(region.get("safety_total") or 0)
    total = int(region.get("total") or 0)
    rank = region.get("sido_rank_safety_total")
    sido_count = region.get("sido_count")

    lines = [
        f"### 지역 범죄 발생 현황 ({label})",
        f"- **치안 관련 3대 범죄**(강력·절도·폭력): **{_format_count(safety_total)}건** / 전체 **{_format_count(total)}건**",
    ]
    if rank and sido_count:
        lines.append(f"- {region.get('sido', '').replace('특별시', '').replace('광역시', '')} 내 순위: **{rank}위 / {sido_count}** (치안 관련 기준)")

    highlights = _top_safety_lines(region)
    if highlights:
        lines.append(f"- 주요 항목: {' · '.join(highlights)}")
    lines.append(CRIME_DISCLAIMER)
    return "\n".join(lines)


def format_crime_stats_detail(region: dict[str, Any]) -> str:
    label = region_full_prefix(region.get("sido", ""), region.get("sigungu", ""))
    by_major = region.get("by_major") or {}
    total = int(region.get("total") or 0)
    safety_total = int(region.get("safety_total") or 0)

    lines = [
        f"## {label} 범죄 발생 통계 (2024년)",
        f"- 전체 발생: **{_format_count(total)}건**",
        f"- 치안 관련(강력·절도·폭력): **{_format_count(safety_total)}건**",
        "",
        "### 범죄 유형별",
    ]
    for major, count in sorted(by_major.items(), key=lambda item: -item[1])[:8]:
        lines.append(f"- {major}: {_format_count(int(count))}건")

    rank_total = region.get("sido_rank_total")
    rank_safety = region.get("sido_rank_safety_total")
    sido_count = region.get("sido_count")
    if sido_count and (rank_total or rank_safety):
        lines.append("")
        lines.append("### 동일 시·도 내 순위")
        if rank_safety:
            lines.append(f"- 치안 관련 3대 범죄: **{rank_safety}위 / {sido_count}**")
        if rank_total:
            lines.append(f"- 전체 발생: **{rank_total}위 / {sido_count}**")

    detail_lines = _top_safety_lines(region, limit=6)
    if detail_lines:
        lines.append("")
        lines.append("### 야간·외출 안전 참고 항목")
        for item in detail_lines:
            lines.append(f"- {item}")

    lines.append("")
    lines.append(CRIME_DISCLAIMER)
    lines.append("")
    lines.append(
        "_길·공원 **안전비상벨** 위치는 `find_safety_bell`로, "
        "아동·청소년 보호시설은 `find_safe_place`로 조회할 수 있습니다._"
    )
    return "\n".join(lines)


async def crime_stats_for_place(
    *,
    place_query: str | None = None,
    sido: str = "",
    sigungu: str = "",
    brief: bool = False,
) -> str | None:
    region = lookup_from_place(sido=sido, sigungu=sigungu, query=place_query or "")
    if not region:
        return None
    if brief:
        return format_crime_stats_brief(region)
    return format_crime_stats_detail(region)
