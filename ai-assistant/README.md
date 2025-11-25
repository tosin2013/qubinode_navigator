# Qubinode AI Assistant

CPU-based AI deployment assistant for infrastructure automation, based on ADR-0027.

## Overview

The Qubinode AI Assistant provides interactive guidance and troubleshooting for infrastructure deployment using:

- **llama.cpp** for high-performance CPU inference
- **IBM Granite-4.0-Micro** (3B parameters) for technical assistance
- **FastAPI** for REST API interface
- **Container-first deployment** with Podman

## Features

- 🤖 **Interactive AI Assistance**: Chat-based guidance for deployment issues
- 🔍 **System Diagnostics**: Automated analysis of system health and configuration
- 📊 **Real-time Monitoring**: Integration with Ansible and system services
- 🛡️ **Local Processing**: All AI inference runs locally without external dependencies
- 🐳 **Containerized**: Easy deployment with Podman/Docker

## Quick Start

### 1. Build the Container

```bash
cd ai-assistant
./scripts/build.sh
```

### 2. Run the Service

```bash
podman run -d \
  --name qubinode-ai \
  -p 8080:8080 \
  -v ./config:/app/config:ro \
  -v ./models:/app/models \
  localhost/qubinode-ai-assistant:latest
```

### 3. Test the Service

```bash
# Check health
curl http://localhost:8080/health

# Use CLI interface
./scripts/qubinode-ai --health
./scripts/qubinode-ai --message "How do I configure KVM on RHEL 9?"
```

### 4. Interactive Mode

```bash
./scripts/qubinode-ai
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Chat Interface
```bash
POST /chat
{
  "message": "How do I troubleshoot libvirt networking?",
  "context": {},
  "max_tokens": 512,
  "temperature": 0.7
}
```

### System Diagnostics
```bash
POST /diagnostics
{
  "system_info": {}
}
```

### Configuration
```bash
GET /config
```

## MCP Tools for LLM Integration

The AI Assistant exposes **4 powerful tools** via Model Context Protocol (MCP) for LLMs to interact with Qubinode:

### 1. **ask_qubinode** (NEW - Learning Tool)
Perfect for LLMs to learn how to use Qubinode by asking questions in natural language.

```python
# Example usage in MCP
await mcp_client.call_tool("ask_qubinode", {
    "question": "How do I create a custom plugin?",
    "topic": "plugins",
    "skill_level": "intermediate"
})
```

**Features:**
- Combines documentation search with AI-powered guidance
- Supports topics: `plugins`, `deployment`, `mcp`, `airflow`, `configuration`
- Skill levels: `beginner`, `intermediate`, `advanced`
- Includes practical examples and next steps
- Falls back to documentation if AI service is unavailable

### 2. **query_documents**
Search the RAG document store for specific information.

```python
await mcp_client.call_tool("query_documents", {
    "query": "How to configure kcli",
    "max_results": 5
})
```

### 3. **chat_with_context**
Send messages with context for intelligent infrastructure-focused responses.

```python
await mcp_client.call_tool("chat_with_context", {
    "message": "What's the best practice for VM naming?",
    "context": {
        "task": "deploying VM",
        "environment": "production",
        "user_role": "admin"
    }
})
```

### 4. **get_project_status**
Get current project health and metrics.

```python
await mcp_client.call_tool("get_project_status", {})
```

## Configuration

The AI assistant can be configured via:

1. **Configuration file**: `config/ai_config.yaml`
2. **Environment variables**: `AI_*` prefixed variables
3. **Runtime parameters**: API request parameters

### Key Configuration Options

```yaml
ai:
  model_name: "granite-4.0-micro"
  max_tokens: 512
  temperature: 0.7
  threads: 4

server:
  host: "0.0.0.0"
  port: 8080
  log_level: "INFO"

features:
  diagnostics: true
  system_monitoring: true
  rag_enabled: true

qubinode:
  integration_enabled: true
  plugin_framework_path: "/opt/qubinode/core"
```

### Environment Variables

- `AI_HOST`: Server host (default: 0.0.0.0)
- `AI_PORT`: Server port (default: 8080)
- `AI_LOG_LEVEL`: Logging level (default: INFO)
- `AI_MODEL_PATH`: Path to AI model file
- `AI_MAX_TOKENS`: Maximum tokens per response
- `AI_TEMPERATURE`: AI response creativity (0.0-2.0)
- `AI_THREADS`: Number of CPU threads for inference

## Model Management

### Granite-4.0-Micro Model

The service automatically downloads the IBM Granite-4.0-Micro model in GGUF format:

- **Size**: ~2-3GB
- **Parameters**: 3B
- **Format**: GGUF (quantized)
- **Performance**: Optimized for CPU inference

### Custom Models

To use a different model:

1. Place the GGUF model file in `/app/models/`
2. Update `ai.model_path` in configuration
3. Restart the service

## Integration with Qubinode Navigator

### Plugin Framework Integration

The AI assistant integrates with the Qubinode plugin framework:

```python
# Example plugin integration
from qubinode.core import PluginManager
from ai_assistant import AIService

plugin_manager = PluginManager()
ai_service = AIService()

# AI-enhanced plugin execution
result = await plugin_manager.execute_with_ai_guidance(
    plugin_name="rhel10_setup",
    ai_service=ai_service
)
```

### Ansible Callback Integration

```yaml
# ansible.cfg
[defaults]
callbacks_enabled = qubinode_ai_callback

[callback_qubinode_ai]
ai_service_url = http://localhost:8080
enable_real_time_guidance = true
```

## Development

### Project Structure

```
ai-assistant/
├── src/
│   ├── main.py              # FastAPI application
│   ├── ai_service.py        # AI inference service
│   ├── config_manager.py    # Configuration management
│   └── health_monitor.py    # Health monitoring
├── config/
│   └── ai_config.yaml       # Default configuration
├── scripts/
│   ├── build.sh            # Container build script
│   └── qubinode-ai         # CLI interface
├── models/                  # AI model storage
├── Dockerfile              # Container definition
└── requirements.txt        # Python dependencies
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
cd src
python main.py

# Test CLI
../scripts/qubinode-ai --health
```

### Testing

```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/integration/

# Load testing
pytest tests/load/
```

## Hardware Requirements

### Minimum Requirements
- **CPU**: x86_64 with AVX2 support
- **Memory**: 6GB RAM (4GB for model + 2GB for system)
- **Storage**: 5GB free space
- **Network**: HTTP access for model download

### Recommended Requirements
- **CPU**: 8+ cores with AVX2/AVX-512
- **Memory**: 8GB+ RAM
- **Storage**: 10GB+ SSD storage
- **Network**: Low-latency network for API access

## Performance Tuning

### CPU Optimization

```yaml
ai:
  threads: 8  # Match CPU core count
  context_size: 2048  # Adjust based on memory
```

### Memory Optimization

```bash
# Limit container memory
podman run --memory=6g qubinode-ai-assistant
```

### Model Quantization

Use different quantization levels for performance/quality trade-offs:

- `Q4_0`: Fastest, lower quality
- `Q5_1`: Balanced performance/quality
- `Q8_0`: Highest quality, slower

## Troubleshooting

### Common Issues

1. **Model Download Fails**
   ```bash
   # Manual download
   wget -O models/granite-4.0-micro.gguf [MODEL_URL]
   ```

2. **High Memory Usage**
   ```bash
   # Reduce context size
   export AI_CONTEXT_SIZE=1024
   ```

3. **Slow Response Times**
   ```bash
   # Increase thread count
   export AI_THREADS=8
   ```

4. **Container Won't Start**
   ```bash
   # Check logs
   podman logs qubinode-ai
   
   # Check health
   curl http://localhost:8080/health
   ```

### Debug Mode

```bash
# Enable debug logging
export AI_LOG_LEVEL=DEBUG

# Run with verbose output
podman run --rm -it qubinode-ai-assistant
```

## Security Considerations

- **Local Processing**: All AI inference runs locally
- **No External APIs**: No data sent to external services
- **Container Isolation**: Runs in isolated container environment
- **Non-root User**: Container runs as non-privileged user
- **Resource Limits**: CPU and memory limits enforced

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is part of the Qubinode Navigator and follows the same licensing terms.

## Support

For support and questions:

- **Issues**: GitHub Issues
- **Documentation**: `/docs` directory
- **Community**: Qubinode Navigator community channels
