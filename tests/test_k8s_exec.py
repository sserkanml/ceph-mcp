from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException

from ceph_mcp.config import Config
from ceph_mcp.k8s_exec import (
    ExecTimeoutError,
    K8sExecClient,
    KubeConnectionError,
    ToolboxPodAmbiguousError,
    ToolboxPodNotFoundError,
)

CFG = Config(
    namespace="rook-ceph",
    toolbox_label="app=rook-ceph-tools",
    kubeconfig=None,
    kube_context=None,
)


def _pod_list(names: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        items=[SimpleNamespace(metadata=SimpleNamespace(name=n)) for n in names]
    )


@patch("ceph_mcp.k8s_exec.k8s_config.load_kube_config")
@patch("ceph_mcp.k8s_exec.k8s_client.CoreV1Api")
def test_find_toolbox_pod_single_match(mock_core_v1_cls, mock_load_kubeconfig):
    mock_api = mock_core_v1_cls.return_value
    mock_api.list_namespaced_pod.return_value = _pod_list(["rook-ceph-tools-abc123"])

    result = K8sExecClient(CFG).find_toolbox_pod()

    assert result == "rook-ceph-tools-abc123"


@patch("ceph_mcp.k8s_exec.k8s_config.load_kube_config")
@patch("ceph_mcp.k8s_exec.k8s_client.CoreV1Api")
def test_find_toolbox_pod_no_match_raises(mock_core_v1_cls, mock_load_kubeconfig):
    mock_api = mock_core_v1_cls.return_value
    mock_api.list_namespaced_pod.return_value = _pod_list([])

    with pytest.raises(ToolboxPodNotFoundError):
        K8sExecClient(CFG).find_toolbox_pod()


@patch("ceph_mcp.k8s_exec.k8s_config.load_kube_config")
@patch("ceph_mcp.k8s_exec.k8s_client.CoreV1Api")
def test_find_toolbox_pod_ambiguous_raises(mock_core_v1_cls, mock_load_kubeconfig):
    mock_api = mock_core_v1_cls.return_value
    mock_api.list_namespaced_pod.return_value = _pod_list(["pod-a", "pod-b"])

    with pytest.raises(ToolboxPodAmbiguousError) as exc_info:
        K8sExecClient(CFG).find_toolbox_pod()
    assert "pod-a" in str(exc_info.value)
    assert "pod-b" in str(exc_info.value)


@patch("ceph_mcp.k8s_exec.k8s_config.load_kube_config")
@patch("ceph_mcp.k8s_exec.k8s_client.CoreV1Api")
def test_find_toolbox_pod_api_error_raises_connection_error(
    mock_core_v1_cls, mock_load_kubeconfig
):
    mock_api = mock_core_v1_cls.return_value
    mock_api.list_namespaced_pod.side_effect = ApiException(
        status=403, reason="Forbidden"
    )

    with pytest.raises(KubeConnectionError):
        K8sExecClient(CFG).find_toolbox_pod()


@patch("ceph_mcp.k8s_exec.k8s_config.load_kube_config")
def test_bad_kubeconfig_raises_connection_error(mock_load_kubeconfig):
    mock_load_kubeconfig.side_effect = ConfigException("no configuration found")

    with pytest.raises(KubeConnectionError):
        K8sExecClient(CFG).find_toolbox_pod()


def _mock_ws_client(*, stdout="ok\n", stderr="", returncode=0, stays_open=False):
    resp = MagicMock()
    resp.is_open.return_value = stays_open
    resp.read_stdout.return_value = stdout
    resp.read_stderr.return_value = stderr
    resp.returncode = returncode
    return resp


@patch("ceph_mcp.k8s_exec.stream")
@patch("ceph_mcp.k8s_exec.k8s_config.load_kube_config")
@patch("ceph_mcp.k8s_exec.k8s_client.CoreV1Api")
def test_exec_command_success(mock_core_v1_cls, mock_load_kubeconfig, mock_stream):
    mock_api = mock_core_v1_cls.return_value
    mock_api.list_namespaced_pod.return_value = _pod_list(["rook-ceph-tools-abc123"])
    mock_stream.return_value = _mock_ws_client(
        stdout='{"status": "HEALTH_OK"}\n', returncode=0
    )

    result = K8sExecClient(CFG).exec_command(["ceph", "health", "detail", "-f", "json"])

    assert result.exit_code == 0
    assert "HEALTH_OK" in result.stdout


@patch("ceph_mcp.k8s_exec.stream")
@patch("ceph_mcp.k8s_exec.k8s_config.load_kube_config")
@patch("ceph_mcp.k8s_exec.k8s_client.CoreV1Api")
def test_exec_command_nonzero_exit_does_not_raise(
    mock_core_v1_cls, mock_load_kubeconfig, mock_stream
):
    mock_api = mock_core_v1_cls.return_value
    mock_api.list_namespaced_pod.return_value = _pod_list(["rook-ceph-tools-abc123"])
    mock_stream.return_value = _mock_ws_client(
        stdout="", stderr="command not found", returncode=127
    )

    result = K8sExecClient(CFG).exec_command(["ceph", "bogus"])

    assert result.exit_code == 127
    assert result.stderr == "command not found"


@patch("ceph_mcp.k8s_exec.stream")
@patch("ceph_mcp.k8s_exec.k8s_config.load_kube_config")
@patch("ceph_mcp.k8s_exec.k8s_client.CoreV1Api")
def test_exec_command_timeout_raises(
    mock_core_v1_cls, mock_load_kubeconfig, mock_stream
):
    mock_api = mock_core_v1_cls.return_value
    mock_api.list_namespaced_pod.return_value = _pod_list(["rook-ceph-tools-abc123"])
    mock_stream.return_value = _mock_ws_client(stays_open=True)

    with pytest.raises(ExecTimeoutError):
        K8sExecClient(CFG).exec_command(["ceph", "health", "detail"], timeout=1)
