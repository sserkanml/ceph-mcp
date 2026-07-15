# ceph-mcp

A read-only [MCP](https://modelcontextprotocol.io) server for **Rook-Ceph** clusters running on Kubernetes.

It lets an LLM (Claude, etc.) inspect the health of a Ceph cluster — cluster health, OSD tree, PG status, pool usage, mon quorum, RGW multisite sync — by executing a fixed set of `ceph` / `radosgw-admin` commands inside the Rook-Ceph toolbox pod and returning structured JSON.

## Why it's safe to hand to an LLM

- **No arbitrary commands.** Every tool maps to exactly one hardcoded command template in [`commands.py`](src/ceph_mcp/commands.py). There is no code path that builds a shell command from model input — the model can only pick *which* tool to call, never *what* to run.
- **Read-only.** Only inspection commands (`ceph health`, `ceph osd tree`, `ceph df`, `radosgw-admin sync status`, ...) are exposed. Nothing that mutates cluster state.
- **Scoped exec, not a shell.** Commands run via the Kubernetes `exec` API inside the existing `rook-ceph-tools` pod — the server itself never needs cluster-admin credentials beyond what your kubeconfig already grants.

## Tools

| Tool | Description |
|---|---|
| `get_cluster_health` | `HEALTH_OK`/`WARN`/`ERR` plus the active health checks and their severity |
| `get_osd_tree` | Hierarchical host/OSD structure with up/down/in/out state |
| `get_osd_df` | Per-OSD capacity/usage, useful for spotting imbalance |
| `get_pg_status` | PG counts by state, plus PG-related health checks |
| `get_pool_usage` | Per-pool stored/used/available bytes and object counts |
| `get_mon_status` | Monitor quorum state and mon list |
| `get_rgw_sync_status` | Per-zone RGW multisite sync state: behind/caught-up/failed |
| `get_cluster_summary` | Composes all of the above into a single "how's the cluster doing" snapshot |

Every tool returns a JSON envelope:

```json
{ "ok": true, "tool": "get_cluster_health", "data": { ... }, "warnings": [] }
```

or, on failure:

```json
{ "ok": false, "tool": "get_cluster_health", "error": "...", "detail": "..." }
```

## Requirements

- Python >= 3.14
- A Kubernetes cluster running [Rook-Ceph](https://rook.io/), with the `rook-ceph-tools` toolbox pod deployed
- A working kubeconfig with permission to `list`/`exec` pods in the Rook-Ceph namespace

## Installation

Once published to PyPI, run it with [`uvx`](https://docs.astral.sh/uv/) — no separate install step needed:

```bash
uvx ceph-mcp
```

Or install it into a virtualenv:

```bash
uv pip install ceph-mcp
```

### From source

```bash
git clone git@github.com:sserkanml/ceph-mcp.git
cd ceph-mcp
uv sync
uv run ceph-mcp
```

## Configuration

Configured entirely through environment variables:

| Variable | Default | Description |
|---|---|---|
| `CEPH_MCP_NAMESPACE` | `rook-ceph` | Namespace the toolbox pod lives in |
| `CEPH_MCP_TOOLBOX_LABEL` | `app=rook-ceph-tools` | Label selector used to find the toolbox pod |
| `CEPH_MCP_KUBECONFIG` | *(default kubeconfig)* | Path to a specific kubeconfig file |
| `CEPH_MCP_KUBE_CONTEXT` | *(current context)* | kubeconfig context to use |

## Usage with Claude Desktop

Config file location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

**Published (PyPI) version:**

```json
{
  "mcpServers": {
    "ceph-mcp": {
      "command": "uvx",
      "args": ["ceph-mcp"],
      "env": {
        "CEPH_MCP_NAMESPACE": "rook-ceph",
        "CEPH_MCP_TOOLBOX_LABEL": "app=rook-ceph-tools"
      }
    }
  }
}
```

**From a local checkout:**

```json
{
  "mcpServers": {
    "ceph-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/ceph-mcp", "ceph-mcp"],
      "env": {
        "CEPH_MCP_NAMESPACE": "rook-ceph",
        "CEPH_MCP_TOOLBOX_LABEL": "app=rook-ceph-tools"
      }
    }
  }
}
```

See [`examples/claude_desktop_config.json`](examples/claude_desktop_config.json) for a ready-to-copy version.

## Development

Project layout:

```
src/ceph_mcp/
├── server.py       # MCP server entrypoint + tool registration
├── commands.py     # fixed allowlist: tool name -> ceph/radosgw-admin command
├── config.py       # env var -> Config resolution
├── k8s_exec.py     # finds the toolbox pod, execs commands via the k8s API
└── parsers/        # raw ceph JSON/text -> structured tool output
tests/
├── fixtures/       # captured real ceph/radosgw-admin output, used by parser tests
└── test_*.py
```

Run the test suite:

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check .
```

### Debugging

Since MCP servers communicate over stdio, use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to interact with the server directly:

```bash
npx @modelcontextprotocol/inspector uv --directory /absolute/path/to/ceph-mcp run ceph-mcp
```

### Publishing to PyPI

```bash
uv sync
uv build
uv publish
```

Requires PyPI credentials via `UV_PUBLISH_TOKEN` (or `--token`).

## License

MIT — see [LICENSE](LICENSE).

## Author

Serkan ([@sserkanml](https://github.com/sserkanml))
