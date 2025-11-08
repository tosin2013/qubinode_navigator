# Multi-stage build for Qubinode AI Assistant
# Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture

# Stage 1: Build llama.cpp
FROM registry.redhat.io/ubi9/ubi:latest AS builder

# Install build dependencies
RUN dnf update -y && \
    dnf install -y --allowerasing gcc-c++ cmake make git wget curl libcurl-devel && \
    dnf clean all

# Clone and build llama.cpp with CPU optimizations (static build)
WORKDIR /build
RUN git clone https://github.com/ggerganov/llama.cpp.git && \
    cd llama.cpp && \
    cmake -B build -DGGML_NATIVE=ON -DGGML_AVX2=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF && \
    cmake --build build --config Release -j$(nproc)

# Stage 2: Runtime environment
FROM registry.redhat.io/ubi9/ubi:latest

# Install runtime dependencies including libraries needed for llama.cpp
RUN dnf update -y && \
    dnf install -y --allowerasing python3 python3-pip curl wget libgomp libstdc++ && \
    dnf clean all

# Create non-root user for security
RUN useradd -m -u 1001 qubinode-ai

# Copy llama.cpp binaries from builder stage
COPY --from=builder /build/llama.cpp/build/bin/llama-server /usr/local/bin/
COPY --from=builder /build/llama.cpp/build/bin/llama-cli /usr/local/bin/

# Set up Python virtual environment (best practice)
WORKDIR /app
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip

# Install Python dependencies in virtual environment
COPY requirements.txt .
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create directories for models and data
RUN mkdir -p /app/models /app/data /app/logs && \
    chown -R qubinode-ai:qubinode-ai /app

# Switch to non-root user
USER qubinode-ai

# Expose API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command using virtual environment
CMD ["/app/venv/bin/python", "src/main.py"]
