# ADR-0049 Implementation Plan

## Multi-Agent LLM Memory Architecture

**Status:** ✅ COMPLETE
**Started:** 2025-12-01
**Completed:** 2025-12-05
**Duration:** 5 days (accelerated from 10-week target)

> **Note:** This is a companion document to [ADR-0049](adr-0049-multi-agent-llm-memory-architecture.md),
> providing detailed implementation phases and progress tracking.

______________________________________________________________________

## Phase 1: PgVector Foundation (Week 1-2)

### Goals

- Add pgvector extension to Airflow PostgreSQL
- Create database schema for RAG and troubleshooting memory
- Implement local embedding generation
- Basic RAG query functionality

### Tasks

#### 1.1 PostgreSQL PgVector Setup

- [ ] Update Airflow docker-compose to use PostgreSQL with pgvector
- [ ] Create initialization script for pgvector extension
- [ ] Test pgvector functionality

**Files to create/modify:**

```
airflow/docker-compose.yml          # Add pgvector-enabled postgres image
airflow/init-scripts/001-pgvector.sql  # Extension and schema setup
```

#### 1.2 Database Schema

- [ ] Create `rag_documents` table for document embeddings
- [ ] Create `troubleshooting_attempts` table for learning
- [ ] Create `agent_decisions` table for decision logging
- [ ] Create indexes for vector similarity search

**SQL Schema:**

```sql
-- rag_documents: Store document embeddings
-- troubleshooting_attempts: Store troubleshooting history
-- agent_decisions: Log all agent decisions
```

#### 1.3 Embedding Service

- [ ] Create embedding service using sentence-transformers
- [ ] Support local model (MiniLM-L6) for disconnected environments
- [ ] Optional: OpenAI ada-002 for connected environments
- [ ] Create embedding API endpoint

**Files to create:**

```
airflow/plugins/qubinode/embedding_service.py
airflow/plugins/qubinode/rag_store.py
```

#### 1.4 Basic RAG Operations

- [ ] Implement document ingestion (chunk + embed + store)
- [ ] Implement similarity search
- [ ] Implement metadata filtering
- [ ] Unit tests for RAG operations

**Files to create:**

```
airflow/plugins/qubinode/rag_operations.py
tests/test_rag_operations.py
```

### Deliverables

- [ ] PgVector running in Airflow PostgreSQL
- [ ] Schema deployed and tested
- [ ] Embedding service functional
- [ ] Basic RAG queries working

______________________________________________________________________

## Phase 2: MCP Enhancement (Week 3-4)

### Goals

- Add RAG query tools to MCP server
- Add troubleshooting history tools
- Add developer delegation tools
- Add override mechanism

### Tasks

#### 2.1 RAG Query Tools

- [ ] `query_rag()` - Search documents by semantic similarity
- [ ] `ingest_to_rag()` - Add new documents
- [ ] `list_rag_documents()` - List documents by type

**File to modify:**

```
airflow/plugins/qubinode/mcp_server_fastmcp.py
```

#### 2.2 Troubleshooting Memory Tools

- [ ] `get_troubleshooting_history()` - Retrieve past attempts
- [ ] `log_troubleshooting_attempt()` - Record new attempt
- [ ] `search_similar_errors()` - Find similar past errors

#### 2.3 Agent Orchestration Tools

- [ ] `delegate_to_developer()` - Send task to Developer Agent
- [ ] `override_developer()` - Override with explicit instruction
- [ ] `get_agent_status()` - Check agent state
- [ ] `check_provider_exists()` - Provider-First enforcement

#### 2.4 Testing with Calling LLM

- [ ] Test MCP tools with Claude Code
- [ ] Verify RAG queries return relevant results
- [ ] Test override mechanism
- [ ] Document tool usage patterns

### Deliverables

- [ ] 8+ new MCP tools deployed
- [ ] Tools tested with Claude Code
- [ ] Documentation for each tool

______________________________________________________________________

## Phase 3: Agent Architecture (Week 5-6)

### Goals

- Implement Manager LLM via LiteLLM
- Implement Developer Agent with confidence scoring
- Integrate Aider for code generation
- Implement four core policies

### Tasks

#### 3.1 LiteLLM Integration

- [ ] Add LiteLLM to Airflow container
- [ ] Configure model routing (Granite models)
- [ ] Create LiteLLM proxy service
- [ ] Test model availability

**Files to create:**

```
airflow/plugins/qubinode/litellm_config.yaml
airflow/plugins/qubinode/llm_router.py
```

#### 3.2 Manager LLM Implementation

- [ ] Create Manager agent class
- [ ] Implement session context management
- [ ] Implement escalation logic
- [ ] Implement provider plan generation

**Files to create:**

```
airflow/plugins/qubinode/agents/manager_agent.py
```

#### 3.3 Developer Agent Implementation

- [ ] Create Developer agent class
- [ ] Implement RAG-augmented task processing
- [ ] Implement confidence scoring algorithm
- [ ] Integrate Aider for code generation

**Files to create:**

```
airflow/plugins/qubinode/agents/developer_agent.py
airflow/plugins/qubinode/agents/confidence_scorer.py
```

#### 3.4 Policy Implementation

- [ ] Policy 1: Confidence & RAG Enrichment
- [ ] Policy 2: Provider-First Rule
- [ ] Policy 3: Missing Provider → Plan
- [ ] Policy 4: Calling LLM Override

**Files to create:**

```
airflow/plugins/qubinode/agents/policies.py
```

#### 3.5 End-to-End Testing

- [ ] Test complete workflow: User → Calling LLM → Manager → Developer
- [ ] Test escalation paths
- [ ] Test override mechanism
- [ ] Test confidence-based stopping

### Deliverables

- [ ] Manager and Developer agents functional
- [ ] Four policies implemented
- [ ] Aider integration working
- [ ] End-to-end workflow tested

______________________________________________________________________

## Phase 4: OpenLineage Integration (Week 7-8)

### Goals

- Deploy Marquez alongside Airflow
- Configure Airflow OpenLineage provider
- Add custom facets for code lineage
- Implement lineage query tools

### Tasks

#### 4.1 Marquez Deployment

- [ ] Add Marquez to docker-compose
- [ ] Add Marquez Web UI
- [ ] Configure networking
- [ ] Test Marquez API

**File to modify:**

```
airflow/docker-compose.yml
```

#### 4.2 Airflow OpenLineage Configuration

- [ ] Install apache-airflow-providers-openlineage
- [ ] Configure OpenLineage transport to Marquez
- [ ] Set namespace to 'qubinode'
- [ ] Test lineage collection from DAG runs

**Files to modify:**

```
airflow/Dockerfile              # Add provider
airflow/config/airflow.cfg      # OpenLineage config
```

#### 4.3 Custom Facets

- [ ] Create `.OpenLineage.job.facets.json` template
- [ ] Include git commit SHA in facets
- [ ] Include branch information
- [ ] Automate facet generation on DAG deployment

**Files to create:**

```
airflow/dags/.OpenLineage.job.facets.json
airflow/scripts/generate-lineage-facets.sh
```

#### 4.4 Lineage Query Tools

- [ ] `get_dag_lineage()` - Query upstream/downstream
- [ ] `get_failure_blast_radius()` - Impact analysis
- [ ] `get_dataset_lineage()` - Track data flow
- [ ] Add to MCP server

### Deliverables

- [ ] Marquez running and collecting lineage
- [ ] Custom facets deployed
- [ ] Lineage tools in MCP server
- [ ] Visualization dashboard accessible

______________________________________________________________________

## Phase 5: Bootstrap & Polish (Week 9-10)

### Goals

- Create RAG bootstrap DAG
- Ingest core documentation
- Performance tuning
- Documentation and training

### Tasks

#### 5.1 RAG Bootstrap DAG

- [ ] Create `rag_bootstrap` DAG
- [ ] Task: Ingest all ADRs
- [ ] Task: Ingest existing DAGs as examples
- [ ] Task: Ingest Airflow provider docs
- [ ] Task: Verify RAG health

**Files to create:**

```
airflow/dags/rag_bootstrap.py
```

#### 5.2 Documentation Ingestion

- [ ] Ingest `docs/adrs/*.md`
- [ ] Ingest `airflow/dags/*.py`
- [ ] Ingest key provider documentation
- [ ] Ingest kcli-pipelines docs

#### 5.3 Performance Tuning

- [ ] Tune PgVector indexes (IVFFlat lists)
- [ ] Add query caching
- [ ] Optimize embedding batch size
- [ ] Benchmark RAG query latency

#### 5.4 Documentation

- [ ] Update ADR-0049 with implementation notes
- [ ] Create user guide for new MCP tools
- [ ] Document agent interaction patterns
- [ ] Create troubleshooting guide

**Files to create:**

```
docs/guides/multi-agent-llm-guide.md
docs/guides/rag-operations-guide.md
```

#### 5.5 Integration Testing

- [ ] Full system test with real user scenarios
- [ ] Test disconnected/air-gapped operation
- [ ] Test context persistence across sessions
- [ ] Validate learning from troubleshooting

### Deliverables

- [ ] Bootstrap DAG functional
- [ ] Core documentation ingested
- [ ] Performance meets targets (\<500ms RAG queries)
- [ ] User documentation complete

______________________________________________________________________

## Quick Start: Phase 1 Today

Let's begin Phase 1 immediately with these first tasks:

### Task 1.1.1: Update docker-compose for PgVector

```yaml
# Use pgvector-enabled PostgreSQL image
postgres:
  image: pgvector/pgvector:pg15
  # ... rest of config
```

### Task 1.2.1: Create schema SQL

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(384),  -- MiniLM-L6 dimensions
    metadata JSONB,
    doc_type VARCHAR(50),
    source_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON rag_documents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### Task 1.3.1: Create embedding service

```python
# Basic embedding service using sentence-transformers
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def embed_text(text: str) -> list[float]:
    return model.encode(text).tolist()
```

______________________________________________________________________

## Progress Tracking

| Phase                            | Status      | Started    | Completed  | Notes                                       |
| -------------------------------- | ----------- | ---------- | ---------- | ------------------------------------------- |
| Phase 1: PgVector Foundation     | ✅ Complete | 2025-12-01 | 2025-12-03 | PgVector schema deployed, embedding service |
| Phase 2: MCP Enhancement         | ✅ Complete | 2025-12-01 | 2025-12-04 | 24 MCP tools in production                  |
| Phase 3: Agent Architecture      | ✅ Complete | 2025-12-03 | 2025-12-04 | Manager, Developer agents, Policy engine    |
| Phase 4: OpenLineage Integration | ✅ Complete | 2025-12-04 | 2025-12-05 | Marquez deployed with Airflow integration   |
| Phase 5: Bootstrap & Polish      | ✅ Complete | 2025-12-05 | 2025-12-05 | RAG bootstrap DAG, 84% test coverage        |

### Implementation Summary (2025-12-05)

**All Components Implemented:**

#### Phase 1: PgVector Foundation

- ✅ PgVector extension in Airflow PostgreSQL (`pgvector/pgvector:pg15`)
- ✅ Database schema (`airflow/init-scripts/001-pgvector-schema.sql`)
- ✅ Embedding service with 3 providers: host, local, OpenAI (`airflow/plugins/qubinode/embedding_service.py`)
- ✅ RAG store with semantic search (`airflow/plugins/qubinode/rag_store.py`)

#### Phase 2: MCP Enhancement

- ✅ FastMCP server with 24 tools (`airflow/scripts/mcp_server_fastmcp.py`)
- ✅ RAG query tools (4): query_rag, ingest_to_rag, manage_rag_documents, get_rag_stats
- ✅ Troubleshooting tools (4): history, logging, error search, diagnosis
- ✅ Agent orchestration tools (4): provider check, confidence score, workflow guide, status

#### Phase 3: Agent Architecture

- ✅ Manager Agent (`airflow/plugins/qubinode/agents/manager_agent.py`)
- ✅ Developer Agent with Aider integration (`airflow/plugins/qubinode/agents/developer_agent.py`)
- ✅ Policy Engine with 4 core policies (`airflow/plugins/qubinode/agents/policies.py`)
- ✅ Confidence Scorer (`airflow/plugins/qubinode/agents/confidence_scorer.py`)
- ✅ LLM Router with environment-aware model selection (`airflow/plugins/qubinode/llm_router.py`)

#### Phase 4: OpenLineage Integration

- ✅ Marquez deployment in docker-compose
- ✅ Marquez Web UI for lineage visualization
- ✅ Airflow OpenLineage provider configured
- ✅ Lineage query tools (4): dag_lineage, blast_radius, dataset_lineage, stats

#### Phase 5: Bootstrap & Polish

- ✅ RAG bootstrap DAG (`airflow/dags/rag_bootstrap.py`)
- ✅ Document ingestion DAG (`airflow/dags/rag_document_ingestion.py`)
- ✅ AI Assistant test suite with 84% coverage (ADR-0056-0060)
- ✅ `qubinode-ai` CLI for AI assistant interaction
- ✅ `rag-cli.py` for standalone RAG operations

**AI Assistant (Interim State):**

- ✅ Qdrant-based RAG service (interim solution per ADR-0027)
- ⏳ Migration to shared PgVector (future consolidation)

### Related ADRs

- **[ADR-0027](adr-0027-cpu-based-ai-deployment-assistant-architecture.md)**: AI Assistant core (RAG component superseded)
- **[ADR-0038](adr-0038-fastmcp-framework-migration.md)**: FastMCP server implementation
- **[ADR-0050](adr-0050-hybrid-host-container-architecture.md)**: Resource optimization architecture
- **[ADR-0056-0060](adr-0056-ai-assistant-test-strategy-overview.md)**: AI Assistant testing strategy

______________________________________________________________________

## Dependencies

### Python Packages

```
sentence-transformers>=2.2.0
pgvector>=0.2.0
psycopg2-binary>=2.9.0
litellm>=1.0.0
aider-chat>=0.30.0
openlineage-airflow>=1.0.0
```

### Docker Images

```
pgvector/pgvector:pg15
marquezproject/marquez:latest
marquezproject/marquez-web:latest
```

### External Services (Optional)

- OpenAI API (for ada-002 embeddings in connected environments)
- Claude API (Calling LLM - already via Claude Code)
