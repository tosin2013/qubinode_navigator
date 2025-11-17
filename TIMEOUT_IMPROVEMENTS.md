# GitHub Actions Timeout Improvements

## Problem
The GitHub Actions CI/CD pipeline was using insufficient timeouts for the AI Assistant health checks, causing failures during model download and startup phases.

## Changes Made

### 1. Docker Health Check Timeouts
**Before:**
```yaml
--health-timeout: '5s'
--health-interval: '10s'  
--health-retries: '3'
```

**After:**
```yaml
--health-timeout: '30s'
--health-interval: '30s'
--health-retries: '5'
```

### 2. Curl Command Timeouts
**Before:**
```bash
curl -f http://localhost:8080/health
```

**After:**
```bash
curl -f --max-time 30 --connect-timeout 10 http://localhost:8080/health
```

### 3. Chat Endpoint Timeout
**Before:**
```bash
curl -f -X POST http://localhost:8080/chat
```

**After:**
```bash
curl -f --max-time 60 --connect-timeout 10 -X POST http://localhost:8080/chat
```

## Rationale

### AI Assistant Startup Process:
1. **Model Download**: 30-60 seconds (depending on network)
2. **llama.cpp Server Start**: 10-15 seconds
3. **Service Initialization**: 5-10 seconds
4. **Total**: 45-85 seconds typical startup time

### Timeout Strategy:
- **Health Check Timeout**: 30s (allows for individual request processing)
- **Health Check Interval**: 30s (reduces log noise, allows startup time)
- **Health Check Retries**: 5 (provides 2.5 minutes total wait time)
- **Curl Max Time**: 30s for health, 60s for chat (chat may involve AI processing)
- **Connect Timeout**: 10s (reasonable for container networking)

## Expected Results
- ✅ Reduced false failures due to startup timing
- ✅ Better handling of model download delays
- ✅ More reliable integration tests
- ✅ Cleaner CI/CD pipeline logs

## Files Modified
- `.github/workflows/ai-assistant-ci.yml`: Updated all curl timeouts and Docker health checks
