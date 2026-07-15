"""Parser for `ceph df detail -f json`."""

from __future__ import annotations

from typing import Any

from . import ParseError


def parse_pool_usage(outputs: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = outputs["df_detail"]
        pools_raw = raw["pools"]
    except (KeyError, TypeError) as exc:
        raise ParseError(f"unexpected df detail shape: {exc}") from exc

    pools = []
    for pool in pools_raw:
        stats = pool.get("stats", {})
        pools.append(
            {
                "name": pool.get("name"),
                "id": pool.get("id"),
                "stored_bytes": stats.get("stored"),
                "used_bytes": stats.get("bytes_used"),
                "available_bytes": stats.get("max_avail"),
                "objects": stats.get("objects"),
            }
        )

    global_stats = raw.get("stats", {})
    summary = {
        "total_bytes": global_stats.get("total_bytes"),
        "total_used_bytes": global_stats.get("total_used_bytes"),
        "total_avail_bytes": global_stats.get("total_avail_bytes"),
    }

    return {"pools": pools, "summary": summary}
