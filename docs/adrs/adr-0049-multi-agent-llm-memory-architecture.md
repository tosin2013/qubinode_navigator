______________________________________________________________________

## layout: default title: ADR-0049 Multi-Agent LLM Memory Architecture parent: Architecture & Design grand_parent: Architectural Decision Records nav_order: 0049

# ADR-0049: Multi-Agent LLM Memory Architecture with PgVector and OpenLineage

## Status

Proposed (2025-12-01)

## Context

### The Problem: Context Loss During Development

Current LLM interactions with Qubinode suffer from critical context loss:

1. **Session Amnesia**: LLMs forget earlier troubleshooting attempts, repeating failed approaches
1. **Cross-Component Blindness**: When debugging DAGs + application code together, context fragments
1. **No Learning**: Each session starts fresh; past successes and failures aren't leveraged
1. **Single-Model Limitations**: Small local models (Granite) lack capacity for complex architectural decisions

### Current State (ADR-0027)

ADR-0027 established the AI Deployment Assistant with:

- ChromaDB for vector storage (document RAG)
- Single-agent architecture
- No execution lineage tracking
- No multi-model orchestration

### Why Change?

| Current Limitation                             | Impact                                                |
| ---------------------------------------------- | ----------------------------------------------------- |
| ChromaDB is separate from Airflow's PostgreSQL | Two databases to manage, no unified queries           |
| No execution history in RAG                    | Can't learn from past deployments                     |
| Single agent model                             | Small model can't handle architecture decisions       |
| No lineage tracking                            | Can't trace DAG relationships or failure blast radius |
| Session-bound context                          | Troubleshooting restarts lose all progress            |

## Decision

Implement a **Multi-Agent LLM Architecture** with persistent memory using PgVector and OpenLineage.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Multi-Agent LLM Architecture                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  CALLING LLM (Claude/GPT-4 via MCP)                                       │  │
│  │  ════════════════════════════════════════════════════════════════════     │  │
│  │  • GLOBAL context: Full session, ADRs, architecture, user intent          │  │
│  │  • Override authority: Can direct Developer Agent explicitly              │  │
│  │  • Intervention triggers:                                                 │  │
│  │    - Developer confidence < 0.6                                           │  │
│  │    - Repeated failures (same error 2+ times)                              │  │
│  │    - Cross-cutting concerns (security, architecture)                      │  │
│  │    - User escalation ("take over")                                        │  │
│  │  • MCP Tools: All existing + new agent orchestration tools                │  │
│  └────────────────────────────────┬──────────────────────────────────────────┘  │
│                                   │                                              │
│                                   │ MCP Protocol                                 │
│                                   ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  MCP SERVER (Enhanced FastMCP)                                            │  │
│  │  ════════════════════════════════════════════════════════════════════     │  │
│  │  • Routes requests to appropriate agent                                   │  │
│  │  • Logs all decisions to PgVector                                         │  │
│  │  • Exposes RAG query tools to Calling LLM                                 │  │
│  │  • Provides agent orchestration tools                                     │  │
│  └────────────────────────────────┬──────────────────────────────────────────┘  │
│                                   │                                              │
│                    ┌──────────────┴──────────────┐                               │
│                    ▼                              ▼                               │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────────┐   │
│  │  MANAGER LLM                │  │  DEVELOPER AGENT                        │   │
│  │  (Granite via LiteLLM)      │  │  (Granite + Aider)                      │   │
│  │  ══════════════════════     │  │  ═══════════════════════════════════    │   │
│  │  • SESSION context          │  │  • TASK context only                    │   │
│  │  • Orchestrates Developer   │  │  • RAG-augmented per task               │   │
│  │  • Escalates when needed    │  │  • Confidence scoring                   │   │
│  │  • Designs provider plans   │  │  • Code generation via Aider            │   │
│  └──────────────┬──────────────┘  └──────────────┬──────────────────────────┘   │
│                 │                                 │                               │
│                 └─────────────┬───────────────────┘                               │
│                               ▼                                                   │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  PERSISTENT MEMORY LAYER                                                  │  │
│  │  ════════════════════════════════════════════════════════════════════     │  │
│  │                                                                           │  │
│  │  ┌─────────────────────────────┐  ┌─────────────────────────────────┐    │  │
│  │  │  PgVector (PostgreSQL)      │  │  OpenLineage + Marquez          │    │  │
│  │  │  ─────────────────────────  │  │  ─────────────────────────────  │    │  │
│  │  │  • Document embeddings      │  │  • DAG execution lineage        │    │  │
│  │  │  • Troubleshooting history  │  │  • Dataset relationships        │    │  │
│  │  │  • Code change context      │  │  • Task dependencies            │    │  │
│  │  │  • Confidence scores        │  │  • Failure blast radius         │    │  │
│  │  │  • Decision logs            │  │  • Cross-DAG impact             │    │  │
│  │  └─────────────────────────────┘  └─────────────────────────────────┘    │  │
│  │                                                                           │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Git Integration (via Aider)                                        │ │  │
│  │  │  • Commit history linkage                                           │ │  │
│  │  │  • Code change attribution                                          │ │  │
│  │  │  • Rollback capability                                              │ │  │
│  │  └─────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Core Policies

#### Policy 1: Confidence & RAG Enrichment

For any task, Developer Agent MUST:

1. **Query RAG** for relevant context:

   - Airflow provider documentation
   - Qubinode infrastructure patterns
   - Related DAGs and ADRs
   - Past troubleshooting attempts

1. **Compute confidence score**:

   ```python
   confidence = (
       0.4 * rag_similarity_score +      # How close are matching docs
       0.3 * rag_hit_count_normalized +  # How many relevant docs found
       0.2 * provider_exists +            # Binary: official provider?
       0.1 * similar_dag_exists           # Have we done this before?
   )
   ```

1. **Act based on confidence**:

   - **High (≥0.8)**: Proceed with task
   - **Medium (0.6-0.8)**: Proceed with caveats noted
   - **Low (\<0.6)**: STOP and escalate

1. **Low confidence escalation**:

   ```
   Developer → Manager: "I don't have enough docs for <X>.
                        Request docs or links for RAG ingestion."

   Manager → Calling LLM: "To proceed safely, we need:
                          - Documentation for <X>
                          - Example implementations
                          Can you provide links or files?"

   User provides docs → Ingested to PgVector → Developer retries
   ```

#### Policy 2: Provider-First Rule

For any external system integration, Developer Agent MUST:

1. **Check Airflow provider registry** (via RAG or provider index)
1. **If provider exists**: Use official operators/hooks
1. **If NO provider exists**: STOP and escalate

```
Developer: "No Airflow provider found for <X>.
           Cannot safely interact via standard operators.
           Request guidance for provider design or alternative architecture."
```

Developer will NOT:

- Invent pseudo-provider layers in DAGs
- Use BashOperator/PythonOperator when official provider exists
- Guess at API interactions without documentation

#### Policy 3: Missing Provider → Plan, Not Code

When Provider-First Rule fails:

1. **Developer reports**:

   - What it searched for
   - Why provider doesn't exist (no docs, no matches)

1. **Manager + Calling LLM collaborate**:

   - Sketch provider architecture
   - Define required connections, APIs, operators
   - Consider alternatives ("Should this be in Airflow at all?")

1. **Output is a plan document**:

   - `docs/provider_plan_<name>.md`
   - ADR if architectural significance
   - TODOs/issues in tracker

1. **Developer STOPS there** - no auto-generated provider code

#### Policy 4: Calling LLM Override Authority

The Calling LLM (Claude/GPT-4) can override Developer Agent when:

| Trigger                 | Action                                                                                   |
| ----------------------- | ---------------------------------------------------------------------------------------- |
| **Repeated Failure**    | Same error class 2+ times → Calling LLM reviews full history, provides explicit approach |
| **Architecture Scope**  | Change affects multiple DAGs → Developer MUST NOT proceed alone                          |
| **Confidence Deadlock** | Developer stuck at low confidence → Calling LLM provides context or accepts risk         |
| **User Request**        | Human says "take over" → Calling LLM assumes direct control                              |

Override instruction format:

```json
{
  "override": true,
  "instruction": "specific approach to take",
  "reasoning": "why previous attempts failed",
  "constraints": ["must check X", "do not try Y"],
  "confidence_override": true
}
```

### Component Details

#### 1. PgVector Integration (Replaces ChromaDB)

**Why PgVector over ChromaDB:**

- Already have PostgreSQL for Airflow
- Single database to manage
- ACID compliance for vector operations
- Lower operational overhead
- SQL queries can join vectors with execution metadata

**Schema:**

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Document embeddings (RAG)
CREATE TABLE rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 or local model
    metadata JSONB,
    doc_type VARCHAR(50),    -- 'adr', 'provider_doc', 'dag', 'troubleshooting'
    source_path TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Troubleshooting memory
CREATE TABLE troubleshooting_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    task_description TEXT,
    error_message TEXT,
    attempted_solution TEXT,
    result VARCHAR(20),      -- 'success', 'failed', 'partial'
    embedding vector(1536),
    confidence_score FLOAT,
    override_by VARCHAR(50), -- NULL, 'manager', 'calling_llm'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Decision log
CREATE TABLE agent_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent VARCHAR(50),       -- 'developer', 'manager', 'calling_llm'
    decision_type VARCHAR(50),
    context JSONB,
    decision TEXT,
    confidence FLOAT,
    rag_hits INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for similarity search
CREATE INDEX ON rag_documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON troubleshooting_attempts USING ivfflat (embedding vector_cosine_ops);
```

#### 2. OpenLineage + Marquez Integration

**Purpose:** Track execution lineage, DAG relationships, failure blast radius

**Deployment:**

```yaml
# docker-compose addition
services:
  marquez:
    image: marquezproject/marquez:latest
    network_mode: host
    environment:
      - MARQUEZ_PORT=5001
      - MARQUEZ_ADMIN_PORT=5002
    depends_on:
      - postgres

  marquez-web:
    image: marquezproject/marquez-web:latest
    network_mode: host
    environment:
      - MARQUEZ_HOST=localhost
      - MARQUEZ_PORT=5001
```

**Airflow Configuration:**

```python
# airflow.cfg or environment
AIRFLOW__OPENLINEAGE__TRANSPORT = '{"type": "http", "url": "http://localhost:5001/api/v1/lineage"}'
AIRFLOW__OPENLINEAGE__NAMESPACE = 'qubinode'
```

**Custom Facets for Code Lineage:**

```json
// .OpenLineage.job.facets.json (in DAG deployment)
{
  "sourceCodeLocation": {
    "_producer": "qubinode-navigator",
    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SourceCodeLocationJobFacet.json",
    "type": "git",
    "url": "https://github.com/tosin2013/qubinode_navigator",
    "repoUrl": "https://github.com/tosin2013/qubinode_navigator.git",
    "path": "airflow/dags/",
    "version": "{{ git_commit_sha }}",
    "branch": "{{ git_branch }}"
  }
}
```

#### 3. MCP Server Enhancement

New tools for Calling LLM to interact with agent system:

```python
# New MCP tools for agent orchestration

@mcp.tool()
async def query_rag(query: str, doc_types: Optional[List[str]] = None, limit: int = 5) -> str:
    """
    Query the RAG store for relevant documents and context.

    Args:
        query: Natural language query
        doc_types: Filter by type ('adr', 'provider_doc', 'dag', 'troubleshooting')
        limit: Maximum results to return

    Returns:
        Relevant documents with similarity scores
    """
    pass

@mcp.tool()
async def get_troubleshooting_history(
    error_pattern: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Retrieve past troubleshooting attempts for learning.

    Args:
        error_pattern: Search for similar errors
        session_id: Get history from specific session
        limit: Maximum results

    Returns:
        Past attempts with outcomes and learnings
    """
    pass

@mcp.tool()
async def delegate_to_developer(
    task: str,
    context: Optional[Dict[str, Any]] = None,
    override_confidence: bool = False
) -> str:
    """
    Delegate a development task to the Developer Agent.

    Args:
        task: Task description
        context: Additional context to pass
        override_confidence: Skip confidence check (Calling LLM takes responsibility)

    Returns:
        Developer Agent response with confidence score
    """
    pass

@mcp.tool()
async def override_developer(
    instruction: str,
    reasoning: str,
    constraints: Optional[List[str]] = None
) -> str:
    """
    Override Developer Agent with explicit instruction.
    Use when Developer is stuck or repeating failures.

    Args:
        instruction: Specific approach to take
        reasoning: Why previous attempts failed
        constraints: What to do/not do

    Returns:
        Execution result
    """
    pass

@mcp.tool()
async def ingest_to_rag(
    content: str,
    doc_type: str,
    source: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Ingest new documentation into RAG store.

    Args:
        content: Document content (markdown, code, etc.)
        doc_type: Type classification
        source: Source URL or path
        metadata: Additional metadata

    Returns:
        Confirmation with document ID
    """
    pass

@mcp.tool()
async def get_dag_lineage(dag_id: str, depth: int = 2) -> str:
    """
    Get execution lineage for a DAG from OpenLineage/Marquez.

    Args:
        dag_id: The DAG to query
        depth: How many levels of dependencies to traverse

    Returns:
        Lineage graph showing upstream/downstream relationships
    """
    pass

@mcp.tool()
async def get_failure_blast_radius(dag_id: str, task_id: Optional[str] = None) -> str:
    """
    Analyze impact of a DAG or task failure.

    Args:
        dag_id: The failed DAG
        task_id: Specific task that failed (optional)

    Returns:
        List of affected downstream DAGs and datasets
    """
    pass

@mcp.tool()
async def check_provider_exists(system_name: str) -> str:
    """
    Check if an Airflow provider exists for a system.

    Args:
        system_name: Name of external system (e.g., 'azure', 'snowflake')

    Returns:
        Provider info if exists, or "NOT_FOUND" with alternatives
    """
    pass
```

#### 4. Embedding Model Selection

**For Disconnected/Air-gapped Environments:**

```python
# Local embedding model (runs on CPU)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dimensions
# Or: "BAAI/bge-small-en-v1.5"  # 384 dimensions, better quality
```

**For Connected Environments:**

```python
# OpenAI embeddings via LiteLLM
EMBEDDING_MODEL = "text-embedding-ada-002"  # 1536 dimensions
```

**Configuration:**

```yaml
# Environment-based selection
embedding:
  model: ${EMBEDDING_MODEL:-sentence-transformers/all-MiniLM-L6-v2}
  dimensions: ${EMBEDDING_DIMENSIONS:-384}
  provider: ${EMBEDDING_PROVIDER:-local}  # 'local' or 'openai'
```

#### 5. Bootstrap / Cold Start Strategy

Initial RAG population order:

1. **Phase 1: Core Documentation**

   ```
   - docs/adrs/*.md (all ADRs)
   - airflow/dags/*.py (existing DAGs as examples)
   - README files
   ```

1. **Phase 2: Airflow Provider Docs**

   ```
   - apache-airflow-providers-* documentation
   - Focus on: postgres, ssh, http, kubernetes
   ```

1. **Phase 3: Qubinode-Specific**

   ```
   - kcli-pipelines scripts and docs
   - freeipa-workshop-deployer docs
   - Existing deployment patterns
   ```

1. **Phase 4: On-Demand**

   ```
   - User-provided docs when confidence is low
   - External documentation fetched on request
   ```

Bootstrap DAG:

```python
# dags/rag_bootstrap.py
from airflow.decorators import dag, task
from datetime import datetime

@dag(
    dag_id='rag_bootstrap',
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # Manual trigger only
    tags=['rag', 'bootstrap', 'setup']
)
def rag_bootstrap():

    @task
    def ingest_adrs():
        """Ingest all ADR documents."""
        pass

    @task
    def ingest_existing_dags():
        """Ingest existing DAGs as examples."""
        pass

    @task
    def ingest_provider_docs():
        """Ingest Airflow provider documentation."""
        pass

    @task
    def verify_rag_health():
        """Verify RAG store is queryable."""
        pass

    ingest_adrs() >> ingest_existing_dags() >> ingest_provider_docs() >> verify_rag_health()

rag_bootstrap()
```

### Model Selection

| Agent               | Model                        | Context Window | Purpose                                          |
| ------------------- | ---------------------------- | -------------- | ------------------------------------------------ |
| **Calling LLM**     | Claude/GPT-4 (via MCP)       | 100K+          | Global context, architecture, override authority |
| **Manager LLM**     | Granite-8B (via LiteLLM)     | 8K             | Session orchestration, escalation decisions      |
| **Developer Agent** | Granite-3B + Aider           | 4K             | Task execution, code generation                  |
| **Embeddings**      | MiniLM-L6 (local) or ada-002 | N/A            | Vector generation                                |

### Workflow Example: Troubleshooting with Memory

```
┌─────────────────────────────────────────────────────────────────────────┐
│  User: "FreeIPA deployment is failing with DNS error"                   │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Calling LLM (Claude)                                                    │
│  ───────────────────────────────────────────────────────────────────    │
│  1. Queries RAG: "freeipa dns error troubleshooting"                    │
│  2. Finds: 2 past attempts, both failed checking DNS config             │
│  3. Recognizes pattern: "Both missed firewall check"                    │
│  4. Delegates with override:                                            │
│     {                                                                    │
│       "override": true,                                                  │
│       "instruction": "Check firewalld for port 53 before DNS config",  │
│       "reasoning": "Past 2 attempts checked DNS but not firewall",      │
│       "constraints": ["check firewall FIRST", "don't repeat DNS check"] │
│     }                                                                    │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Developer Agent                                                         │
│  ───────────────────────────────────────────────────────────────────    │
│  1. Receives override instruction                                        │
│  2. Skips confidence check (Calling LLM responsible)                    │
│  3. Executes: firewall-cmd --list-ports                                 │
│  4. Finds: Port 53 NOT open                                             │
│  5. Fixes: firewall-cmd --add-port=53/tcp --permanent                   │
│  6. Re-runs FreeIPA install → SUCCESS                                   │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PgVector: Store Learning                                                │
│  ───────────────────────────────────────────────────────────────────    │
│  {                                                                       │
│    "error_pattern": "freeipa dns error",                                │
│    "root_cause": "firewall blocking port 53",                           │
│    "solution": "open port 53 in firewalld",                             │
│    "confidence": 0.95,                                                   │
│    "source": "calling_llm_override"                                     │
│  }                                                                       │
│                                                                          │
│  Next time: Developer checks firewall FIRST (RAG retrieves this)        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Consequences

### Positive

1. **No More Context Loss**: PgVector persists all troubleshooting attempts across sessions
1. **Learning System**: Past successes and failures inform future decisions
1. **Unified RAG**: AI assistant, MCP server, and DAGs share same knowledge base
1. **Appropriate Model for Task**: Large model for architecture, small model for execution
1. **Calling LLM Override**: Prevents small model from spinning on repeated failures
1. **Execution Lineage**: OpenLineage tracks DAG relationships and failure blast radius
1. **Provider Compliance**: Forces use of official Airflow providers
1. **Disconnected Support**: Local embedding model works air-gapped

### Negative

1. **Increased Complexity**: Multiple agents, databases, and orchestration layers
1. **PostgreSQL Dependency**: PgVector requires PostgreSQL (already have for Airflow)
1. **Marquez Overhead**: Additional container for lineage visualization
1. **Bootstrap Time**: Initial RAG population takes time
1. **Model Coordination**: LiteLLM routing adds latency

### Mitigations

| Risk                  | Mitigation                                        |
| --------------------- | ------------------------------------------------- |
| Complexity            | Phased implementation, clear component boundaries |
| PostgreSQL dependency | Already required for Airflow                      |
| Marquez overhead      | Optional component, can start with PgVector only  |
| Bootstrap time        | Background DAG, prioritized ingestion             |
| Latency               | Cache frequent queries, async operations          |

## Implementation Phases

### Phase 1: PgVector Foundation (Week 1-2)

- Add pgvector extension to Airflow PostgreSQL
- Create schema for RAG documents and troubleshooting
- Implement embedding generation (local model)
- Basic RAG query functionality
- Migrate existing ChromaDB data (if any)

### Phase 2: MCP Enhancement (Week 3-4)

- Add new MCP tools for RAG queries
- Add troubleshooting history tools
- Add developer delegation tools
- Add override mechanism
- Test with Calling LLM (Claude Code)

### Phase 3: Agent Architecture (Week 5-6)

- Implement Manager LLM via LiteLLM
- Implement Developer Agent with confidence scoring
- Integrate Aider for code generation
- Implement four core policies
- End-to-end workflow testing

### Phase 4: OpenLineage Integration (Week 7-8)

- Deploy Marquez alongside Airflow
- Configure Airflow OpenLineage provider
- Add custom facets for code lineage
- Implement lineage query tools
- Dashboard for visualization

### Phase 5: Bootstrap & Polish (Week 9-10)

- Create RAG bootstrap DAG
- Ingest core documentation
- Performance tuning
- Documentation and training

## References

- [ADR-0027: CPU-Based AI Deployment Assistant](adr-0027-cpu-based-ai-deployment-assistant-architecture.md) - Superseded for RAG component
- [ADR-0036: Apache Airflow Workflow Orchestration](adr-0036-apache-airflow-workflow-orchestration-integration.md)
- [ADR-0038: FastMCP Framework Migration](adr-0038-fastmcp-framework-migration.md) - MCP server being enhanced
- [ADR-0046: DAG Validation Pipeline](adr-0046-dag-validation-pipeline-and-host-execution.md)
- [PgVector Documentation](https://github.com/pgvector/pgvector)
- [OpenLineage Airflow Integration](https://openlineage.io/docs/integrations/airflow/)
- [Marquez Project](https://marquezproject.ai/)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Aider Documentation](https://aider.chat/)

## Future Considerations

1. **Feedback Loop**: Human approval/rejection training the confidence model
1. **Cost Management**: Rate limiting for external LLM APIs
1. **Multi-tenant**: Namespace isolation for different users/projects
1. **Metrics Dashboard**: Confidence scores, override frequency, RAG hit rates
1. **Provider Auto-Generation**: Eventually, auto-generate missing providers (carefully)
