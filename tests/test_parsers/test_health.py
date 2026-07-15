import pytest

from ceph_mcp.parsers import ParseError
from ceph_mcp.parsers.health import parse_health
from conftest import load_json_fixture


def test_parse_health_ok():
    data = parse_health({"health_detail": load_json_fixture("health_detail_ok.json")})
    assert data["status"] == "HEALTH_OK"
    assert data["checks"] == []
    assert data["mutes"] == []


def test_parse_health_warn():
    data = parse_health({"health_detail": load_json_fixture("health_detail_warn.json")})
    assert data["status"] == "HEALTH_WARN"
    ids = [c["id"] for c in data["checks"]]
    assert ids == ["OSD_DOWN", "PG_DEGRADED"]
    osd_down = next(c for c in data["checks"] if c["id"] == "OSD_DOWN")
    assert osd_down["severity"] == "HEALTH_WARN"
    assert osd_down["count"] == 1
    assert osd_down["detail"] == ["osd.3 (root=default,host=host2) is down"]


def test_parse_health_err():
    data = parse_health({"health_detail": load_json_fixture("health_detail_err.json")})
    assert data["status"] == "HEALTH_ERR"
    ids = [c["id"] for c in data["checks"]]
    assert "PG_DAMAGED" in ids


def test_parse_health_missing_status_raises():
    with pytest.raises(ParseError):
        parse_health({"health_detail": {}})
