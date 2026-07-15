"""MCP server entrypoint + tool registration for ceph-mcp.

Every tool call execs a fixed, pre-defined command inside the Rook-Ceph
toolbox pod (see commands.py) and returns a structured JSON envelope:
`{"ok": true, "tool": ..., "data": ..., "warnings": [...]}` on success, or
`{"ok": false, "tool": ..., "error": ..., "detail": ...}` on failure.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from . import commands
from .config import load_config
from .k8s_exec import K8sExecClient, K8sExecError
from .parsers import ParseError

server = Server("ceph-mcp")

_state: dict[str, Any] = {}

SUMMARY_TOOL_NAME = "get_cluster_summary"
SUMMARY_SUBTOOLS = [
    "get_cluster_health",
    "get_mon_status",
    "get_osd_tree",
    "get_pg_status",
    "get_pool_usage",
    "get_rgw_sync_status",
]

DETAIL_TRUNCATE_LIMIT = 2000

EMPTY_INPUT_SCHEMA = {"type": "object", "properties": {}, "required": []}


def _truncate(text: str, limit: int = DETAIL_TRUNCATE_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... (truncated, {len(text)} bytes total)"


def _ok_envelope(
    tool: str, data: dict[str, Any], warnings: list[str] | None = None
) -> dict[str, Any]:
    return {"ok": True, "tool": tool, "data": data, "warnings": warnings or []}


def _error_envelope(tool: str, error: str, detail: str | None = None) -> dict[str, Any]:
    envelope: dict[str, Any] = {"ok": False, "tool": tool, "error": error}
    if detail:
        envelope["detail"] = _truncate(detail)
    return envelope


def _k8s_client() -> K8sExecClient:
    return _state["k8s_client"]


def _run_single_tool(name: str) -> dict[str, Any]:
    spec = commands.TOOLS[name]
    client = _k8s_client()
    outputs: dict[str, Any] = {}

    for sub in spec.subcommands:
        try:
            result = client.exec_command(sub.argv)
        except K8sExecError as exc:
            return _error_envelope(
                name, f"failed to exec '{sub.binary}' in toolbox pod", str(exc)
            )

        if result.exit_code not in (0, None):
            return _error_envelope(
                name,
                f"command '{' '.join(sub.argv)}' exited with status {result.exit_code}",
                result.stderr or result.stdout,
            )

        if sub.json_output:
            try:
                outputs[sub.label] = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                return _error_envelope(
                    name,
                    f"failed to parse JSON output of '{' '.join(sub.argv)}'",
                    str(exc),
                )
        else:
            outputs[sub.label] = result.stdout

    try:
        data = spec.parser(outputs)
    except ParseError as exc:
        return _error_envelope(
            name, f"failed to parse output of tool '{name}'", str(exc)
        )

    return _ok_envelope(name, data)


def _run_cluster_summary() -> dict[str, Any]:
    data: dict[str, Any] = {}
    warnings: list[str] = []

    for sub_name in SUMMARY_SUBTOOLS:
        envelope = _run_single_tool(sub_name)
        if envelope["ok"]:
            data[sub_name] = envelope["data"]
        elif sub_name == "get_cluster_health":
            return _error_envelope(
                SUMMARY_TOOL_NAME,
                f"get_cluster_health failed: {envelope['error']}",
                envelope.get("detail"),
            )
        else:
            warnings.append(f"{sub_name}: {envelope['error']}")

    return _ok_envelope(SUMMARY_TOOL_NAME, data, warnings)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    tools = [
        types.Tool(
            name=spec.name, description=spec.description, inputSchema=EMPTY_INPUT_SCHEMA
        )
        for spec in commands.TOOLS.values()
    ]
    tools.append(
        types.Tool(
            name=SUMMARY_TOOL_NAME,
            description=(
                "One-shot high-level cluster snapshot: composes health, mon, "
                "OSD tree, PG status, pool usage, and RGW sync status into a "
                "single 'how's the cluster doing' answer."
            ),
            inputSchema=EMPTY_INPUT_SCHEMA,
        )
    )
    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == SUMMARY_TOOL_NAME:
        envelope = await asyncio.to_thread(_run_cluster_summary)
    elif name in commands.TOOLS:
        envelope = await asyncio.to_thread(_run_single_tool, name)
    else:
        raise ValueError(f"Unknown tool: {name}")

    return [types.TextContent(type="text", text=json.dumps(envelope, indent=2))]


async def main() -> None:
    cfg = load_config()
    client = K8sExecClient(cfg)

    try:
        client.find_toolbox_pod()
    except K8sExecError as exc:
        print(f"ceph-mcp: failed to find toolbox pod: {exc}", file=sys.stderr)
        sys.exit(1)

    _state["k8s_client"] = client

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ceph-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
