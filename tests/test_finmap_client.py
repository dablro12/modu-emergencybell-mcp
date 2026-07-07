"""Tests for finmap_client helpers."""

from finmap_client import _finmap_error_hint, _parse_finmap_error


class _FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        import json

        return json.loads(self.text)


def test_parse_finmap_error_json():
    resp = _FakeResponse(400, '{"rsp_code":"163","rsp_message":"API 요청 처리 실패"}')
    assert "163" in _parse_finmap_error(resp)


def test_finmap_error_hint_211():
    assert "토큰" in _finmap_error_hint("211")
