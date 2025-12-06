______________________________________________________________________

## layout: default title: ADR-0038 FastMCP Framework Migration parent: Architecture & Design grand_parent: Architectural Decision Records nav_order: 38

# ADR-0038: FastMCP Framework Migration for MCP Server Implementation

**Status:** Accepted - Implemented (2025-12-05)
**Date:** 2025-11-21
**Decision Makers:** Platform Team, AI Integration Team
**Related ADRs:** ADR-0027 (AI Assistant), ADR-0036 (Airflow Integration)

## Context and Problem Statement

We initially implemented Model Context Protocol (MCP) servers using the low-level `modelcontextprotocol/python-sdk` with custom SSE transport. This approach has proven fragile:

**Current Problems:**

- ❌ AI Assistant MCP has SSE transport errors
- ❌ Manual SSE implementation using internal APIs
- ❌ 171 lines of complex transport code
- ❌ Unreliable client connections
- ❌ Difficult to debug and extend

## Decision

**Migrate to FastMCP Framework**

### Why FastMCP?

1. **90% Less Code**

   - Current: 171 lines of complex transport code
   - FastMCP: ~60 lines total (including tool logic)

1. **Framework Handles Complexity**

   - Automatic SSE/HTTP/stdio transport
   - Built-in JSON-RPC error handling
   - No internal API usage

1. **Production Ready**

   - Used by multiple production projects
   - Active development and community

### Code Comparison

**Current (Custom SSE):**

```python
# 171 lines in mcp_http_server.py
async with self.sse.connect_sse(
    request.scope,
    request.receive,
    request._send  # Internal API!
) as (read_stream, write_stream):
    await self.mcp_server.run(...)
```

**FastMCP:**

```python
from fastmcp import FastMCP
mcp = FastMCP("Qubinode AI")

@mcp.tool()
async def query_documents(query: str) -> str:
    """Search RAG"""
    return results

# That's it! FastMCP handles everything!
```

## Migration Plan

**Phase 1: PoC (2-3 hours)** ← We are here

1. Install FastMCP
1. Implement 3 tools
1. Test with Ansible playbook
1. Go/No-Go decision

**Phase 2: Full Migration (1-2 days)**

- Migrate Airflow tools
- Update containers
- Production deployment

**Total: 4-6 days vs weeks debugging**

## Positive Consequences

- ✅ 90% less code to maintain
- ✅ More reliable connections
- ✅ Faster development of new tools
- ✅ Better error handling
- ✅ Multiple transports (SSE, HTTP, stdio)

## Negative Consequences

- ⚠️ New dependency (fastmcp)
- ⚠️ Migration time (4-6 days)

## Links

- **FastMCP:** https://github.com/jlowin/fastmcp
- **Status:** `/root/qubinode_navigator/MCP-IMPLEMENTATION-STATUS.md`

______________________________________________________________________

## Implementation Status

**Implementation Complete (2025-12-05):**

- ✅ Phase 1 (PoC): Completed - FastMCP installed and tested
- ✅ Phase 2 (Full Migration): Completed - All tools migrated

**Production Deployments:**

| Server                  | Location                                | Tools    | Status     |
| ----------------------- | --------------------------------------- | -------- | ---------- |
| Airflow MCP             | `airflow/scripts/mcp_server_fastmcp.py` | 24 tools | Production |
| AI Assistant MCP (HTTP) | `ai-assistant/mcp_server_fastmcp.py`    | 2 tools  | PoC        |
| AI Assistant MCP (CLI)  | `ai-assistant/mcp_server_cli.py`        | 2 tools  | Production |

**Tool Categories Implemented:**

- RAG Query Tools (4): query_rag, ingest_to_rag, manage_rag_documents, get_rag_stats
- Troubleshooting Tools (4): get_troubleshooting_history, log_troubleshooting_attempt, search_similar_errors, diagnose_issue
- DAG Management (3): list_dags, get_dag_info, trigger_dag
- VM Operations (5): list_vms, get_vm_info, create_vm, delete_vm, preflight_vm_creation
- Lineage & Analytics (4): get_dag_lineage, get_failure_blast_radius, get_dataset_lineage, get_lineage_stats
- Agent Orchestration (4): check_provider_exists, compute_confidence_score, get_workflow_guide, get_airflow_status
