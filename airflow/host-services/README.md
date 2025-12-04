# Qubinode Host Services

## Overview

These services run on the **host** (not in containers) as part of the hybrid architecture defined in ADR-0050. Running on the host provides:

- **Smaller container images** (~2-3GB vs 10.5GB)
- **GPU access** for embedding models
- **Direct filesystem access** for tools like Aider
- **Shared services** across multiple tools

## Services

### 1. Embedding Service (Port 8891)

Vector embedding service using sentence-transformers for RAG.

```bash
# Install dependencies
pip3 install sentence-transformers fastapi uvicorn pydantic

# Pre-download model
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Install systemd service
sudo cp qubinode-embedding.service /etc/systemd/system/
sudo mkdir -p /opt/qubinode/{services,models}
sudo cp embedding_service.py /opt/qubinode/services/

# Start service
sudo systemctl daemon-reload
sudo systemctl enable --now qubinode-embedding.service

# Check status
sudo systemctl status qubinode-embedding.service
curl http://localhost:8891/health
```

**API Endpoints:**

| Endpoint  | Method | Description                   |
| --------- | ------ | ----------------------------- |
| `/embed`  | POST   | Generate embeddings for texts |
| `/health` | GET    | Health check                  |
| `/`       | GET    | Service info                  |

**Example:**

```bash
curl -X POST http://localhost:8891/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello world", "How are you?"]}'
```

### 2. LiteLLM Proxy (Port 4000)

Multi-model LLM router that connects to:

- Local Ollama (Granite models) - works offline
- External APIs (OpenAI, Anthropic) - requires API keys

```bash
# Install LiteLLM
pip3 install litellm

# Install config and service
sudo mkdir -p /opt/qubinode/config /etc/qubinode
sudo cp litellm_config.yaml /opt/qubinode/config/
sudo cp qubinode-litellm.service /etc/systemd/system/

# Configure API keys (optional, for external models)
sudo cat > /etc/qubinode/litellm.env << 'EOF'
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
LITELLM_MASTER_KEY=$(openssl rand -hex 32)
EOF
sudo chmod 600 /etc/qubinode/litellm.env

# Start service
sudo systemctl daemon-reload
sudo systemctl enable --now qubinode-litellm.service

# Check status
sudo systemctl status qubinode-litellm.service
curl http://localhost:4000/health
```

**Available Models:**

| Model Name         | Backend   | Notes             |
| ------------------ | --------- | ----------------- |
| `granite-code`     | Ollama    | Code generation   |
| `granite-instruct` | Ollama    | General assistant |
| `granite-3b`       | Ollama    | Lightweight tasks |
| `local`            | Ollama    | Fallback          |
| `claude-sonnet`    | Anthropic | Requires API key  |
| `gpt-4`            | OpenAI    | Requires API key  |

**Example:**

```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-master-key" \
  -d '{
    "model": "granite-instruct",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Quick Install (All Services)

```bash
# Run from qubinode_navigator/airflow/host-services directory
./install-host-services.sh
```

Or via deploy-qubinode.sh:

```bash
QUBINODE_ENABLE_AIRFLOW=true QUBINODE_ENABLE_AI_SERVICES=true ./deploy-qubinode.sh
```

## Service Management

```bash
# View logs
journalctl -u qubinode-embedding.service -f
journalctl -u qubinode-litellm.service -f

# Restart services
sudo systemctl restart qubinode-embedding.service
sudo systemctl restart qubinode-litellm.service

# Stop services
sudo systemctl stop qubinode-embedding.service
sudo systemctl stop qubinode-litellm.service

# Disable services
sudo systemctl disable qubinode-embedding.service
sudo systemctl disable qubinode-litellm.service
```

## Integration with Airflow

The containerized Airflow services connect to these host services via localhost:

```yaml
# In docker-compose.yml
environment:
  QUBINODE_EMBEDDING_SERVICE_URL: 'http://localhost:8891'
  QUBINODE_LITELLM_PROXY_URL: 'http://localhost:4000'
```

DAGs and plugins can use these services:

```python
import httpx

# Generate embeddings
async def get_embeddings(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8891/embed",
            json={"texts": texts}
        )
        return response.json()["embeddings"]

# Call LLM
async def chat(prompt: str, model: str = "granite-instruct") -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:4000/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            },
            headers={"Authorization": f"Bearer {LITELLM_KEY}"}
        )
        return response.json()["choices"][0]["message"]["content"]
```

## Troubleshooting

### Embedding service won't start

```bash
# Check logs
journalctl -u qubinode-embedding.service -n 50

# Common issues:
# - Missing sentence-transformers: pip3 install sentence-transformers
# - Model download failed: Check /opt/qubinode/models permissions
# - Port in use: netstat -tlnp | grep 8891
```

### LiteLLM can't connect to Ollama

```bash
# Check Ollama is running
systemctl status ollama.service
curl http://localhost:11434/api/tags

# Check model is available
ollama list
ollama pull granite3.1-dense:8b
```

### Memory issues

```bash
# Check memory usage
systemctl status qubinode-embedding.service
systemctl status qubinode-litellm.service

# Adjust limits in service files
# MemoryMax=3G -> MemoryMax=2G
```

## References

- [ADR-0050: Hybrid Host-Container Architecture](../../docs/adrs/adr-0050-hybrid-host-container-architecture.md)
- [ADR-0049: Multi-Agent LLM Memory Architecture](../../docs/adrs/adr-0049-multi-agent-llm-memory-architecture.md)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Sentence Transformers Documentation](https://www.sbert.net/)
