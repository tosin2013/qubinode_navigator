# Slim Airflow image for Qubinode Navigator
# ADR-0050: Hybrid Host-Container Architecture
# Heavy AI/ML components (sentence-transformers, litellm, aider) run on host
# This container focuses on orchestration only
#
# Based on official Apache Airflow 2.10.4
# Using Python 3.12 for forward compatibility (aligned with ADR-0001 and ADR-0025)
FROM docker.io/apache/airflow:2.10.4-python3.12

# Switch to airflow user (no root needed for slim image)
USER airflow

# Core dependencies for Qubinode integration
# These are lightweight and needed for DAG execution
RUN pip install --no-cache-dir \
    # HTTP client for calling host services
    httpx>=0.24.0 \
    # PostgreSQL vector extension client
    pgvector>=0.2.0 \
    psycopg2-binary>=2.9.0 \
    # Pydantic for data validation
    pydantic>=2.0.0

# ADR-0049 Phase 4: OpenLineage integration for data/code lineage
RUN pip install --no-cache-dir \
    apache-airflow-providers-openlineage>=1.0.0 \
    openlineage-python>=1.0.0

# ============================================================================
# REMOVED FROM CONTAINER (now run on host per ADR-0050):
# ============================================================================
# - sentence-transformers (1.5GB with PyTorch) -> Host embedding service :8891
# - litellm (500MB+) -> Host LiteLLM proxy :4000
# - aider-chat -> Host tool, direct filesystem access
# - kcli, libvirt-python -> Host tool, direct libvirt access
# - libvirt-dev, gcc, python3-dev -> Not needed without libvirt-python
# ============================================================================

# Environment variables for host service integration
ENV QUBINODE_EMBEDDING_SERVICE_URL=http://localhost:8891 \
    QUBINODE_LITELLM_PROXY_URL=http://localhost:4000 \
    QUBINODE_OLLAMA_URL=http://localhost:11434

# Stay as airflow user
USER airflow
