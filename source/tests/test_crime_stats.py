"""Tests for regional crime statistics index and formatting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crime_stats import (
    format_crime_stats_brief,
    format_crime_stats_detail,
    load_index,
    lookup_from_place,
)
from scripts.process_crime_stats_data import main as build_index

INDEX_FILE = Path(__file__).resolve().parents[2] / "data" / "emergencybell" / "crime_stats_index.json"


@pytest.fixture(scope="module", autouse=True)
def ensure_crime_index() -> None:
    if not INDEX_FILE.exists():
        build_index()


def test_index_loaded():
    data = load_index()
    assert data.get("meta", {}).get("region_count", 0) >= 200


def test_lookup_gangnam():
    region = lookup_from_place(sido="서울특별시", sigungu="강남구")
    assert region is not None
    assert region["total"] > 0
    assert region["safety_total"] > 0
    assert region["by_major"]["절도범죄"] > 0


def test_lookup_from_query():
    region = lookup_from_place(query="부산 해운대구")
    assert region is not None
    assert region["sigungu"] == "해운대구"


def test_format_brief_contains_rank():
    region = lookup_from_place(sido="서울특별시", sigungu="강남구")
    text = format_crime_stats_brief(region)
    assert "치안 관련" in text
    assert "순위" in text
    assert "112" in text


def test_format_detail_has_major_categories():
    region = lookup_from_place(sido="서울특별시", sigungu="종로구")
    text = format_crime_stats_detail(region)
    assert "범죄 유형별" in text
    assert "강력범죄" in text or "절도범죄" in text


def test_foreign_region_not_indexed():
    data = load_index()
    assert not any(key.startswith("외국") for key in data.get("lookup", {}))


def test_index_json_roundtrip():
    raw = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    assert raw["regions"]
    sample = next(iter(raw["regions"].values()))
    assert "safety_detail" in sample
