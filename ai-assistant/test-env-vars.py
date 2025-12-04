#!/usr/bin/env python3
"""
Test script to verify environment variable substitution
"""

import os
import sys
import asyncio

sys.path.append("src")

from src.config_manager import ConfigManager
from src.model_manager import ModelManager


async def test_env_substitution():
    """Test environment variable substitution"""

    print("=== Testing Environment Variable Substitution ===")

    # Test without environment variables set
    print("\n1. Testing without environment variables:")
    config_manager = ConfigManager("config/ai_config.yaml")
    await config_manager.load_config()

    print("Raw config ai_service section:")
    ai_service_config = config_manager.config.get("ai_service", {})
    for key, value in ai_service_config.items():
        if isinstance(value, str) and len(str(value)) < 100:
            print(f"  {key}: {value} (type: {type(value)})")

    # Test ModelManager initialization
    print("\n2. Testing ModelManager initialization:")
    try:
        model_manager = ModelManager(config_manager.config)
        print(f"  Model type: {model_manager.model_type}")
        print(f"  GPU layers: {model_manager.gpu_layers} (type: {type(model_manager.gpu_layers)})")
        print(f"  Use GPU: {model_manager.use_gpu}")
        print(f"  Threads: {model_manager.threads}")
        print("  ✓ ModelManager initialized successfully")
    except Exception as e:
        print(f"  ✗ ModelManager failed: {e}")
        return False

    # Test with environment variables set
    print("\n3. Testing with environment variables set:")
    os.environ["AI_GPU_LAYERS"] = "16"
    os.environ["AI_THREADS"] = "8"
    os.environ["AI_MODEL_TYPE"] = "granite-7b"

    config_manager2 = ConfigManager("config/ai_config.yaml")
    await config_manager2.load_config()

    try:
        model_manager2 = ModelManager(config_manager2.config)
        print(f"  Model type: {model_manager2.model_type}")
        print(f"  GPU layers: {model_manager2.gpu_layers} (type: {type(model_manager2.gpu_layers)})")
        print(f"  Use GPU: {model_manager2.use_gpu}")
        print(f"  Threads: {model_manager2.threads}")
        print("  ✓ ModelManager with env vars initialized successfully")
    except Exception as e:
        print(f"  ✗ ModelManager with env vars failed: {e}")
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_env_substitution())
    sys.exit(0 if success else 1)
