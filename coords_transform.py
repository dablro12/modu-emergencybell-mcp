"""EPSG:5179 (Korea 2000 / Central Belt) → WGS84."""

from __future__ import annotations


def tm5179_to_wgs84(x: float, y: float) -> tuple[float, float] | None:
    """TM 좌표(행정안전부 동물시설 — EPSG:5174) → (lat, lng)."""
    try:
        from pyproj import Transformer

        transformer = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)
        lng, lat = transformer.transform(x, y)
        if not (33 <= lat <= 39 and 124 <= lng <= 132):
            return None
        return lat, lng
    except Exception:
        return None
