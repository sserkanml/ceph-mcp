"""Parser for `radosgw-admin sync status`.

This is the one module doing real text parsing: `radosgw-admin sync status`
has no `--format json` mode, unlike every other command used by this
server. Treat its regexes as the most likely place for real-world Ceph
output to diverge from what's captured here.
"""

from __future__ import annotations

import re
from typing import Any

from . import ParseError

_REALM_RE = re.compile(r"^\s*realm\s+\S+\s+\((?P<name>[^)]+)\)")
_ZONEGROUP_RE = re.compile(r"^\s*zonegroup\s+\S+\s+\((?P<name>[^)]+)\)")
_ZONE_RE = re.compile(r"^\s*zone\s+\S+\s+\((?P<name>[^)]+)\)")
_METADATA_SYNC_RE = re.compile(r"^\s*metadata sync\s+(?P<status>.+?)\s*$")
_DATA_SOURCE_RE = re.compile(r"^\s*data sync source:\s+\S+\s+\((?P<name>[^)]+)\)")
_FULL_SYNC_RE = re.compile(r"full sync:\s*(?P<done>\d+)/(?P<total>\d+)\s+shards")
_INCREMENTAL_SYNC_RE = re.compile(
    r"incremental sync:\s*(?P<done>\d+)/(?P<total>\d+)\s+shards"
)


def parse_rgw_sync_status(outputs: dict[str, Any]) -> dict[str, Any]:
    text = outputs.get("sync_status")
    if not isinstance(text, str) or not text.strip():
        raise ParseError("empty radosgw-admin sync status output")

    realm = zonegroup = zone = None
    metadata_status: str | None = None
    sources: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in text.splitlines():
        if m := _REALM_RE.match(line):
            realm = m.group("name")
            continue
        if m := _ZONEGROUP_RE.match(line):
            zonegroup = m.group("name")
            continue
        if m := _ZONE_RE.match(line):
            zone = m.group("name")
            continue
        if m := _METADATA_SYNC_RE.match(line):
            metadata_status = m.group("status").strip()
            continue
        if m := _DATA_SOURCE_RE.match(line):
            if current is not None:
                sources.append(current)
            current = {
                "zone": m.group("name"),
                "status": "unknown",
                "full_sync": {"done": None, "total": None},
                "incremental_sync": {"done": None, "total": None},
            }
            continue
        if current is None:
            continue

        stripped = line.strip()
        if m := _FULL_SYNC_RE.search(stripped):
            current["full_sync"] = {
                "done": int(m.group("done")),
                "total": int(m.group("total")),
            }
        elif m := _INCREMENTAL_SYNC_RE.search(stripped):
            current["incremental_sync"] = {
                "done": int(m.group("done")),
                "total": int(m.group("total")),
            }
        elif "caught up" in stripped:
            current["status"] = "caught-up"
        elif "behind" in stripped:
            current["status"] = "behind"
        elif "recovering" in stripped:
            current["status"] = "recovering"
        elif stripped.startswith("failed") or "error" in stripped.lower():
            current["status"] = "error"
        elif stripped == "syncing" and current["status"] == "unknown":
            current["status"] = "syncing"

    if current is not None:
        sources.append(current)

    if realm is None or zonegroup is None or zone is None:
        raise ParseError("could not find realm/zonegroup/zone in sync status output")

    return {
        "realm": realm,
        "zonegroup": zonegroup,
        "zone": zone,
        "metadata_sync": {"status": metadata_status or "unknown"},
        "data_sync_sources": sources,
    }
