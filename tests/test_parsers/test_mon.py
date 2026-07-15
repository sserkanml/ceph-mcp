import pytest

from ceph_mcp.parsers import ParseError
from ceph_mcp.parsers.mon import parse_mon_status
from conftest import load_json_fixture


def test_parse_mon_status_healthy():
    data = parse_mon_status(
        {"quorum_status": load_json_fixture("quorum_status_healthy.json")}
    )
    assert data["quorum_leader"] == "a"
    assert data["quorum_names"] == ["a", "b", "c"]
    assert all(m["in_quorum"] for m in data["mons"])


def test_parse_mon_status_degraded():
    data = parse_mon_status(
        {"quorum_status": load_json_fixture("quorum_status_degraded.json")}
    )
    by_name = {m["name"]: m for m in data["mons"]}
    assert by_name["b"]["in_quorum"] is False
    assert by_name["a"]["in_quorum"] is True
    assert data["quorum_leader"] == "a"


def test_parse_mon_status_missing_monmap_raises():
    with pytest.raises(ParseError):
        parse_mon_status({"quorum_status": {}})
