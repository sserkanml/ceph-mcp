from ceph_mcp.commands import ALLOWED_BINARIES, TOOLS, list_tool_names


def test_every_binary_is_allowlisted():
    for tool in TOOLS.values():
        for sub in tool.subcommands:
            assert sub.binary in ALLOWED_BINARIES


def test_tool_name_matches_dict_key():
    for key, tool in TOOLS.items():
        assert tool.name == key


def test_no_duplicate_subcommand_labels_within_a_tool():
    for tool in TOOLS.values():
        labels = [sub.label for sub in tool.subcommands]
        assert len(labels) == len(set(labels))


def test_cluster_summary_is_not_a_command_template():
    assert "get_cluster_summary" not in TOOLS


def test_list_tool_names_matches_tools_dict():
    assert set(list_tool_names()) == set(TOOLS.keys())


def test_every_tool_has_at_least_one_subcommand():
    for tool in TOOLS.values():
        assert len(tool.subcommands) >= 1
