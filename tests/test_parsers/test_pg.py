import pytest

from ceph_mcp.parsers import ParseError
from ceph_mcp.parsers.pg import parse_pg_status
from conftest import load_json_fixture


def test_parse_pg_status_clean():
    data = parse_pg_status(
        {
            "pg_stat": load_json_fixture("pg_stat_clean.json"),
            "health_detail": load_json_fixture("health_detail_ok.json"),
        }
    )
    assert data["num_pgs"] == 320
    assert data["counts_by_state"] == {"active+clean": 320}
    assert data["related_health_checks"] == []


def test_parse_pg_status_degraded():
    data = parse_pg_status(
        {
            "pg_stat": load_json_fixture("pg_stat_degraded.json"),
            "health_detail": load_json_fixture("health_detail_warn.json"),
        }
    )
    assert data["counts_by_state"]["active+undersized+degraded"] == 16
    ids = [c["id"] for c in data["related_health_checks"]]
    assert ids == ["PG_DEGRADED"]
    assert "OSD_DOWN" not in ids


def test_parse_pg_status_missing_input_raises():
    with pytest.raises(ParseError):
        parse_pg_status({"pg_stat": {}})


def test_parse_pg_status_missing_pg_summary_raises():
    with pytest.raises(ParseError):
        parse_pg_status(
            {
                "pg_stat": {"pg_ready": True},
                "health_detail": load_json_fixture("health_detail_ok.json"),
            }
        )
