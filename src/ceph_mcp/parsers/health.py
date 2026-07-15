"""Parser for `ceph health detail -f json`."""

from __future__ import annotations

from typing import Any

from . import ParseError


def parse_health(outputs: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = outputs["health_detail"]
        status = raw["status"]
        checks_raw = raw.get("checks", {})
        mutes = raw.get("mutes", [])
    except (KeyError, TypeError) as exc:
        raise ParseError(f"unexpected health detail shape: {exc}") from exc

    checks = []
    for check_id, check in checks_raw.items():
        summary = check.get("summary", {})
        detail_entries = check.get("detail", [])
        detail = [
            entry.get("message", str(entry)) if isinstance(entry, dict) else str(entry)
            for entry in detail_entries
        ]
        checks.append(
            {
                "id": check_id,
                "severity": check.get("severity", "UNKNOWN"),
                "message": summary.get("message", ""),
                "count": summary.get("count"),
                "detail": detail,
            }
        )
    checks.sort(key=lambda c: c["id"])

    return {"status": status, "checks": checks, "mutes": mutes}
