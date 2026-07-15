from ceph_mcp.config import load_config


def test_defaults_when_env_empty():
    cfg = load_config({})
    assert cfg.namespace == "rook-ceph"
    assert cfg.toolbox_label == "app=rook-ceph-tools"
    assert cfg.kubeconfig is None
    assert cfg.kube_context is None


def test_overrides_from_env():
    cfg = load_config(
        {
            "CEPH_MCP_NAMESPACE": "openshift-storage",
            "CEPH_MCP_TOOLBOX_LABEL": "app=rook-ceph-tooling",
            "CEPH_MCP_KUBECONFIG": "/path/to/kubeconfig",
            "CEPH_MCP_KUBE_CONTEXT": "my-context",
        }
    )
    assert cfg.namespace == "openshift-storage"
    assert cfg.toolbox_label == "app=rook-ceph-tooling"
    assert cfg.kubeconfig == "/path/to/kubeconfig"
    assert cfg.kube_context == "my-context"


def test_empty_string_treated_as_unset_for_optional_vars():
    cfg = load_config({"CEPH_MCP_KUBECONFIG": "", "CEPH_MCP_KUBE_CONTEXT": ""})
    assert cfg.kubeconfig is None
    assert cfg.kube_context is None


def test_defaults_to_os_environ(monkeypatch):
    monkeypatch.setenv("CEPH_MCP_NAMESPACE", "from-real-environ")
    cfg = load_config()
    assert cfg.namespace == "from-real-environ"
