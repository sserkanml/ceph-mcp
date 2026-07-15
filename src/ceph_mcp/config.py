"""Environment-variable / config resolution for ceph-mcp.

Knows nothing about Kubernetes or Ceph — just resolves the four settings
described in the design spec (namespace, toolbox label, kubeconfig path,
kube context) from environment variables into a plain, immutable Config.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os

DEFAULT_NAMESPACE = "rook-ceph"
DEFAULT_TOOLBOX_LABEL = "app=rook-ceph-tools"


@dataclass(frozen=True)
class Config:
    namespace: str
    toolbox_label: str
    kubeconfig: str | None
    kube_context: str | None


def _optional(env: Mapping[str, str], key: str) -> str | None:
    value = env.get(key)
    return value if value else None


def load_config(env: Mapping[str, str] | None = None) -> Config:
    """Resolve a Config from environment variables (defaults to os.environ)."""
    if env is None:
        env = os.environ

    return Config(
        namespace=env.get("CEPH_MCP_NAMESPACE") or DEFAULT_NAMESPACE,
        toolbox_label=env.get("CEPH_MCP_TOOLBOX_LABEL") or DEFAULT_TOOLBOX_LABEL,
        kubeconfig=_optional(env, "CEPH_MCP_KUBECONFIG"),
        kube_context=_optional(env, "CEPH_MCP_KUBE_CONTEXT"),
    )
