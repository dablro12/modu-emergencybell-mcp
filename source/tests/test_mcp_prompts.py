"""MCP Prompt 등록 테스트."""

from __future__ import annotations

import modu_emergencybell as me


def test_prompts_registered() -> None:
    names = {p.name for p in me.mcp._prompt_manager.list_prompts()}  # noqa: SLF001
    assert "urgent_restroom" in names
    assert "classify_before_call" in names
    assert len(names) >= 12
