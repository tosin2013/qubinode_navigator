# Custom Airflow image with kcli for Qubinode Navigator
# Based on official Apache Airflow 2.10.4
# Using Python 3.11 for kcli compatibility (kcli 99.0 has issues with Python 3.12)
FROM docker.io/apache/airflow:2.10.4-python3.11

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

# Install kcli via pip (use latest version to avoid getiterator bug in 99.0)
RUN pip install --no-cache-dir \
    kcli \
    libvirt-python \
    paramiko \
    mcp>=0.9.0 \
    fastmcp>=0.2.0 \
    starlette>=0.27.0 \
    uvicorn>=0.30.0 \
    httpx>=0.24.0 \
    sse-starlette>=1.6.0

# Switch back to root for entrypoint
USER root

# Create directory for kcli config
RUN mkdir -p /root/.kcli && chmod 755 /root/.kcli

# Set environment variables for libvirt
ENV LIBVIRT_DEFAULT_URI=qemu:///system

# Switch back to airflow user (will be overridden by docker-compose user setting)
USER airflow
