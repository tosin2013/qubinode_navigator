# Custom Airflow image with kcli for Qubinode Navigator
# Based on official Apache Airflow 2.10.4
# Using Python 3.12 for forward compatibility (aligned with ADR-0001 and ADR-0025)
FROM docker.io/apache/airflow:2.10.4-python3.12

# Switch to root to install system packages
USER root

# Install system dependencies for kcli and libvirt
RUN apt-get update && apt-get install -y \
    libvirt-clients \
    libvirt-dev \
    pkg-config \
    gcc \
    python3-dev \
    genisoimage \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Switch to airflow user
USER airflow

# Install kcli and ansible via pip (use latest version to avoid getiterator bug in 99.0)
RUN pip install --no-cache-dir \
    kcli \
    libvirt-python \
    paramiko \
    ansible \
    ansible-core \
    mcp>=0.9.0 \
    fastmcp>=0.2.0 \
    starlette>=0.27.0 \
    uvicorn>=0.30.0 \
    httpx>=0.24.0 \
    sse-starlette>=1.6.0

# ADR-0049: Phase 1 - Embedding and RAG dependencies
RUN pip install --no-cache-dir \
    sentence-transformers>=2.2.0 \
    pgvector>=0.2.0 \
    psycopg2-binary>=2.9.0

# ADR-0049: Phase 3 - Multi-Agent LLM Architecture dependencies
RUN pip install --no-cache-dir \
    litellm>=1.0.0 \
    aider-chat>=0.30.0 \
    pydantic>=2.0.0

# ADR-0049: Phase 4 - OpenLineage integration for data/code lineage
RUN pip install --no-cache-dir \
    apache-airflow-providers-openlineage>=1.0.0 \
    openlineage-python>=1.0.0

# Switch back to root for entrypoint
USER root

# Create directory for kcli config
RUN mkdir -p /root/.kcli && chmod 755 /root/.kcli

# Set environment variables for libvirt
ENV LIBVIRT_DEFAULT_URI=qemu:///system

# Switch back to airflow user (will be overridden by docker-compose user setting)
USER airflow
