import pytest

from ceph_mcp.parsers import ParseError
from ceph_mcp.parsers.pool import parse_pool_usage
from conftest import load_json_fixture


def test_parse_pool_usage():
    data = parse_pool_usage({"df_detail": load_json_fixture("df_detail.json")})
    assert len(data["pools"]) == 2
    rbd = next(p for p in data["pools"] if p["name"] == "rbd")
    assert rbd["stored_bytes"] == 2000000000
    assert rbd["objects"] == 500
    assert data["summary"]["total_bytes"] == 10737418240


def test_parse_pool_usage_near_full():
    data = parse_pool_usage(
        {"df_detail": load_json_fixture("df_detail_pool_near_full.json")}
    )
    rbd = data["pools"][0]
    assert rbd["available_bytes"] == 214748364


def test_parse_pool_usage_missing_pools_raises():
    with pytest.raises(ParseError):
        parse_pool_usage({"df_detail": {}})
