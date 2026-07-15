import pytest

from ceph_mcp.parsers import ParseError
from ceph_mcp.parsers.osd import parse_osd_df, parse_osd_tree
from conftest import load_json_fixture


def test_parse_osd_tree():
    data = parse_osd_tree({"osd_tree": load_json_fixture("osd_tree.json")})
    assert [h["host"] for h in data["hosts"]] == ["host1", "host2"]
    assert data["hosts"][0]["osd_ids"] == [0, 1]
    assert data["hosts"][1]["osd_ids"] == [2, 3]

    by_id = {o["id"]: o for o in data["osds"]}
    assert by_id[0]["up"] is True
    assert by_id[0]["in"] is True
    assert by_id[3]["up"] is False
    assert by_id[3]["in"] is False
    assert by_id[3]["host"] == "host2"


def test_parse_osd_tree_missing_nodes_raises():
    with pytest.raises(ParseError):
        parse_osd_tree({"osd_tree": {}})


def test_parse_osd_df():
    data = parse_osd_df({"osd_df": load_json_fixture("osd_df.json")})
    assert len(data["osds"]) == 4
    assert data["summary"]["total_pgs"] == 96
    by_id = {o["id"]: o for o in data["osds"]}
    assert by_id[2]["utilization"] == 80.0
    assert by_id[3]["status"] == "down"


def test_parse_osd_df_missing_nodes_raises():
    with pytest.raises(ParseError):
        parse_osd_df({"osd_df": {}})
