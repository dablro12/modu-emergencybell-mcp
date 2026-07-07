"""다국어 입력 감지 · 외국어 장소·의도 키워드 — 한국 거주 모든 사용자 지원."""

from __future__ import annotations

import re

HANGUL_RE = re.compile(r"[가-힣]")
LATIN_RE = re.compile(r"[A-Za-z]{2,}")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# 외국어 역명 → 한국어 역 키 (STATION_REGION · Kakao 검색용)
FOREIGN_STATION_ALIASES: dict[str, str] = {
    "gangnam station": "강남역",
    "myeongdong station": "명동역",
    "hongdae station": "홍대입구역",
    "hongdae entrance station": "홍대입구역",
    "itaewon station": "이태원",
    "seomyeon station": "서면역",
    "haeundae station": "해운대",
    "coex station": "코엑스",
    "seoul station": "서울역",
    "yeouido station": "여의도",
    "jiangnan station": "강남역",
    "江南站": "강남역",
    "江南": "강남역",
    "明洞站": "명동역",
    "弘大站": "홍대입구역",
    "弘大": "홍대입구역",
    "梨泰院站": "이태원",
    "海云台站": "해운대",
    "西面站": "서면역",
}

EN_PLACE_NOISE = frozenset({
    "restroom",
    "restrooms",
    "toilet",
    "toilets",
    "bathroom",
    "pharmacy",
    "hospital",
    "clinic",
    "emergency",
    "atm",
    "wifi",
    "bus",
    "stop",
    "help",
    "please",
    "urgent",
    "urgently",
    "near",
    "nearby",
    "around",
})

ZH_PLACE_NOISE = frozenset({
    "厕所",
    "洗手间",
    "卫生间",
    "药店",
    "药房",
    "医院",
    "急诊",
    "轮椅",
    "公交",
    "站",
    "附近",
    "帮助",
    "急",
})

EN_CHAT_NOISE = re.compile(
    r"\b(restroom|toilet|bathroom|urgent(?:ly)?|please|help\s*me|where\s+is|"
    r"need\s+a|asap|right\s+now)\b",
    re.IGNORECASE,
)
ZH_CHAT_NOISE = re.compile(
    r"(厕所|洗手间|卫生间|在哪|哪里|附近|急|帮帮我|怎么办)",
)

EN_SUFFIXES = (" near", " nearby", " area", " around")
ZH_SUFFIXES = ("附近", "周边", "一带", "这边")


def detect_input_language(text: str) -> str:
    """ko | en | zh | ja (휴리스틱)."""
    stripped = (text or "").strip()
    if not stripped:
        return "ko"
    hangul = len(HANGUL_RE.findall(stripped))
    cjk = len(CJK_RE.findall(stripped))
    latin = len(LATIN_RE.findall(stripped))
    if hangul >= max(cjk, latin // 3, 1) and hangul > 0:
        return "ko"
    if cjk >= latin and cjk > 0:
        return "zh"
    if latin > 0:
        return "en"
    return "ko"


def text_indicates_foreign_input(text: str) -> bool:
    return detect_input_language(text) in ("en", "zh", "ja")


def resolve_foreign_station(text: str) -> str:
    """외국어 역명 → 한국어 역·랜드마크 키."""
    lowered = (text or "").lower()
    for alias, station in sorted(FOREIGN_STATION_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in lowered or alias in (text or ""):
            return station
    return ""


def strip_multilingual_noise(query: str) -> str:
    """영·중 자연어 잡음 제거 (landmarks.strip_poi_noise 보조)."""
    cleaned = (query or "").strip()
    if not cleaned:
        return cleaned
    cleaned = EN_CHAT_NOISE.sub("", cleaned).strip(" ,.!?")
    cleaned = ZH_CHAT_NOISE.sub("", cleaned).strip(" ,.!?，。！？")
    for suffix in EN_SUFFIXES + ZH_SUFFIXES:
        if cleaned.lower().endswith(suffix.lower()) or cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned or (query or "").strip()


def foreign_intent_keywords() -> dict[str, tuple[str, ...]]:
    """classify_intents 보강용 (영·중)."""
    return {
        "restroom_en": ("restroom", "toilet", "bathroom", "poop", "bowel"),
        "restroom_zh": ("厕所", "洗手间", "卫生间", "上厕所"),
        "pharmacy_en": ("pharmacy", "medicine", "drugstore"),
        "pharmacy_zh": ("药店", "药房", "买药"),
        "clinic_en": ("clinic", "hospital", "fever", "doctor", "pediatric"),
        "clinic_zh": ("医院", "诊所", "发烧", "儿科", "看病"),
        "emergency_en": ("emergency room", "er bed", "ambulance"),
        "emergency_zh": ("急诊", "急救", "救护车"),
        "safety_en": ("safety bell", "crime", "unsafe", "scared", "at night"),
        "safety_zh": ("安全", "犯罪", "害怕", "晚上", "夜间"),
        "accessible_en": ("wheelchair", "accessible", "elevator", "disability"),
        "accessible_zh": ("轮椅", "无障碍", "电梯", "残疾"),
        "locker_en": ("locker", "luggage", "storage"),
        "locker_zh": ("储物柜", "行李", "寄存"),
        "wifi_en": ("wifi", "wi-fi", "internet"),
        "wifi_zh": ("无线", "wifi", "网络"),
        "bus_en": ("bus stop", "bus station"),
        "bus_zh": ("公交站", "公交车站", "巴士站"),
        "vet_en": ("vet", "veterinary", "animal hospital", "dog vomit", "cat sick", "pet emergency"),
        "vet_zh": ("动物医院", "宠物医院", "狗吐", "猫生病"),
        "hotlines_en": ("call", "hotline", "police", "gas leak", "missing child"),
        "hotlines_zh": ("报警", "电话", "煤气", "走失", "失踪"),
    }


def agent_translation_hint(language: str) -> str:
    """classify_emergency_intent 응답용 에이전트 가이드."""
    if language == "en":
        return (
            "Detected **English** input. Pass full `user_request` to tools; "
            "translate the final answer to English. Keep Korean addresses/facility names."
        )
    if language == "zh":
        return (
            "检测到**中文**输入。请将完整 `user_request` 传给工具；"
            "最终回答请译为中文，地址和设施名保留韩文。"
        )
    return ""
