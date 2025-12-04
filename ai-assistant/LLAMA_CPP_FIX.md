# llama.cpp Server Fix for AI Assistant

## Problem

The AI Assistant container was failing to start with the error:

```
FileNotFoundError: [Errno 2] No such file or directory: '/app/llama.cpp/server'
```

## Root Cause

The running container was built from an older version of the code that expected the llama.cpp server at `/app/llama.cpp/server`, but the current Dockerfile installs it to `/usr/local/bin/llama-server`.

## Solution Applied

### 1. Dockerfile Updates

- **Added backward compatibility symlinks** in the Dockerfile:
  ```dockerfile
  # Create compatibility symlinks for backward compatibility
  RUN mkdir -p /app/llama.cpp && \
      ln -s /usr/local/bin/llama-server /app/llama.cpp/server && \
      ln -s /usr/local/bin/llama-cli /app/llama.cpp/cli
  ```

### 2. Enhanced model_manager.py

- **Added robust path detection** with multiple fallback locations:
  - `/usr/local/bin/llama-server` (primary)
  - `/app/llama.cpp/server` (backward compatibility)
  - `llama-server` (system PATH)
- **Improved error handling** with detailed error messages
- **Added logging** to show which executable path is being used

### 3. Build and Verification Scripts

- **`rebuild-container.sh`**: Automated container rebuild script
- **`verify-llama-install.sh`**: Verification script to check llama.cpp installation

## How to Apply the Fix

### Option 1: Rebuild Container (Recommended)

```bash
cd /root/qubinode_navigator/ai-assistant
./rebuild-container.sh
```

### Option 2: Manual Steps

```bash
# Stop existing container
docker stop qubinode-ai-assistant
docker rm qubinode-ai-assistant

# Remove old image
docker rmi qubinode-ai-assistant:latest

# Rebuild with fixes
docker build -t qubinode-ai-assistant:latest .

# Start new container
docker run -d --name qubinode-ai-assistant -p 8080:8080 qubinode-ai-assistant:latest
```

## Verification

Run the verification script to ensure the fix worked:

```bash
./verify-llama-install.sh
```

Expected output should show:

- ✅ `/usr/local/bin/llama-server` found
- ✅ `/app/llama.cpp/server` symlink found
- ✅ Executable works

## Files Modified

- `Dockerfile`: Added symlinks for backward compatibility
- `src/model_manager.py`: Enhanced path detection and error handling
- `rebuild-container.sh`: New build script
- `verify-llama-install.sh`: New verification script
- `LLAMA_CPP_FIX.md`: This documentation

## Prevention

This fix ensures that both old and new code paths work, preventing similar issues in the future. The enhanced path detection in `model_manager.py` will automatically find the correct executable location.
