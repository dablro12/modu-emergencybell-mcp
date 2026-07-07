"""카카오맵 링크·정적 지도 이미지 URL (draw_shabby 스타일 마크다운)."""

from __future__ import annotations

import math
import os
from typing import Any
from urllib.parse import quote, urlencode

import httpx

PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    "https://modu-emergencybell-mcp.playmcp-endpoint.kakaocloud.io",
).rstrip("/")

KAKAO_STATIC_MAP = "https://dapi.kakao.com/v2/maps/staticmap"
OSM_STATIC_MAP = "https://staticmap.openstreetmap.de/staticmap.php"


def _safe_label(name: str, *, limit: int = 36) -> str:
    text = (name or "위치").strip()
    return text[:limit] if len(text) > limit else text


def kakao_map_view_url(name: str, lat: float, lng: float) -> str:
    label = quote(_safe_label(name), safe="")
    return f"https://map.kakao.com/link/map/{label},{lat},{lng}"


def kakao_map_route_url(name: str, lat: float, lng: float) -> str:
    label = quote(_safe_label(name), safe="")
    return f"https://map.kakao.com/link/to/{label},{lat},{lng}"


def _centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    lat = sum(p[0] for p in points) / len(points)
    lng = sum(p[1] for p in points) / len(points)
    return lat, lng


def _map_level(points: list[tuple[float, float]]) -> int:
    if len(points) <= 1:
        return 3
    max_span = 0.0
    for i, (lat1, lng1) in enumerate(points):
        for lat2, lng2 in points[i + 1 :]:
            span = max(abs(lat1 - lat2), abs(lng1 - lng2))
            max_span = max(max_span, span)
    if max_span > 0.08:
        return 6
    if max_span > 0.03:
        return 5
    if max_span > 0.01:
        return 4
    return 3


def build_map_image_url(
    *,
    center_lat: float,
    center_lng: float,
    markers: list[tuple[float, float]] | None = None,
    width: int = 480,
    height: int = 300,
    title: str = "지도",
) -> str:
    marker_pairs = markers or [(center_lat, center_lng)]
    marker_param = "|".join(f"{lng:.6f},{lat:.6f}" for lat, lng in marker_pairs[:5])
    params = {
        "lat": f"{center_lat:.6f}",
        "lng": f"{center_lng:.6f}",
        "w": str(width),
        "h": str(height),
        "m": marker_param,
        "t": _safe_label(title, limit=24),
    }
    return f"{PUBLIC_BASE_URL}/img/map?{urlencode(params)}"


def extract_lat_lng(item: dict[str, Any]) -> tuple[float, float] | None:
    lat = item.get("latitude") or item.get("lat")
    lng = item.get("longitude") or item.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def format_place_map_lines(
    name: str,
    lat: float | None,
    lng: float | None,
    *,
    include_image: bool = True,
    rank: int = 1,
) -> list[str]:
    if lat is None or lng is None:
        return []
    lines = [
        f"- **지도**: [카카오맵에서 보기]({kakao_map_view_url(name, lat, lng)})",
        f"- **길찾기**: [여기로 안내]({kakao_map_route_url(name, lat, lng)})",
    ]
    if include_image and rank <= 3:
        lines.append(
            f"![{_safe_label(name)} 위치]({build_map_image_url(center_lat=lat, center_lng=lng, title=name)})"
        )
    return lines


def append_overview_map(
    lines: list[str],
    items: list[dict[str, Any]],
    *,
    title: str,
) -> None:
    points: list[tuple[float, float]] = []
    for item in items[:3]:
        coords = extract_lat_lng(item)
        if coords:
            points.append(coords)
    if not points:
        return
    center = _centroid(points)
    url = build_map_image_url(
        center_lat=center[0],
        center_lng=center[1],
        markers=points,
        title=title,
    )
    lines.append(f"![{title}]({url})")
    lines.append("")


def enrich_result_lines(
    lines: list[str],
    *,
    name: str,
    item: dict[str, Any],
    rank: int,
    include_image: bool = True,
) -> None:
    coords = extract_lat_lng(item)
    if not coords:
        return
    lat, lng = coords
    lines.extend(
        format_place_map_lines(
            name,
            lat,
            lng,
            include_image=include_image,
            rank=rank,
        )
    )


async def fetch_static_map_png(
    *,
    center_lat: float,
    center_lng: float,
    markers: list[tuple[float, float]],
    width: int = 480,
    height: int = 300,
) -> bytes:
    marker_param = "|".join(f"{lng:.6f},{lat:.6f}" for lat, lng in markers[:5])
    level = _map_level(markers)
    api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()

    if api_key:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    KAKAO_STATIC_MAP,
                    headers={"Authorization": f"KakaoAK {api_key}"},
                    params={
                        "center": f"{center_lng:.6f},{center_lat:.6f}",
                        "level": level,
                        "w": min(max(width, 80), 800),
                        "h": min(max(height, 80), 800),
                        "markers": f"size:small|{marker_param}",
                    },
                )
                if response.status_code == 200 and "image" in (response.headers.get("content-type") or ""):
                    return response.content
        except (httpx.HTTPError, OSError):
            pass

    return await _fetch_osm_static_map(
        center_lat=center_lat,
        center_lng=center_lng,
        markers=markers,
        width=width,
        height=height,
    )


async def _fetch_osm_static_map(
    *,
    center_lat: float,
    center_lng: float,
    markers: list[tuple[float, float]],
    width: int,
    height: int,
) -> bytes:
    marker_chunks = [f"{lat:.6f},{lng:.6f},red-pushpin" for lat, lng in markers[:5]]
    params: dict[str, str | int] = {
        "center": f"{center_lat:.6f},{center_lng:.6f}",
        "zoom": 16 if len(markers) <= 1 else 15,
        "size": f"{min(width, 640)}x{min(height, 640)}",
    }
    if marker_chunks:
        params["markers"] = "|".join(marker_chunks)

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(OSM_STATIC_MAP, params=params)
        response.raise_for_status()
        return response.content


def register_map_routes(mcp: Any) -> None:
    from starlette.requests import Request
    from starlette.responses import Response

    @mcp.custom_route("/img/map", methods=["GET"])
    async def map_image(request: Request) -> Response:
        try:
            center_lat = float(request.query_params.get("lat", "0"))
            center_lng = float(request.query_params.get("lng", "0"))
        except ValueError:
            return Response("invalid coordinates", status_code=400)

        width = int(request.query_params.get("w", "480"))
        height = int(request.query_params.get("h", "300"))
        raw_markers = request.query_params.get("m", "")
        markers: list[tuple[float, float]] = []
        if raw_markers:
            for chunk in raw_markers.split("|"):
                parts = chunk.split(",")
                if len(parts) != 2:
                    continue
                try:
                    lng, lat = float(parts[0]), float(parts[1])
                    if math.isfinite(lat) and math.isfinite(lng):
                        markers.append((lat, lng))
                except ValueError:
                    continue
        if not markers:
            markers = [(center_lat, center_lng)]

        try:
            png = await fetch_static_map_png(
                center_lat=center_lat,
                center_lng=center_lng,
                markers=markers,
                width=width,
                height=height,
            )
        except (httpx.HTTPError, OSError) as exc:
            return Response(f"map render failed: {exc}", status_code=502)

        return Response(
            content=png,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )
