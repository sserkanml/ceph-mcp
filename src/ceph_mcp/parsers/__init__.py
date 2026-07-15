"""Pure parsing functions that turn captured ceph/radosgw-admin output into
the plain dicts returned as each MCP tool's ``data`` field.

Modules in this package must never import ``kubernetes`` or ``k8s_exec`` —
they operate purely on strings/dicts so they can be unit-tested against
fixture files without a live cluster.
"""


class ParseError(Exception):
    """Raised when command output doesn't match the expected shape."""
