# Airflow AI Assistant Chat Integration Troubleshooting

## Common Issues

### Issue: 400 Bad Request or Timeout Errors in AI Chat

**Symptoms:**
- Browser console shows: `Failed to load resource: the server responded with a status of 400 (BAD REQUEST)`
- Chat requests timeout
- Loading spinner never completes

**Root Cause:**
The AI Assistant's `/chat` endpoint uses LLM inference which can take 30-90 seconds to respond, especially on the first request or with complex queries.

**Solution Applied:**
1. **Backend timeout increased to 90 seconds** in `ai_chat_plugin.py`
2. **Frontend shows informative loading message**: "🤔 Thinking... (this may take 30-60 seconds for AI inference)"
3. **Network connectivity verified**: All containers on `airflow_default` network

**Verification:**
```bash
# Test AI Assistant from Airflow container
podman exec airflow_airflow-webserver_1 curl http://qubinode-ai-assistant:8080/health

# Check network connectivity
podman network inspect airflow_default --format '{{range .Containers}}{{.Name}} {{end}}'

# Should show: airflow_postgres_1 airflow_airflow-scheduler_1 qubinode-ai-assistant airflow_airflow-webserver_1
```

### Issue: Containers Not on Same Network

**Symptoms:**
- Cannot resolve `qubinode-ai-assistant` hostname
- Connection refused errors

**Solution:**
```bash
# Connect AI Assistant to Airflow network
podman network connect airflow_default qubinode-ai-assistant

# Verify
podman network inspect airflow_default
```

### Issue: AI Assistant Not Responding

**Symptoms:**
- Health endpoint returns 503 Service Unavailable
- `/chat` endpoint times out even with extended timeout

**Diagnosis:**
```bash
# Check AI Assistant logs
podman logs qubinode-ai-assistant --tail 50

# Check AI Assistant health
curl http://localhost:8080/health | jq

# Common issues shown in health:
# - "RAG documents not loaded" (warning, not critical)
# - LLM server not responding
# - Model not loaded
```

**Solution:**
```bash
# Restart AI Assistant
podman restart qubinode-ai-assistant

# Wait for it to be ready (can take 2-3 minutes)
for i in {1..60}; do
  curl -s http://localhost:8080/health && break
  sleep 3
done
```

### Issue: Airflow Webserver Not Loading Chat Plugin

**Symptoms:**
- `/ai-assistant` endpoint returns 404
- Menu item not showing in Airflow UI

**Solution:**
```bash
# Restart webserver to reload plugins
cd /root/qubinode_navigator/airflow
podman-compose restart airflow-webserver

# Wait for webserver to be ready
sleep 30
curl http://localhost:8888/health
```

## Performance Tips

### Faster AI Responses

1. **Keep AI Assistant Running**: First request after restart is slowest (model loading)
2. **Simple Queries**: Short, specific questions get faster responses
3. **Context Matters**: Provide relevant context to avoid long inference times

### Resource Usage

AI Assistant is CPU-intensive during inference:
```bash
# Monitor resource usage
podman stats qubinode-ai-assistant

# Expected during chat:
# CPU: 50-100% (normal for LLM inference)
# Memory: 8-10% (on 64GB system)
```

## Network Architecture

```
┌─────────────────────────────────────────────┐
│          Podman Network: airflow_default    │
│                                             │
│  ┌──────────────────┐   ┌────────────────┐ │
│  │  AI Assistant    │   │  Airflow       │ │
│  │  qubinode-ai-    │◄──┤  Webserver     │ │
│  │  assistant:8080  │   │  :8888         │ │
│  └──────────────────┘   └────────────────┘ │
│           ▲                                 │
│           │                                 │
│  ┌────────┴─────────┐   ┌────────────────┐ │
│  │  Airflow         │   │  PostgreSQL    │ │
│  │  Scheduler       │   │  :5432         │ │
│  └──────────────────┘   └────────────────┘ │
└─────────────────────────────────────────────┘
          │
          │ Port Mappings
          ▼
┌─────────────────────────────────────────────┐
│              Host Network                    │
│  localhost:8080  → AI Assistant              │
│  localhost:8888  → Airflow UI                │
│  localhost:5432  → PostgreSQL                │
└─────────────────────────────────────────────┘
```

## Logs and Debugging

### View Logs
```bash
# Airflow webserver logs
podman logs airflow_airflow-webserver_1 --tail 100

# AI Assistant logs
podman logs qubinode-ai-assistant --tail 100

# All Airflow services
cd /root/qubinode_navigator/airflow
podman-compose logs -f
```

### Check Service Health
```bash
# Use the status command
./deploy-airflow.sh status

# Or manually check each service
curl http://localhost:8888/health  # Airflow
curl http://localhost:8080/health  # AI Assistant
```

### Test Chat API Directly
```bash
# From host
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}' \
  --max-time 60

# From Airflow container
podman exec airflow_airflow-webserver_1 \
  curl -X POST http://qubinode-ai-assistant:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}' \
  --max-time 60
```

## Quick Fixes

### Complete Restart
```bash
cd /root/qubinode_navigator/airflow
podman-compose down
podman-compose up -d

# Reconnect AI Assistant to network
podman network connect airflow_default qubinode-ai-assistant
```

### Plugin Issues
```bash
# Rebuild image with latest plugin changes
cd /root/qubinode_navigator/airflow
podman build -t qubinode-airflow:2.10.4-python3.12 -f Dockerfile .
podman-compose up -d --force-recreate
```

## Support

For additional help:
1. Check Airflow logs: `podman logs airflow_airflow-webserver_1`
2. Check AI Assistant logs: `podman logs qubinode-ai-assistant`
3. Verify network: `podman network inspect airflow_default`
4. Test connectivity: Use curl commands above
5. Review: `airflow/README.md` and `airflow/TOOLS-AVAILABLE.md`
