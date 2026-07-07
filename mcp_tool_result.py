"""MCP Tool 응답 — isError 패턴 (프로토콜 권장)."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

FAILURE_MARKERS = (
    "찾지 못했습니다",
    "찾을 수 없습니다",
    "정보를 찾지 못했습니다",
    "찾으려면 **",
    "지원하지 않는 service",
    "서비스 오류:",
    "시설 ID `",
    "정보를 찾지 못했습니다",
)

# 라우팅·핫라인은 '찾지 못했습니다'가 없어도 정상 응답
NO_ERROR_TOOLS = frozenset({"classify_emergency_intent", "get_emergency_hotlines", "get_phrase_card"})


def is_failure_text(text: str) -> bool:
    return any(marker in text for marker in FAILURE_MARKERS)


def tool_result(text: str, *, is_error: bool | None = None) -> CallToolResult | str:
    """문자열 Tool 결과 → 실패 시 CallToolResult(isError=True)."""
    if is_error is None:
        is_error = is_failure_text(text)
    if not is_error:
        return text
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        isError=True,
    )


def tool_error(message: str) -> CallToolResult:
    body = message if message.startswith("서비스 오류:") else f"서비스 오류: {message}"
    return CallToolResult(
        content=[TextContent(type="text", text=body)],
        isError=True,
    )


def _wrap_tool_fn(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = await fn(*args, **kwargs)
            except ValueError as exc:
                return tool_error(str(exc))
            except Exception as exc:  # noqa: BLE001
                return tool_error(f"{exc.__class__.__name__}: {exc}")
            if isinstance(result, CallToolResult):
                return result
            text = str(result)
            if name in NO_ERROR_TOOLS:
                return text
            return tool_result(text)

        return async_wrapper

    @functools.wraps(fn)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            result = fn(*args, **kwargs)
        except ValueError as exc:
            return tool_error(str(exc))
        except Exception as exc:  # noqa: BLE001
            return tool_error(f"{exc.__class__.__name__}: {exc}")
        if isinstance(result, CallToolResult):
            return result
        text = str(result)
        if name in NO_ERROR_TOOLS:
            return text
        return tool_result(text)

    return sync_wrapper


def install_tool_error_wrapping(mcp: FastMCP) -> None:
    """등록된 모든 Tool fn에 isError 래핑 적용."""
    for tool in mcp._tool_manager.list_tools():  # noqa: SLF001
        tool.fn = _wrap_tool_fn(tool.name, tool.fn)
