"""Kubernetes client wrapper: find the Rook-Ceph toolbox pod and exec
commands inside it.

Knows nothing about Ceph — callers hand it argv lists and get back raw
stdout/stderr/exit code. Only pod-discovery/connection/transport failures
raise here; a nonzero exit code from the command running inside the pod is
returned in ExecResult, not raised, since interpreting "the ceph command
itself failed" is Ceph-domain knowledge that belongs to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass

import yaml
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException
from kubernetes.stream import stream

from .config import Config


class K8sExecError(Exception):
    """Base class for pod-discovery/connection/exec-transport failures."""


class KubeConnectionError(K8sExecError):
    pass


class ToolboxPodNotFoundError(K8sExecError):
    pass


class ToolboxPodAmbiguousError(K8sExecError):
    pass


class ExecTimeoutError(K8sExecError):
    pass


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int | None


class K8sExecClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._core_v1: k8s_client.CoreV1Api | None = None
        self._pod_name: str | None = None

    def _api(self) -> k8s_client.CoreV1Api:
        if self._core_v1 is None:
            try:
                k8s_config.load_kube_config(
                    config_file=self._config.kubeconfig,
                    context=self._config.kube_context,
                )
            except ConfigException as exc:
                raise KubeConnectionError(f"failed to load kubeconfig: {exc}") from exc
            self._core_v1 = k8s_client.CoreV1Api()
        return self._core_v1

    def find_toolbox_pod(self) -> str:
        api = self._api()
        try:
            pods = api.list_namespaced_pod(
                namespace=self._config.namespace,
                label_selector=self._config.toolbox_label,
            )
        except ApiException as exc:
            raise KubeConnectionError(
                f"failed to list pods in namespace '{self._config.namespace}': {exc}"
            ) from exc

        names = [pod.metadata.name for pod in pods.items]
        if len(names) == 0:
            raise ToolboxPodNotFoundError(
                f"no pod matching label selector '{self._config.toolbox_label}' "
                f"found in namespace '{self._config.namespace}'"
            )
        if len(names) > 1:
            raise ToolboxPodAmbiguousError(
                f"multiple pods matching label selector '{self._config.toolbox_label}' "
                f"found in namespace '{self._config.namespace}': {names}"
            )

        self._pod_name = names[0]
        return self._pod_name

    def exec_command(self, argv: list[str], timeout: int = 30) -> ExecResult:
        if self._pod_name is None:
            self.find_toolbox_pod()

        try:
            return self._exec_once(argv, timeout)
        except ApiException as exc:
            if exc.status == 404:
                # Pod may have been rescheduled; re-discover once and retry.
                self.find_toolbox_pod()
                return self._exec_once(argv, timeout)
            raise KubeConnectionError(f"exec into toolbox pod failed: {exc}") from exc

    def _exec_once(self, argv: list[str], timeout: int) -> ExecResult:
        api = self._api()
        resp = stream(
            api.connect_get_namespaced_pod_exec,
            name=self._pod_name,
            namespace=self._config.namespace,
            command=argv,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False,
        )
        try:
            resp.run_forever(timeout=timeout)
            if resp.is_open():
                raise ExecTimeoutError(
                    f"command {argv!r} did not complete within {timeout}s"
                )
            stdout = resp.read_stdout()
            stderr = resp.read_stderr()
            exit_code = self._read_exit_code(resp)
        finally:
            resp.close()

        return ExecResult(stdout=stdout or "", stderr=stderr or "", exit_code=exit_code)

    @staticmethod
    def _read_exit_code(resp) -> int | None:
        try:
            return resp.returncode
        except yaml.YAMLError, KeyError, IndexError, ValueError, TypeError:
            return None
