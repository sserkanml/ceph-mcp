"""Parser for `ceph quorum_status -f json`."""

from __future__ import annotations

from typing import Any

from . import ParseError


def parse_mon_status(outputs: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = outputs["quorum_status"]
        mons_raw = raw["monmap"]["mons"]
    except (KeyError, TypeError) as exc:
        raise ParseError(f"unexpected quorum status shape: {exc}") from exc

    quorum_names = set(raw.get("quorum_names", []))
    mons = [
        {
            "name": mon.get("name"),
            "rank": mon.get("rank"),
            "addr": mon.get("addr"),
            "in_quorum": mon.get("name") in quorum_names,
        }
        for mon in mons_raw
    ]
    mons.sort(key=lambda m: m["rank"] if m["rank"] is not None else -1)

    return {
        "quorum_leader": raw.get("quorum_leader_name"),
        "quorum_names": sorted(quorum_names),
        "mons": mons,
    }
