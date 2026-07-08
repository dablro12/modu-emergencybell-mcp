"""증상·중독·오복용 건강 트리아지 — 심평원·식약처·NEMC 연계."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from hotlines import format_emergency_hotlines
from hira_client import format_disease_rows, search_disease_by_keyword
from intent_routing import resolve_effective_place
from mfds_client import format_easy_drug_rows, search_easy_drug
from nemc_client import (
    find_emergency_rooms_near,
    find_open_clinics_near,
    find_open_pharmacies_near,
    parse_treatment_day,
)
from place_context import is_pet_care_query

Urgency = Literal["critical", "urgent", "moderate", "low"]

TRIAGE_DISCLAIMER = (
    "⚠️ **면책**: 응급처치·진단·처방이 아닙니다. "
    "호흡곤란·의식저하·대량 출혈·경련 등은 **즉시 119**."
)

POISON_PATTERNS: tuple[tuple[tuple[str, ...], str, Urgency, str], ...] = (
    (
        ("강아지 약", "동물 약", "반려동물 약", "수의", "펫 약", "동물용"),
        "wrong_species_drug",
        "critical",
        "응급실",
    ),
    (
        ("본드", "접착제", "풀", "강력접착", "순간접착"),
        "chemical_ingestion",
        "critical",
        "응급실",
    ),
    (
        ("레고", "장난감", "블록", "작은 물건", "이물"),
        "foreign_body_child",
        "urgent",
        "소아과",
    ),
    (
        ("잘못 먹", "다른 약", "틀린 약", "오복용"),
        "wrong_drug",
        "urgent",
        "응급실",
    ),
    (
        ("삼켰", "먹었", "복용", "마셨"),
        "ingestion_general",
        "urgent",
        "응급실",
    ),
)

SYMPTOM_SPECIALTY: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("목", "인후", "목이", "목이 따", "목이 아"), "ent", "이비인후과"),
    (("두통", "머리", "어지", "현기"), "internal", "내과"),
    (("열", "발열", "39", "38", "fever"), "pediatric", "소아과"),
    (("배", "복통", "설사", "구토", "토"), "internal", "내과"),
    (("가슴", "흉통", "심장"), "emergency", "응급실"),
    (("숨", "호흡", "숨이"), "emergency", "응급실"),
    (("넘어", "쓰러", "골절", "다쳤"), "orthopedic", "정형외과"),
    (("축구", "운동", "뛰", "달린"), "internal", "내과"),
    (("피부", "발진", "가려"), "dermatology", "피부과"),
)

SPECIALTY_NEMC = {
    "pediatric": "pediatric",
    "internal": "internal",
    "ent": "internal",
    "orthopedic": "orthopedic",
    "emergency": "emergency",
    "dermatology": "general",
    "general": "general",
}

DRUG_HINTS = (
    "타이레놀",
    "acetaminophen",
    "이부프로펜",
    "판콜",
    "해열",
    "진통",
    "약",
    "medicine",
)


def _is_human_pet_drug_ingestion(text: str) -> bool:
    """True when a human seems to have taken animal medication by mistake."""
    lowered = (text or "").lower()
    pet_drug = _contains_any(text, ("강아지 약", "고양이 약", "동물 약", "반려동물 약", "수의", "펫 약", "동물용"))
    human_ingestion = _contains_any(text, ("내 약", "사람", "인 줄", "잘못 먹", "먹었", "복용", "삼켰", "mistook", "human"))
    return pet_drug and human_ingestion


@dataclass
class TriageResult:
    urgency: Urgency
    category: str
    specialty: str
    department_ko: str
    first_actions: list[str]
    hotline_situation: str | None
    drug_query: str | None
    disease_keyword: str | None


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(k in text or k in lowered for k in keywords)


def classify_health_urgency(text: str) -> Urgency:
    if _contains_any(text, ("의식", "경련", "숨", "호흡곤란", "대량 출혈", "쓰러", "의식없")):
        return "critical"
    if _contains_any(text, ("본드", "접착제", "강아지 약", "동물 약", "오복용", "삼켰", "먹었")):
        return "urgent" if "본드" not in text and "강아지" not in text else "critical"
    if _contains_any(text, ("39", "40", "응급", "급해", "급한")):
        return "urgent"
    if _contains_any(text, ("아파", "아픈", "쑤시", "불편", "어떻게")):
        return "moderate"
    return "low"


def analyze_health_request(text: str) -> TriageResult:
    urgency = classify_health_urgency(text)
    category = "symptom"
    specialty = "general"
    department = "내과·가정의학과"
    actions: list[str] = []
    hotline: str | None = None
    drug_query: str | None = None
    disease_kw: str | None = None

    for keywords, cat, urg, dept in POISON_PATTERNS:
        if _contains_any(text, keywords):
            category = cat
            urgency = urg
            department = dept
            specialty = "emergency" if "응급" in dept else "pediatric"
            hotline = "poison"
            actions = [
                "지금 당장 **추가 복용·삼키게 하지 마세요.**",
                "먹은 것·양·시간을 메모하고 **1339**(응급의료상담) 또는 **119**에 문의하세요.",
                "구토 유도는 전문가 지시 없이 하지 마세요.",
            ]
            if cat == "foreign_body_child":
                actions.append("작은 이물 삼킴 — **소아과·응급실**에서 영상 확인이 필요할 수 있습니다.")
            if cat == "wrong_species_drug":
                actions.append("동물용 의약품은 사람에게 **절대 복용하지 마세요.** 포장·성분표를 지참하세요.")
            if cat == "chemical_ingestion":
                actions.append("접착제·화학물질 — **119** 또는 **1339**에 즉시 연락하세요.")
            break

    if category == "symptom":
        for keywords, spec, dept_ko in SYMPTOM_SPECIALTY:
            if _contains_any(text, keywords):
                specialty = spec
                department = dept_ko
                disease_kw = keywords[0]
                break
        if _contains_any(text, ("약", "먹어야", "복용")):
            category = "drug_question"
            hotline = "medical_urgent"
            for hint in DRUG_HINTS:
                if hint in text:
                    drug_query = hint
                    break
            if not drug_query:
                drug_query = "해열진통제"
        actions = [
            f"증상 기준 추천 진료과: **{department}** (공공데이터·키워드 기반, 확정 진단 아님).",
            "증상이 악화되거나 호흡곤란·의식 변화가 있으면 **119**.",
            "야간·주말이면 **1339**에 어느 과·어디로 갈지 상담 가능.",
        ]
        if _contains_any(text, ("축구", "운동")) and _contains_any(text, ("목", "두통", "머리")):
            actions.insert(
                0,
                "운동 직후 목·두통 — **탈수·과호흡·목 근육 긴장** 가능. 물을 조금씩 마시고 휴식 후에도 지속되면 진료.",
            )

    if not actions:
        actions = ["상황을 **1339**에 설명하고 이동할 병원·과를 상담하세요."]

    return TriageResult(
        urgency=urgency,
        category=category,
        specialty=specialty,
        department_ko=department,
        first_actions=actions,
        hotline_situation=hotline,
        drug_query=drug_query,
        disease_keyword=disease_kw,
    )


def _urgency_label(urgency: Urgency) -> str:
    return {
        "critical": "🚨 **즉시 신고·응급**",
        "urgent": "⚠️ **빠른 진료·상담 필요**",
        "moderate": "🟡 **당일·가까운 의원·병원**",
        "low": "🟢 **가벼운 상담·자가관리 가능성**",
    }[urgency]


async def health_triage(
    user_request: str,
    place_query: str | None = None,
    language: str = "ko",
) -> str:
    if is_pet_care_query(user_request) and not _is_human_pet_drug_ingestion(user_request):
        from outdoor_services import find_outdoor_service

        effective, _ = await resolve_effective_place(
            place_query=place_query,
            user_request=user_request,
            fallback="서울",
        )
        return (
            "## 건강 트리아지\n"
            "반려동물 건강 문의는 사람 의료 트리아지가 아닙니다.\n\n"
            + await find_outdoor_service(place_query=effective, service="vet_hospital", limit=5)
        )

    effective, place_ctx = await resolve_effective_place(
        place_query=place_query,
        user_request=user_request,
        fallback="서울",
    )
    place = effective or place_ctx.expanded_query or "서울"
    triage = analyze_health_request(user_request)
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    qt, time_note = parse_treatment_day(None, kst=now)

    sections: list[str] = [
        "## 건강 트리아지 (모두의비상벨)",
        f"**질문**: {user_request.strip()}",
        f"**기준 지역**: {place}",
        f"**긴급도**: {_urgency_label(triage.urgency)}",
        f"**추천 진료과**: {triage.department_ko}",
        "",
        TRIAGE_DISCLAIMER,
        "",
        "### 지금 할 일",
    ]
    for step in triage.first_actions:
        sections.append(f"- {step}")

    situation = triage.hotline_situation or (
        "life_threatening" if triage.urgency == "critical" else "medical_urgent"
    )
    sections.append("")
    sections.append(
        format_emergency_hotlines(
            user_request,
            situation=situation,
            language=language if language in ("ko", "en") else "ko",
        )
    )

    if triage.disease_keyword:
        try:
            rows = await search_disease_by_keyword(triage.disease_keyword, limit=2)
            if rows:
                sections.append(format_disease_rows(rows, keyword=triage.disease_keyword))
        except Exception as exc:  # noqa: BLE001
            sections.append(f"_질병정보 API: {exc}_")

    if triage.drug_query:
        try:
            rows = await search_easy_drug(item_name=triage.drug_query, limit=2)
            if rows:
                sections.append(format_easy_drug_rows(rows, query=triage.drug_query))
        except Exception as exc:  # noqa: BLE001
            sections.append(f"_e약은요 API: {exc}_")

    nemc_specialty = SPECIALTY_NEMC.get(triage.specialty, "general")
    sections.append("")
    sections.append("### 가까운 의료기관")
    if triage.urgency in ("critical", "urgent") or triage.category.startswith(
        ("chemical", "wrong", "ingestion", "foreign")
    ):
        try:
            sections.append(await find_emergency_rooms_near(place_query=place, limit=3))
        except Exception as exc:  # noqa: BLE001
            sections.append(f"_응급실 API: {exc}_")
    try:
        sections.append(
            await find_open_clinics_near(
                place_query=place,
                specialty=nemc_specialty,
                treatment_day=qt,
                limit=5,
            )
        )
    except Exception as exc:  # noqa: BLE001
        sections.append(f"_진료 병원 API: {exc}_")
    if triage.category in ("drug_question", "symptom") or triage.urgency != "low":
        try:
            sections.append(
                await find_open_pharmacies_near(place_query=place, treatment_day=qt, limit=3)
            )
        except Exception as exc:  # noqa: BLE001
            sections.append(f"_약국 API: {exc}_")
    if time_note:
        sections.append(f"_{time_note}_")

    return "\n\n---\n\n".join(s for s in sections if s and s.strip())
