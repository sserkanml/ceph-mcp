"""Parsers for `ceph osd tree -f json` and `ceph osd df -f json`."""

from __future__ import annotations

from typing import Any

from . import ParseError


def parse_osd_tree(outputs: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = outputs["osd_tree"]
        nodes = raw["nodes"]
    except (KeyError, TypeError) as exc:
        raise ParseError(f"unexpected osd tree shape: {exc}") from exc

    osd_host: dict[int, str] = {}
    for node in nodes:
        if node.get("type") == "host":
            for child_id in node.get("children", []):
                osd_host[child_id] = node.get("name")

    osds = []
    for node in nodes:
        if node.get("type") != "osd":
            continue
        reweight = node.get("reweight", 1.0)
        osds.append(
            {
                "id": node["id"],
                "name": node.get("name"),
                "host": osd_host.get(node["id"]),
                "device_class": node.get("device_class"),
                "up": node.get("status") == "up",
                "in": reweight not in (0, 0.0),
                "reweight": reweight,
                "crush_weight": node.get("crush_weight"),
            }
        )
    osds.sort(key=lambda o: o["id"])

    hosts_map: dict[str | None, list[int]] = {}
    for osd in osds:
        hosts_map.setdefault(osd["host"], []).append(osd["id"])
    hosts = [
        {"host": host, "osd_ids": sorted(ids)}
        for host, ids in sorted(
            hosts_map.items(), key=lambda kv: (kv[0] is None, kv[0])
        )
    ]

    return {"hosts": hosts, "osds": osds, "stray": raw.get("stray", [])}


def parse_osd_df(outputs: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = outputs["osd_df"]
        nodes = raw["nodes"]
    except (KeyError, TypeError) as exc:
        raise ParseError(f"unexpected osd df shape: {exc}") from exc

    osds = [
        {
            "id": node["id"],
            "name": node.get("name"),
            "device_class": node.get("device_class"),
            "kb": node.get("kb"),
            "kb_used": node.get("kb_used"),
            "kb_avail": node.get("kb_avail"),
            "utilization": node.get("utilization"),
            "var": node.get("var"),
            "pgs": node.get("pgs"),
            "status": node.get("status"),
        }
        for node in nodes
    ]
    osds.sort(key=lambda o: o["id"])

    return {"osds": osds, "summary": raw.get("summary", {})}
