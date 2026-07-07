"""건강보험심사평가원(HIRA) 공공데이터 API."""

from __future__ import annotations

from typing import Any

from datago_common import fetch_datago

DISEASE_BASE = "https://apis.data.go.kr/B551182/diseaseInfoService1"
HOSP_BASE = "https://apis.data.go.kr/B551182/hospInfoService1"
HOSP_DETAIL_BASE = "https://apis.data.go.kr/B551182/hospDetailInfoService1"
DRUG_USAGE_BASE = "https://apis.data.go.kr/B551182/mdcnUseInfoService1"
NON_COVERED_BASE = "https://apis.data.go.kr/B551182/nipFeeInfoService1"

HIRA_DISCLAIMER = (
    "_출처: 건강보험심사평가원 공공데이터. 진단·처방이 아니며, "
    "증상이 심하면 **119·1339**에 직접 문의하세요._"
)


async def search_disease_by_keyword(
    keyword: str,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not keyword.strip():
        return []
    rows = await fetch_datago(
        f"{DISEASE_BASE}/getDissNameCodeList1",
        {
            "pageNo": 1,
            "numOfRows": min(max(limit, 5), 20),
            "sickType": 1,
            "medTp": 1,
            "diseaseType": "SICK_CD",
            "searchText": keyword.strip(),
        },
    )
    return rows[:limit]


async def search_hospital_basis(
    *,
    sido_cd: str | None = None,
    sigungu_cd: str | None = None,
    hospital_name: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "pageNo": 1,
        "numOfRows": min(max(limit, 5), 20),
    }
    if sido_cd:
        params["sidoCd"] = sido_cd
    if sigungu_cd:
        params["sgguCd"] = sigungu_cd
    if hospital_name:
        params["yadmNm"] = hospital_name
    rows = await fetch_datago(f"{HOSP_BASE}/getHospBasisList1", params)
    return rows[:limit]


def format_disease_rows(rows: list[dict[str, Any]], *, keyword: str) -> str:
    if not rows:
        return f"질병명 **{keyword}** 관련 공공데이터를 찾지 못했습니다."

    lines = [f"## 질병 정보 (심평원) — `{keyword}`", ""]
    for idx, row in enumerate(rows, start=1):
        name = row.get("sickNm") or row.get("diseaseNm") or row.get("dissNm") or "질병"
        code = row.get("sickCd") or row.get("dissCd") or ""
        en = row.get("sickEngNm") or row.get("dissEngNm") or ""
        lines.append(f"### {idx}. {name}")
        if code:
            lines.append(f"- **코드**: {code}")
        if en:
            lines.append(f"- **영문명**: {en}")
        lines.append("")
    lines.append(HIRA_DISCLAIMER)
    return "\n".join(lines).strip()
