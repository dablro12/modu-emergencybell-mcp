"""지도 링크·이미지 URL 생성 테스트."""

from __future__ import annotations

from map_preview import (
    append_overview_map,
    build_map_image_url,
    extract_lat_lng,
    format_place_map_lines,
    kakao_map_route_url,
    kakao_map_view_url,
)


def test_kakao_map_links() -> None:
    url = kakao_map_view_url("강남역 화장실", 37.4979, 127.0276)
    assert "map.kakao.com/link/map" in url
    route = kakao_map_route_url("강남역 화장실", 37.4979, 127.0276)
    assert "link/to" in route


def test_build_map_image_url() -> None:
    url = build_map_image_url(center_lat=37.5, center_lng=127.0, title="테스트")
    assert "/img/map?" in url
    assert "lat=37.500000" in url


def test_format_place_map_lines_includes_image_for_top_rank() -> None:
    lines = format_place_map_lines("OO화장실", 37.5, 127.0, rank=1)
    assert any("카카오맵에서 보기" in line for line in lines)
    assert any(line.startswith("![") for line in lines)


def test_format_place_map_lines_no_image_after_rank_3() -> None:
    lines = format_place_map_lines("OO화장실", 37.5, 127.0, rank=4)
    assert any("카카오맵" in line for line in lines)
    assert not any(line.startswith("![") for line in lines)


def test_extract_lat_lng_aliases() -> None:
    assert extract_lat_lng({"latitude": 37.5, "longitude": 127.0}) == (37.5, 127.0)
    assert extract_lat_lng({"lat": 37.5, "lng": 127.0}) == (37.5, 127.0)


def test_append_overview_map() -> None:
    lines: list[str] = []
    append_overview_map(
        lines,
        [
            {"name": "A", "lat": 37.5, "lng": 127.0},
            {"name": "B", "lat": 37.51, "lng": 127.01},
        ],
        title="근처 화장실",
    )
    assert len(lines) >= 1
    assert lines[0].startswith("![근처 화장실]")


def test_restroom_list_has_map_links() -> None:
    from helpers import format_restroom_list

    text = format_restroom_list(
        [
            {
                "name": "테스트화장실",
                "road_address": "서울 강남구",
                "jibun_address": "",
                "latitude": 37.4979,
                "longitude": 127.0276,
                "distance_m": 100,
                "id": "t1",
                "opening": {"type_raw": "상시", "detail": "", "is_always_open": True},
                "user_types": {"tags": ["wheelchair"], "wheelchair": True, "child": False, "infant_care": False, "elderly_safety": False},
                "facilities": {"emergency_bell": False, "emergency_bell_location": "", "diaper_station": False, "diaper_station_location": ""},
                "phone": "",
            }
        ],
        query="강남역",
    )
    assert "카카오맵에서 보기" in text
    assert "/img/map?" in text
