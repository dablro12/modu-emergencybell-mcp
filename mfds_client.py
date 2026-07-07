"""식품의약품안전처(MFDS) e약은요·DUR API."""

from __future__ import annotations

import re
from typing import Any

from datago_common import fetch_datago

EASY_DRUG_URL = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
DUR_PRODUCT_URL = "https://apis.data.go.kr/1471000/DurPrdlstInfoService/getDurPrdlstInfoList"
DUR_INGREDIENT_URL = "https://apis.data.go.kr/1471000/DurPrdlstInfoService/getDurPrdlstInfoList3"

MFDS_DISCLAIMER = (
    "_출처: 식약처 e약은요·DUR 공공데이터. **자가 진단·복용 결정이 아닙니다.** "
    "잘못 복용·중독 의심 시 **119·1339**._"
)


def _clip(text: str, limit: int = 280) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


async def search_easy_drug(
    *,
    item_name: str | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not (item_name or "").strip():
        return []
    rows = await fetch_datago(
        EASY_DRUG_URL,
        {
            "pageNo": 1,
            "numOfRows": min(max(limit, 3), 10),
            "type": "json",
            "itemName": item_name.strip(),
        },
        response_format="json",
    )
    return rows[:limit]


async def search_dur_product(
    *,
    item_name: str | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not (item_name or "").strip():
        return []
    rows = await fetch_datago(
        DUR_PRODUCT_URL,
        {
            "pageNo": 1,
            "numOfRows": min(max(limit, 3), 10),
            "type": "json",
            "itemName": item_name.strip(),
        },
        response_format="json",
    )
    return rows[:limit]


def format_easy_drug_rows(rows: list[dict[str, Any]], *, query: str) -> str:
    if not rows:
        return f"**{query}** 의약품 정보(e약은요)를 찾지 못했습니다."

    lines = [f"## 의약품 정보 (e약은요) — `{query}`", ""]
    for idx, row in enumerate(rows, start=1):
        name = row.get("itemName") or "의약품"
        entp = row.get("entpName") or ""
        lines.append(f"### {idx}. {name}")
        if entp:
            lines.append(f"- **업체**: {entp}")
        for label, key in (
            ("효능", "efcyQesitm"),
            ("사용법", "useMethodQesitm"),
            ("주의(경고)", "atpnWarnQesitm"),
            ("주의사항", "atpnQesitm"),
            ("상호작용", "intrcQesitm"),
            ("부작용", "seQesitm"),
        ):
            value = _clip(str(row.get(key) or ""))
            if value:
                lines.append(f"- **{label}**: {value}")
        lines.append("")
    lines.append(MFDS_DISCLAIMER)
    return "\n".join(lines).strip()
