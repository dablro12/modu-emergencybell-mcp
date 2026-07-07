"""Kakao + juso 하이브리드 장소 해석 — 좌표·시·구·동 통합."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from juso_client import resolve_administrative
from kakao_local import (
    _geocode_anchor,
    extract_admin_from_document,
    geocode_via_kakao_candidates,
    search_address,
)
from landmarks import (
    lookup_landmark_coords,
    lookup_landmark_region,
    lookup_sido_centroid,
    resolve_landmark_poi,
    strip_poi_noise,
)
from place_context import expand_place_query
from region_parse import (
    extract_sido_hint,
    normalize_place_query,
    parse_place_query,
    region_full_prefix,
)

POI_HINTS = ("역", "coex", "코엑스", "공원", "해변", "시장", "몰", "백화점", "터미널", "공항", "성당")


@dataclass
class PlaceContext:
    query: str
    expanded_query: str = ""
    latitude: float | None = None
    longitude: float | None = None
    sido: str = ""
    sigungu: str = ""
    dong: str = ""
    confidence: str = "low"
    source: str = "unknown"
    warning: str | None = None
    candidates: list[dict[str, str]] = field(default_factory=list)

    @property
    def region_prefix(self) -> str:
        return region_full_prefix(self.sido, self.sigungu)

    @property
    def coords(self) -> tuple[float, float] | None:
        if self.latitude is not None and self.longitude is not None:
            return self.latitude, self.longitude
        return None

    def apply_admin(self, *, sido: str, sigungu: str, dong: str = "") -> None:
        if sido:
            self.sido = sido
        if sigungu:
            self.sigungu = sigungu
        if dong:
            self.dong = dong

    def apply_coords(self, lat: float, lng: float) -> None:
        self.latitude = lat
        self.longitude = lng


def _prefer_keyword(query: str) -> bool:
    text = query.strip().lower()
    if "역" in query:
        return True
    if any(h in text for h in POI_HINTS):
        return True
    if query.endswith(("동", "구", "군", "시", "도")):
        return False
    return len(query.strip()) <= 12


def _prefer_juso(query: str) -> bool:
    return query.endswith(("동", "구", "군")) or " " in query.strip()


def _is_latin_query(query: str) -> bool:
    from juso_client import is_latin_address_query

    return is_latin_address_query(query)


def _confidence_rank(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(value, 0)


def _set_confidence(ctx: PlaceContext, level: str) -> None:
    if _confidence_rank(level) >= _confidence_rank(ctx.confidence):
        ctx.confidence = level


def _apply_kakao_doc(ctx: PlaceContext, doc: dict[str, Any], source: str) -> None:
    sido, sigungu, dong = extract_admin_from_document(doc)
    ctx.apply_admin(sido=sido, sigungu=sigungu, dong=dong)
    coords = None
    if doc.get("y") and doc.get("x"):
        coords = (float(doc["y"]), float(doc["x"]))
    if coords:
        ctx.apply_coords(coords[0], coords[1])
    ctx.source = source
    _set_confidence(ctx, "high" if ctx.coords and ctx.sigungu else "medium")
    label = doc.get("place_name") or doc.get("address_name") or doc.get("road_address_name")
    if label and not ctx.expanded_query:
        ctx.expanded_query = str(label)


def _apply_juso(ctx: PlaceContext, row: dict[str, str]) -> None:
    ctx.apply_admin(sido=row["sido"], sigungu=row["sigungu"], dong=row.get("dong", ""))
    ctx.expanded_query = row.get("expanded_query") or ctx.expanded_query
    ctx.source = "juso_eng" if row.get("lang") == "en" else "juso"
    if row.get("lang") == "en" and row.get("display_addr_en"):
        ctx.warning = (
            f"영문 주소 `{row['display_addr_en']}` → "
            f"한글 `{row.get('road_addr') or ctx.expanded_query}` 로 해석했습니다."
        )
    _set_confidence(ctx, "high")


async def _geocode_juso_address(ctx: PlaceContext, address: str, *, sido_hint: str) -> None:
    docs = await search_address(address, size=3)
    for doc in docs:
        if sido_hint and sido_hint not in str(doc):
            continue
        coords = None
        if doc.get("y") and doc.get("x"):
            coords = (float(doc["y"]), float(doc["x"]))
        if coords:
            ctx.apply_coords(coords[0], coords[1])
            if ctx.source == "juso":
                ctx.source = "juso+kakao_address"
            _set_confidence(ctx, "high")
            return
        _apply_kakao_doc(ctx, doc, "kakao_address")


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _apply_landmark_poi_override(ctx: PlaceContext, query: str) -> None:
    poi = resolve_landmark_poi(query)
    if not poi:
        return
    lm_coords, lm_region, keyword = poi
    if lm_region and not ctx.sigungu:
        sido, sigungu = parse_place_query(lm_region)
        ctx.apply_admin(sido=sido, sigungu=sigungu)
        if ctx.source == "unknown":
            ctx.source = "landmark_region"

    label = f"{ctx.expanded_query or ''} {ctx.query or ''}"
    keyword_in_label = keyword in label or keyword.lower() in label.lower()
    should_override = False
    if ctx.coords:
        dist = _haversine_m(ctx.coords[0], ctx.coords[1], lm_coords[0], lm_coords[1])
        should_override = dist > 120 or (not keyword_in_label and len(keyword) >= 4)
    else:
        should_override = True

    if should_override:
        ctx.apply_coords(lm_coords[0], lm_coords[1])
        ctx.source = "landmark_poi" if ctx.source == "unknown" else f"landmark_poi+{ctx.source}"
        _set_confidence(ctx, "medium")
        if keyword not in (ctx.expanded_query or ""):
            ctx.expanded_query = f"{lm_region} {keyword}".strip()


async def resolve_place_context(query: str) -> PlaceContext:
    """자연어 장소 → 좌표·행정구역 (Kakao 1순위 POI, juso 2순위 주소)."""
    raw = (query or "").strip()
    stripped = strip_poi_noise(raw) or raw
    ctx = PlaceContext(query=raw)
    if not stripped:
        return ctx

    normalized = normalize_place_query(stripped)
    expanded = expand_place_query(normalized)
    ctx.expanded_query = expanded or normalized
    sido_hint = extract_sido_hint(ctx.expanded_query) or extract_sido_hint(stripped)
    anchor = _geocode_anchor(ctx.expanded_query, sido_hint)

    prefer_keyword = _prefer_keyword(stripped) or _prefer_keyword(ctx.expanded_query)

    coords, doc, source = await geocode_via_kakao_candidates(
        ctx.expanded_query,
        sido_hint=sido_hint,
        prefer_keyword=prefer_keyword,
        anchor=anchor,
    )
    if doc:
        _apply_kakao_doc(ctx, doc, source)
    elif coords:
        ctx.apply_coords(coords[0], coords[1])
        ctx.source = source or "kakao"
        _set_confidence(ctx, "medium")

    need_juso = (
        (not ctx.sigungu or _prefer_juso(stripped))
        and _prefer_juso(ctx.expanded_query)
    ) or (not ctx.sigungu and stripped.endswith("동"))
    latin_query = _is_latin_query(stripped) or _is_latin_query(ctx.expanded_query)
    if need_juso or (not ctx.sigungu and not prefer_keyword) or latin_query:
        from juso_client import is_latin_address_query

        prefer_en = is_latin_address_query(stripped) or is_latin_address_query(ctx.expanded_query)
        juso = await resolve_administrative(ctx.expanded_query, prefer_english=prefer_en)
        if not juso and expanded != stripped:
            juso = await resolve_administrative(stripped, prefer_english=prefer_en)
        if juso:
            _apply_juso(ctx, juso)
            if not ctx.coords:
                addr = juso.get("road_addr") or juso.get("jibun_addr") or ""
                if addr:
                    await _geocode_juso_address(ctx, addr, sido_hint=sido_hint)

    if not ctx.sigungu:
        landmark_region = lookup_landmark_region(stripped) or lookup_landmark_region(
            ctx.expanded_query
        )
        if landmark_region:
            sido, sigungu = parse_place_query(landmark_region)
            ctx.apply_admin(sido=sido, sigungu=sigungu)
            if ctx.source == "unknown":
                ctx.source = "landmark_region"
            _set_confidence(ctx, "medium")

    if not ctx.sigungu:
        sido, sigungu = parse_place_query(ctx.expanded_query)
        if sido:
            ctx.apply_admin(sido=sido, sigungu=sigungu)
            if ctx.source == "unknown":
                ctx.source = "parse_place_query"
            _set_confidence(ctx, "medium")

    if not ctx.coords:
        landmark = lookup_landmark_coords(stripped) or lookup_landmark_coords(
            ctx.expanded_query
        )
        if landmark:
            ctx.apply_coords(landmark[0], landmark[1])
            if ctx.source == "unknown":
                ctx.source = "landmark"
            ctx.warning = (
                "랜드마크 좌표 추정치입니다. **구·동·역** 이름을 더 구체적으로 알려주세요."
            )
            _set_confidence(ctx, "low")
        elif sido_hint and not ctx.sigungu:
            centroid = lookup_sido_centroid(sido_hint)
            if centroid:
                ctx.apply_coords(centroid[0], centroid[1])
                ctx.source = "sido_centroid"
                ctx.warning = (
                    "시·도 중심 좌표 추정치입니다. **동·역** 이름을 포함해 주세요."
                )
                _set_confidence(ctx, "low")
        elif not ctx.coords and ctx.sigungu:
            ctx.warning = (
                "행정구역은 특정했으나 좌표를 찾지 못했습니다. "
                "반경 검색 정확도가 낮을 수 있습니다."
            )

    if ctx.sido and not ctx.expanded_query:
        ctx.expanded_query = " ".join(
            part for part in (ctx.sido, ctx.sigungu, ctx.dong) if part
        ).strip()
    elif ctx.sido and ctx.sigungu and ctx.expanded_query == stripped:
        ctx.expanded_query = region_full_prefix(ctx.sido, ctx.sigungu)
        if ctx.dong and ctx.dong not in ctx.expanded_query:
            ctx.expanded_query = f"{ctx.expanded_query} {ctx.dong}".strip()

    _apply_landmark_poi_override(ctx, stripped)
    if raw != stripped:
        _apply_landmark_poi_override(ctx, raw)

    return ctx
