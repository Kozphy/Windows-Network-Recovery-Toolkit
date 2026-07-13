"""Read-only MCP server for technology risk tools."""

from __future__ import annotations

import asyncio
import os

from mcp_server import tools


async def _run_stdio_server() -> None:
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError as exc:
        raise RuntimeError("mcp package required — pip install '.[mcp]'") from exc

    server = Server("trisk-readonly")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name="get_proxy_status", description="Read proxy state from fixture", inputSchema={"type": "object", "properties": {"fixture_path": {"type": "string"}}}),
            Tool(name="get_tls_status", description="TLS path probe", inputSchema={"type": "object", "properties": {"host": {"type": "string"}, "port": {"type": "integer"}}, "required": ["host"]}),
            Tool(name="get_risk_report", description="List risk items from DB", inputSchema={"type": "object", "properties": {"limit": {"type": "integer"}}}),
            Tool(name="get_evidence_timeline", description="Domain event timeline", inputSchema={"type": "object", "properties": {"aggregate_id": {"type": "string"}}, "required": ["aggregate_id"]}),
            Tool(name="run_control_tests", description="Read control test results", inputSchema={"type": "object", "properties": {"incident_id": {"type": "string"}}, "required": ["incident_id"]}),
            Tool(name="generate_governance_report", description="Executive governance report", inputSchema={"type": "object", "properties": {"audit_dir": {"type": "string"}}}),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if os.getenv("MCP_READ_ONLY", "1") not in ("1", "true", "True") and name.startswith("remediate"):
            raise ValueError("write tools blocked")
        dispatch = {
            "get_proxy_status": lambda a: tools.get_proxy_status(a.get("fixture_path")),
            "get_tls_status": lambda a: tools.get_tls_status(a["host"], int(a.get("port", 443))),
            "get_risk_report": lambda a: tools.get_risk_report(int(a.get("limit", 50))),
            "get_evidence_timeline": lambda a: tools.get_evidence_timeline(a["aggregate_id"]),
            "run_control_tests": lambda a: tools.run_control_tests(a["incident_id"]),
            "generate_governance_report": lambda a: tools.generate_governance_report(a.get("audit_dir")),
        }
        if name not in dispatch:
            raise ValueError(f"unknown tool: {name}")
        result = dispatch[name](arguments or {})
        import json

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_run_stdio_server())


if __name__ == "__main__":
    main()
