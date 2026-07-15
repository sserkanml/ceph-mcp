import pytest

from ceph_mcp.parsers import ParseError
from ceph_mcp.parsers.rgw_sync import parse_rgw_sync_status
from conftest import load_fixture


def test_parse_rgw_sync_caught_up():
    data = parse_rgw_sync_status(
        {"sync_status": load_fixture("rgw_sync_status_caught_up.txt")}
    )
    assert data["realm"] == "myrealm"
    assert data["zonegroup"] == "us"
    assert data["zone"] == "us-east-1"
    assert len(data["data_sync_sources"]) == 1
    source = data["data_sync_sources"][0]
    assert source["zone"] == "us-west-1"
    assert source["status"] == "caught-up"
    assert source["incremental_sync"] == {"done": 128, "total": 128}


def test_parse_rgw_sync_behind():
    data = parse_rgw_sync_status(
        {"sync_status": load_fixture("rgw_sync_status_behind.txt")}
    )
    source = data["data_sync_sources"][0]
    assert source["status"] == "behind"
    assert source["incremental_sync"] == {"done": 100, "total": 128}


def test_parse_rgw_sync_error():
    data = parse_rgw_sync_status(
        {"sync_status": load_fixture("rgw_sync_status_error.txt")}
    )
    source = data["data_sync_sources"][0]
    assert source["status"] == "error"


def test_parse_rgw_sync_no_multisite():
    data = parse_rgw_sync_status(
        {"sync_status": load_fixture("rgw_sync_status_no_multisite.txt")}
    )
    assert data["data_sync_sources"] == []
    assert data["zone"] == "us-east-1"


def test_parse_rgw_sync_empty_raises():
    with pytest.raises(ParseError):
        parse_rgw_sync_status({"sync_status": ""})


def test_parse_rgw_sync_missing_identity_raises():
    with pytest.raises(ParseError):
        parse_rgw_sync_status({"sync_status": "some unrelated text\n"})
