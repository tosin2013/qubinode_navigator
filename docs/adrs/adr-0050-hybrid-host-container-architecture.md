---
layout: default
title: ADR-0050 Hybrid Host-Container Architecture
parent: Architecture & Design
grand_parent: Architectural Decision Records
nav_order: 0050
---

# ADR-0050: Hybrid Host-Container Architecture for Resource Optimization

## Status
Proposed (2025-12-01)

## Context

### The Problem: Heavy Container Images

ADR-0049 introduced a multi-agent LLM architecture with several heavy dependencies:

| Component | Size Impact | Reason |
|-----------|-------------|--------|
| sentence-transformers | ~1.5GB | PyTorch + model weights |
| litellm + aider-chat | ~500MB+ | LLM routing + code agent |
| libvirt-dev, gcc, python3-dev | ~300MB | Build dependencies |

The resulting Airflow container image is **~10.5GB**, which causes:

1. **Long build times** (~10-15 minutes)
2. **High memory usage** when container starts
3. **Slow deployment** when pulling/pushing images
4. **Resource contention** with actual workloads

### Scheduler Memory Issues

Research into Airflow scheduler crashes revealed several issues affecting RHEL-based systems:

1. **Known memory leaks** in Airflow 2.10.x ([Issue #50708](https://github.com/apache/airflow/issues/50708))
2. **nofile ulimit issue** on RHEL/Rocky causing memory explosion ([Discussion #29731](https://github.com/apache/airflow/discussions/29731))
3. **DAG parsing overhead** - complex DAGs parsed frequently consume memory
4. **Top-level code execution** - imports outside tasks run on every parse

### Current Architecture (ADR-0049)

All components run in containers:
```
┌─────────────────────────────────────────────────┐
│  Container: qubinode-airflow (10.5GB)           │
│  ├── Airflow Core                               │
│  ├── sentence-transformers (PyTorch)            │
│  ├── litellm + aider-chat                       │
│  ├── libvirt-python + kcli                      │
│  └── All Python dependencies                    │
└─────────────────────────────────────────────────┘
```

### Why This Doesn't Work for Qubinode

1. **Hypervisor host has limited resources** - VMs need the memory, not containers
2. **kcli needs direct libvirt access** - socket mounting is fragile
3. **Embedding models benefit from GPU** - containers can't easily access host GPU
4. **Ollama/Granite already runs on host** - duplicating in container is wasteful

## Decision

Implement a **hybrid architecture** where heavy AI/ML components run on the host and lightweight orchestration runs in containers.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         QUBINODE HOST                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  HOST SERVICES (installed via deploy-qubinode.sh)                        │   │
│  │  ════════════════════════════════════════════════════════════════════    │   │
│  │                                                                          │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐  │   │
│  │  │  Embedding Service  │  │  LiteLLM Proxy      │  │  Aider Agent    │  │   │
│  │  │  (Port 8891)        │  │  (Port 4000)        │  │  (On-demand)    │  │   │
│  │  │  ─────────────────  │  │  ─────────────────  │  │  ─────────────  │  │   │
│  │  │  • sentence-        │  │  • Routes to Ollama │  │  • Code gen     │  │   │
│  │  │    transformers     │  │  • Routes to OpenAI │  │  • Git aware    │  │   │
│  │  │  • GPU access       │  │  • Model selection  │  │  • Direct FS    │  │   │
│  │  │  • ~1.5GB memory    │  │  • Rate limiting    │  │                 │  │   │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────────┘  │   │
│  │                                                                          │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                       │   │
│  │  │  Ollama (Granite)   │  │  kcli               │                       │   │
│  │  │  (Port 11434)       │  │  (Direct libvirt)   │                       │   │
│  │  │  ─────────────────  │  │  ─────────────────  │                       │   │
│  │  │  • Local LLM        │  │  • VM management    │                       │   │
│  │  │  • Already running  │  │  • Network config   │                       │   │
│  │  └─────────────────────┘  └─────────────────────┘                       │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│                          localhost connections                                   │
│                                   │                                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  CONTAINERS (podman-compose, ~3GB total)                                 │   │
│  │  ════════════════════════════════════════════════════════════════════    │   │
│  │                                                                          │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐  │   │
│  │  │  PostgreSQL+PgVector│  │  Airflow Scheduler  │  │  Airflow Web    │  │   │
│  │  │  (1GB limit)        │  │  (2GB limit)        │  │  (1GB limit)    │  │   │
│  │  │  ─────────────────  │  │  ─────────────────  │  │  ─────────────  │  │   │
│  │  │  • RAG storage      │  │  • DAG orchestration│  │  • UI           │  │   │
│  │  │  • Metadata         │  │  • Task execution   │  │  • API          │  │   │
│  │  │  • Vector search    │  │  • LocalExecutor    │  │  • Auth         │  │   │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────────┘  │   │
│  │                                                                          │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  (Optional profiles) │   │
│  │  │  MCP Server         │  │  Marquez + Web      │                       │   │
│  │  │  (512MB limit)      │  │  (1GB + 256MB)      │                       │   │
│  │  │  ─────────────────  │  │  ─────────────────  │                       │   │
│  │  │  • Tool exposure    │  │  • Lineage storage  │                       │   │
│  │  │  • DAG triggers     │  │  • Visualization    │                       │   │
│  │  └─────────────────────┘  └─────────────────────┘                       │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Component Placement Decision Matrix

| Component | Container | Host | Reason |
|-----------|:---------:|:----:|--------|
| PostgreSQL + PgVector | ✅ | | Easy to manage, isolated data |
| Airflow Scheduler | ✅ | | Containerized orchestration |
| Airflow Webserver | ✅ | | Web UI isolation |
| MCP Server | ✅ | | Lightweight, needs Airflow access |
| Marquez | ✅ | | Lineage storage, optional |
| **Embedding Service** | | ✅ | Heavy (PyTorch), GPU access |
| **LiteLLM Proxy** | | ✅ | Connects to host Ollama |
| **Aider** | | ✅ | Needs git/filesystem access |
| **kcli** | | ✅ | Direct libvirt access |
| **Ollama** | | ✅ | Already running on host |

### Memory Budget

**Total host memory assumption: 32GB**

| Component | Memory Limit | Notes |
|-----------|-------------|-------|
| **Host VMs** | ~20GB | Primary workload |
| **Host Services** | ~4GB | Embedding (2GB), LiteLLM (512MB), Ollama (1.5GB) |
| **Containers** | ~6GB | Postgres (1GB), Scheduler (2GB), Web (1GB), MCP (512MB), Marquez (1.25GB) |
| **OS/Buffer** | ~2GB | System overhead |

### Container Resource Limits

Applied in `docker-compose.yml`:

```yaml
services:
  postgres:
    mem_limit: 1g
    mem_reservation: 512m
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  airflow-scheduler:
    mem_limit: 2g
    mem_reservation: 1g
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  airflow-webserver:
    mem_limit: 1g
    mem_reservation: 512m
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  airflow-mcp-server:
    mem_limit: 512m
    mem_reservation: 256m
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

### Scheduler Optimization Settings

```yaml
environment:
  # Reduce DAG parsing frequency (default 30s)
  AIRFLOW__SCHEDULER__MIN_FILE_PROCESS_INTERVAL: '60'
  # Limit parsing processes (default = CPU count)
  AIRFLOW__SCHEDULER__PARSING_PROCESSES: '2'
  # Limit DAG runs created per loop
  AIRFLOW__SCHEDULER__MAX_DAGRUNS_TO_CREATE_PER_LOOP: '10'
  # Reduce directory scan frequency
  AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL: '120'
```

### Host Services Implementation

#### 1. Embedding Service (Port 8891)

```python
# /opt/qubinode/services/embedding_service.py
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
import uvicorn

app = FastAPI()
model = SentenceTransformer('all-MiniLM-L6-v2')

@app.post("/embed")
async def embed(texts: list[str]):
    embeddings = model.encode(texts)
    return {"embeddings": embeddings.tolist()}

@app.get("/health")
async def health():
    return {"status": "healthy", "model": "all-MiniLM-L6-v2"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8891)
```

Systemd service:
```ini
# /etc/systemd/system/qubinode-embedding.service
[Unit]
Description=Qubinode Embedding Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qubinode/services
ExecStart=/usr/bin/python3 embedding_service.py
Restart=always
RestartSec=10
Environment=TRANSFORMERS_CACHE=/opt/qubinode/models

[Install]
WantedBy=multi-user.target
```

#### 2. LiteLLM Proxy (Port 4000)

```yaml
# /opt/qubinode/config/litellm_config.yaml
model_list:
  - model_name: granite-code
    litellm_params:
      model: ollama/granite-code:8b
      api_base: http://localhost:11434

  - model_name: granite-instruct
    litellm_params:
      model: ollama/granite3.1-dense:8b
      api_base: http://localhost:11434

  # Optional: External models when connected
  - model_name: claude-3-sonnet
    litellm_params:
      model: claude-3-sonnet-20240229
      api_key: os.environ/ANTHROPIC_API_KEY

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY

litellm_settings:
  drop_params: true
  set_verbose: false
```

Systemd service:
```ini
# /etc/systemd/system/qubinode-litellm.service
[Unit]
Description=Qubinode LiteLLM Proxy
After=network.target ollama.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/litellm --config /opt/qubinode/config/litellm_config.yaml --port 4000
Restart=always
RestartSec=10
Environment=LITELLM_MASTER_KEY=your-secret-key

[Install]
WantedBy=multi-user.target
```

### Slim Dockerfile

Remove heavy dependencies from container:

```dockerfile
# Dockerfile.slim - Lightweight Airflow for orchestration only
FROM docker.io/apache/airflow:2.10.4-python3.12

USER airflow

# Only install lightweight dependencies
RUN pip install --no-cache-dir \
    httpx>=0.24.0 \
    pgvector>=0.2.0 \
    psycopg2-binary>=2.9.0 \
    apache-airflow-providers-openlineage>=1.0.0 \
    openlineage-python>=1.0.0

# No sentence-transformers (host service)
# No litellm (host service)
# No aider-chat (host tool)
# No libvirt-dev (host tool)
```

**Expected image size: ~2-3GB** (down from 10.5GB)

### Communication Flow

```
┌─────────────────┐     HTTP POST /embed      ┌─────────────────┐
│  Airflow DAG    │ ───────────────────────── │ Embedding Svc   │
│  (Container)    │     [texts]               │ (Host:8891)     │
└─────────────────┘                           └─────────────────┘
                                                      │
                                              ┌───────┴───────┐
                                              │               │
┌─────────────────┐     HTTP POST /chat       ▼               │
│  MCP Server     │ ──────────────────── ┌─────────────────┐  │
│  (Container)    │     [prompt]         │ LiteLLM Proxy   │  │
└─────────────────┘                      │ (Host:4000)     │  │
                                         └────────┬────────┘  │
                                                  │           │
                                                  ▼           │
                                         ┌─────────────────┐  │
                                         │ Ollama          │  │
                                         │ (Host:11434)    │  │
                                         └─────────────────┘  │
                                                              │
┌─────────────────┐     Store vectors     ┌─────────────────┐ │
│  Embedding Svc  │ ────────────────────▶ │ PostgreSQL      │ │
│  (Host)         │                       │ + PgVector      │◀┘
└─────────────────┘                       │ (Container)     │
                                          └─────────────────┘
```

### Integration with deploy-qubinode.sh

Add optional AI services installation:

```bash
# In deploy-qubinode.sh

install_ai_services() {
    log_step "Installing AI Services for Hybrid Architecture..."

    # Create directories
    mkdir -p /opt/qubinode/{services,config,models}

    # Install Python dependencies
    pip3 install sentence-transformers fastapi uvicorn litellm

    # Copy service files
    cp airflow/host-services/embedding_service.py /opt/qubinode/services/
    cp airflow/host-services/litellm_config.yaml /opt/qubinode/config/

    # Install systemd services
    cp airflow/host-services/qubinode-embedding.service /etc/systemd/system/
    cp airflow/host-services/qubinode-litellm.service /etc/systemd/system/

    # Pre-download embedding model
    python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

    # Enable and start services
    systemctl daemon-reload
    systemctl enable --now qubinode-embedding.service
    systemctl enable --now qubinode-litellm.service

    log_success "AI Services installed and running"
}

# Call during Airflow setup if enabled
if [[ "${QUBINODE_ENABLE_AIRFLOW}" == "true" ]]; then
    install_airflow_containers

    if [[ "${QUBINODE_ENABLE_AI_SERVICES}" == "true" ]]; then
        install_ai_services
    fi
fi
```

## Consequences

### Positive

1. **Smaller container images** - ~2-3GB vs 10.5GB
2. **Faster deployments** - Less to pull/push
3. **Better resource utilization** - Host services share memory efficiently
4. **GPU access** - Embedding service can use host GPU if available
5. **Stable scheduler** - Memory limits and ulimits prevent crashes
6. **Simpler kcli integration** - No socket mounting needed
7. **Reusable services** - Embedding/LiteLLM can serve multiple tools

### Negative

1. **More components to manage** - Host services + containers
2. **Service dependencies** - Containers depend on host services
3. **Deployment complexity** - deploy-qubinode.sh must install host services
4. **Network assumptions** - Relies on localhost connectivity

### Mitigations

| Risk | Mitigation |
|------|------------|
| Service discovery | All services use well-known localhost ports |
| Service health | Systemd auto-restart + health endpoints |
| Deployment order | deploy-qubinode.sh installs host services first |
| Configuration drift | All config in version-controlled files |

## Implementation Phases

### Phase 1: Container Optimization (This ADR)
- ✅ Add memory limits to docker-compose.yml
- ✅ Add ulimits for RHEL compatibility
- ✅ Add scheduler optimization settings
- [ ] Create slim Dockerfile

### Phase 2: Host Services
- [ ] Create embedding service script
- [ ] Create LiteLLM config
- [ ] Create systemd unit files
- [ ] Update deploy-qubinode.sh

### Phase 3: Integration
- [ ] Update Airflow plugins to use host services
- [ ] Update MCP tools to use LiteLLM proxy
- [ ] Test end-to-end workflow
- [ ] Document service management

## References

- [ADR-0049: Multi-Agent LLM Memory Architecture](adr-0049-multi-agent-llm-memory-architecture.md)
- [ADR-0043: Host Network Access for VM Connectivity](adr-0043-host-network-access-for-vm-connectivity.md)
- [Airflow Scheduler Memory Issues - Stack Overflow](https://stackoverflow.com/questions/52060390/airflow-scheduler-out-of-memory-problems)
- [Airflow Memory Leak Issue #50708](https://github.com/apache/airflow/issues/50708)
- [RHEL/Rocky nofile ulimit Issue](https://github.com/apache/airflow/discussions/29731)
- [Airflow Docker Compose Documentation](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Sentence Transformers Documentation](https://www.sbert.net/)
