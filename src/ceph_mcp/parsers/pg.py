"""Parser for PG status: combines `ceph pg stat -f json` with the
PG-related checks from `ceph health detail -f json`.
"""

from __future__ import annotations

from typing import Any

from . import ParseError

# Health check IDs relevant to PG state, per the Ceph health check reference.
PG_CHECK_IDS = {
    "PG_AVAILABILITY",
    "PG_DEGRADED",
    "PG_DAMAGED",
    "PG_NOT_SCRUBBED",
    "PG_NOT_DEEP_SCRUBBED",
    "PG_RECOVERY_FULL",
    "PG_BACKFILL_FULL",
    "PG_SLOW_SNAP_TRIMMING",
    "TOO_MANY_PGS",
}


def parse_pg_status(outputs: dict[str, Any]) -> dict[str, Any]:
    try:
        pg_stat_raw = outputs["pg_stat"]
        health_raw = outputs["health_detail"]
        pg_summary = pg_stat_raw["pg_summary"]
    except (KeyError, TypeError) as exc:
        raise ParseError(f"missing pg status input: {exc}") from exc

    counts_by_state = {
        entry["name"]: entry["num"] for entry in pg_summary.get("num_pg_by_state", [])
    }
    num_pgs = pg_summary.get("num_pgs", sum(counts_by_state.values()))

    checks_raw = health_raw.get("checks", {})
    related = []
    for check_id, check in checks_raw.items():
        if check_id not in PG_CHECK_IDS:
            continue
        summary = check.get("summary", {})
        related.append(
            {
                "id": check_id,
                "severity": check.get("severity", "UNKNOWN"),
                "message": summary.get("message", ""),
            }
        )
    related.sort(key=lambda c: c["id"])

    return {
        "counts_by_state": counts_by_state,
        "num_pgs": num_pgs,
        "related_health_checks": related,
    }
