#!/usr/bin/env python3
"""Crawl PlayMCP listing pages 0-20 via public API."""

import csv
import json
import time
from pathlib import Path

import requests

BASE_URL = "https://playmcp.kakao.com/api/v1/mcps"
OUTPUT_DIR = Path("/workspace/data/crawled_data")
START_PAGE = 0
END_PAGE = 20
PAGE_SIZE = 12
SORT_BY = "FEATURED_LEVEL"
REQUEST_DELAY = 0.3


def fetch_page(page: int) -> dict:
    params = {
        "page": page,
        "sortBy": SORT_BY,
        "pageSize": PAGE_SIZE,
    }
    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_mcp_summary(mcp: dict) -> dict:
    tools = mcp.get("formattedTools") or []
    team = mcp.get("teamProfile") or {}
    classification = team.get("classification") or {}
    image = mcp.get("image") or {}

    return {
        "id": mcp.get("id"),
        "name": mcp.get("name"),
        "identify_name": mcp.get("identifyName"),
        "description": mcp.get("description"),
        "author": team.get("name"),
        "author_type": classification.get("type"),
        "tool_count": len(tools),
        "tools": [t.get("name") for t in tools],
        "monthly_tool_call_count": mcp.get("monthlyToolCallCount"),
        "total_tool_call_count": mcp.get("totalToolCallCount"),
        "featured_level": mcp.get("featuredLevel"),
        "status": mcp.get("status"),
        "applicable_ai_scope": mcp.get("applicableAIServiceScope"),
        "auth_type": (mcp.get("authConfigSummary") or {}).get("type"),
        "image_url": image.get("fullUrl"),
        "starter_messages": mcp.get("starterMessages") or [],
        "detail_url": f"https://playmcp.kakao.com/mcp/{mcp.get('identifyName')}",
    }


def save_page(page: int, data: dict) -> None:
    page_path = OUTPUT_DIR / f"page_{page}.json"
    with page_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_combined_csv(all_mcps: list[dict]) -> None:
    csv_path = OUTPUT_DIR / "playmcp_all.csv"
    if not all_mcps:
        return

    fieldnames = list(all_mcps[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_mcps:
            row_copy = dict(row)
            row_copy["tools"] = "|".join(row_copy.get("tools") or [])
            row_copy["starter_messages"] = "|".join(row_copy.get("starter_messages") or [])
            writer.writerow(row_copy)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_mcps: list[dict] = []
    meta: dict = {}

    for page in range(START_PAGE, END_PAGE + 1):
        print(f"Fetching page {page}...")
        data = fetch_page(page)
        save_page(page, data)

        if not meta:
            meta = {
                "total_pages": data.get("totalPages"),
                "total_elements": data.get("totalElements"),
                "page_size": PAGE_SIZE,
                "sort_by": SORT_BY,
                "source_url_template": "https://playmcp.kakao.com/?page={page}",
                "api_url": BASE_URL,
            }

        for mcp in data.get("content", []):
            summary = extract_mcp_summary(mcp)
            summary["source_page"] = page
            all_mcps.append(summary)

        time.sleep(REQUEST_DELAY)

    with (OUTPUT_DIR / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    with (OUTPUT_DIR / "playmcp_all.json").open("w", encoding="utf-8") as f:
        json.dump(all_mcps, f, ensure_ascii=False, indent=2)

    save_combined_csv(all_mcps)

    print(f"\nDone. Collected {len(all_mcps)} MCPs from pages {START_PAGE}-{END_PAGE}.")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
