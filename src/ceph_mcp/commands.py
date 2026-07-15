"""Fixed allowlist mapping each read-only MCP tool to its underlying
ceph/radosgw-admin command(s).

This is the "hard read-only guarantee" from the design spec: there is no
code path that builds a command from arbitrary model input. Every tool maps
to exactly one pre-defined command template here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .parsers.health import parse_health
from .parsers.mon import parse_mon_status
from .parsers.osd import parse_osd_df, parse_osd_tree
from .parsers.pg import parse_pg_status
from .parsers.pool import parse_pool_usage
from .parsers.rgw_sync import parse_rgw_sync_status

ALLOWED_BINARIES = {"ceph", "radosgw-admin"}


@dataclass(frozen=True)
class SubCommand:
    label: str
    binary: str
    args: list[str] = field(default_factory=list)
    json_output: bool = True

    @property
    def argv(self) -> list[str]:
        return [self.binary, *self.args]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    subcommands: list[SubCommand]
    parser: Callable[[dict[str, Any]], dict[str, Any]]


TOOLS: dict[str, ToolSpec] = {
    "get_cluster_health": ToolSpec(
        name="get_cluster_health",
        description=(
            "Cluster health status (HEALTH_OK/WARN/ERR) with the list of "
            "active health checks and their severity."
        ),
        subcommands=[
            SubCommand("health_detail", "ceph", ["health", "detail", "-f", "json"]),
        ],
        parser=parse_health,
    ),
    "get_osd_tree": ToolSpec(
        name="get_osd_tree",
        description="Hierarchical host/OSD structure with up/down/in/out state.",
        subcommands=[
            SubCommand("osd_tree", "ceph", ["osd", "tree", "-f", "json"]),
        ],
        parser=parse_osd_tree,
    ),
    "get_osd_df": ToolSpec(
        name="get_osd_df",
        description="Per-OSD capacity/usage, useful for spotting imbalance.",
        subcommands=[
            SubCommand("osd_df", "ceph", ["osd", "df", "-f", "json"]),
        ],
        parser=parse_osd_df,
    ),
    "get_pg_status": ToolSpec(
        name="get_pg_status",
        description="PG counts by state, plus PG-related health checks.",
        subcommands=[
            SubCommand("pg_stat", "ceph", ["pg", "stat", "-f", "json"]),
            SubCommand("health_detail", "ceph", ["health", "detail", "-f", "json"]),
        ],
        parser=parse_pg_status,
    ),
    "get_pool_usage": ToolSpec(
        name="get_pool_usage",
        description="Per-pool stored/used/available bytes and object counts.",
        subcommands=[
            SubCommand("df_detail", "ceph", ["df", "detail", "-f", "json"]),
        ],
        parser=parse_pool_usage,
    ),
    "get_mon_status": ToolSpec(
        name="get_mon_status",
        description="Monitor quorum state and mon list.",
        subcommands=[
            SubCommand("quorum_status", "ceph", ["quorum_status", "-f", "json"]),
        ],
        parser=parse_mon_status,
    ),
    "get_rgw_sync_status": ToolSpec(
        name="get_rgw_sync_status",
        description="Per-zone RGW multisite sync state: behind/caught-up/failed.",
        subcommands=[
            SubCommand(
                "sync_status", "radosgw-admin", ["sync", "status"], json_output=False
            ),
        ],
        parser=parse_rgw_sync_status,
    ),
}


def list_tool_names() -> list[str]:
    return list(TOOLS.keys())
