from landmarks import lookup_landmark_coords, lookup_landmark_region


def test_gyeongbokgung_landmark_coords_and_region() -> None:
    coords = lookup_landmark_coords("경복궁 근처 화장실")
    assert coords is not None
    lat, lng = coords
    assert 37.57 < lat < 37.59
    assert 126.97 < lng < 126.99
    assert lookup_landmark_region("경복궁") == "서울특별시 종로구"
