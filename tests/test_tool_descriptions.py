"""PlayMCP tools/list description 필수 검증."""

import asyncio

from modu_emergencybell import mcp

EXPECTED = {
    "emergency_guide_tool",
    "health_triage_tool",
    "get_emergency_hotlines",
    "find_nearest_restroom",
    "find_medical_care",
    "find_veteran_hospital",
    "find_safety_bell",
    "get_phrase_card",
    "find_subway_facility_tool",
    "find_safe_place",
    "find_accessible_facility_tool",
    "find_outdoor_service_tool",
}
SERVICE_NAME = "모두의비상벨: 급할 때 필요한 생활 정보를 찾는 도우미"
SERVICE_IDENTIFIER = f"modu-emergencybell({SERVICE_NAME})"


def test_all_tools_have_description() -> None:
    async def _run() -> None:
        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        assert names == EXPECTED
        for t in tools:
            assert t.description and t.description.strip(), f"missing description: {t.name}"
            assert SERVICE_NAME in t.description, f"missing service name: {t.name}"
            assert SERVICE_IDENTIFIER in t.description, f"missing service identifier: {t.name}"
            assert not t.description.startswith(SERVICE_NAME), t.name
            assert "PARAMETERS:" not in t.description, t.name
            assert len(t.description) < 200, t.name
            for param_name, schema in t.inputSchema.get("properties", {}).items():
                assert schema.get("description", "").strip(), (
                    f"missing inputSchema description: {t.name}.{param_name}"
                )

    asyncio.run(_run())
