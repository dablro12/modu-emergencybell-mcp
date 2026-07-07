from __future__ import annotations

from nemc_client import format_clinic_list, format_er_list, format_pharmacy_list


def test_format_clinic_includes_map_links() -> None:
    text = format_clinic_list(
        [
            {
                "dutyName": "테스트의원",
                "dutyAddr": "서울 종로구",
                "wgs84Lat": "37.5723",
                "wgs84Lon": "126.9794",
            }
        ],
        region_label="서울 종로구",
        treatment_day="6",
        specialty="general",
    )
    assert "카카오맵에서 보기" in text
    assert "/img/map?" in text


def test_format_pharmacy_includes_map_links() -> None:
    text = format_pharmacy_list(
        [
            {
                "dutyName": "테스트약국",
                "dutyAddr": "서울 종로구",
                "wgs84Lat": "37.5723",
                "wgs84Lon": "126.9794",
            }
        ],
        region_label="서울 종로구",
        treatment_day="6",
    )
    assert "카카오맵에서 보기" in text
    assert "/img/map?" in text


def test_format_er_includes_map_links() -> None:
    text = format_er_list(
        [
            {
                "dutyName": "테스트응급실",
                "wgs84Lat": "37.5723",
                "wgs84Lon": "126.9794",
                "hvec": "3",
            }
        ],
        region_label="서울 종로구",
    )
    assert "카카오맵에서 보기" in text
    assert "/img/map?" in text
