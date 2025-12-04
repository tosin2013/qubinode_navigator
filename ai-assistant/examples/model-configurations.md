# AI Assistant Model Configuration Examples

The Qubinode AI Assistant supports multiple models and hardware configurations through environment variables.

## Quick Start Examples

### CPU-Only (Default - Granite 4.0 Micro)

```bash
podman run -d --name qubinode-ai-assistant \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data:Z \
  quay.io/qubinode/ai-assistant:latest
```

### GPU-Accelerated (Llama3 8B)

```bash
podman run -d --name qubinode-ai-assistant \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data:Z \
  --device nvidia.com/gpu=all \
  -e AI_MODEL_TYPE=llama3-8b \
  -e AI_USE_GPU=true \
  -e AI_GPU_LAYERS=32 \
  quay.io/qubinode/ai-assistant:latest
```

### Fast GPU Model (Phi-3 Mini)

```bash
podman run -d --name qubinode-ai-assistant \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data:Z \
  --device nvidia.com/gpu=all \
  -e AI_MODEL_TYPE=phi3-mini \
  -e AI_USE_GPU=true \
  -e AI_GPU_LAYERS=32 \
  quay.io/qubinode/ai-assistant:latest
```

### OpenAI GPT-4 (Cloud)

```bash
podman run -d --name qubinode-ai-assistant \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data:Z \
  -e AI_MODEL_TYPE=openai-gpt4 \
  -e OPENAI_API_KEY=your_api_key_here \
  quay.io/qubinode/ai-assistant:latest
```

### Local Ollama Integration

```bash
# First start Ollama with Llama3
ollama run llama3

# Then start AI Assistant
podman run -d --name qubinode-ai-assistant \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data:Z \
  -e AI_MODEL_TYPE=ollama-local \
  --network host \
  quay.io/qubinode/ai-assistant:latest
```

## Environment Variables

| Variable            | Default             | Description                        |
| ------------------- | ------------------- | ---------------------------------- |
| `AI_MODEL_TYPE`     | `granite-4.0-micro` | Model preset to use                |
| `AI_USE_GPU`        | `false`             | Enable GPU acceleration            |
| `AI_GPU_LAYERS`     | `0`                 | Number of layers to offload to GPU |
| `AI_THREADS`        | `4`                 | CPU threads for inference          |
| `AI_CONTEXT_LENGTH` | `4096`              | Model context window size          |
| `AI_TEMPERATURE`    | `0.7`               | Sampling temperature               |
| `AI_MAX_TOKENS`     | `512`               | Maximum response tokens            |
| `AI_MODEL_PATH`     | (varies)            | Custom model file path             |
| `AI_MODEL_URL`      | (varies)            | Custom model download URL          |

## Hardware Recommendations

### CPU-Only Systems

- **2-4GB RAM**: `granite-4.0-micro` (default)
- **8GB+ RAM**: `granite-7b` for better responses

### GPU Systems

- **4GB+ VRAM**: `phi3-mini` for fast inference
- **6GB+ VRAM**: `llama3-8b` for best quality
- **8GB+ VRAM**: `granite-7b` with GPU acceleration

### Cloud/API

- **Production**: `openai-gpt4` for best quality
- **Cost-effective**: `anthropic-claude`
- **Enterprise**: `azure-openai`

## Custom Model Configuration

### Using Your Own Model

```bash
podman run -d --name qubinode-ai-assistant \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data:Z \
  -v /path/to/your/model.gguf:/app/models/custom.gguf:Z \
  -e AI_MODEL_TYPE=custom \
  -e AI_MODEL_PATH=/app/models/custom.gguf \
  quay.io/qubinode/ai-assistant:latest
```

### Performance Tuning

```bash
# High-performance CPU setup
podman run -d --name qubinode-ai-assistant \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data:Z \
  -e AI_MODEL_TYPE=granite-7b \
  -e AI_THREADS=8 \
  -e AI_CONTEXT_LENGTH=8192 \
  quay.io/qubinode/ai-assistant:latest

# Memory-constrained setup
podman run -d --name qubinode-ai-assistant \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data:Z \
  -e AI_MODEL_TYPE=granite-4.0-micro \
  -e AI_THREADS=2 \
  -e AI_CONTEXT_LENGTH=2048 \
  -e AI_MAX_TOKENS=256 \
  quay.io/qubinode/ai-assistant:latest
```

## Model Information API

Check current model configuration:

```bash
curl http://localhost:8080/model/info
```

Get hardware recommendations:

```bash
curl http://localhost:8080/model/hardware
```

## Troubleshooting

### GPU Not Detected

```bash
# Check GPU availability
podman run --rm --device nvidia.com/gpu=all nvidia/cuda:11.8-base nvidia-smi

# Verify GPU layers are being used
podman logs qubinode-ai-assistant | grep "GPU acceleration"
```

### Out of Memory

```bash
# Reduce context length and threads
-e AI_CONTEXT_LENGTH=2048 \
-e AI_THREADS=2 \
-e AI_MAX_TOKENS=256
```

### Slow Responses

```bash
# Use smaller model or enable GPU
-e AI_MODEL_TYPE=granite-4.0-micro  # Smaller model
# OR
-e AI_USE_GPU=true -e AI_GPU_LAYERS=32  # GPU acceleration
```
