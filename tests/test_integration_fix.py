#!/usr/bin/env python3
"""
Quick test to verify the integration test fix
"""

import subprocess
import time
import requests
import sys


def test_integration_fix():
    """Test the integration fix"""
    print("=== Testing Integration Fix ===")

    # Check if integration image exists
    print("1. Checking integration image...")
    result = subprocess.run(
        [
            "docker",
            "images",
            "-q",
            "quay.io/takinosh/qubinode-ai-assistant:integration",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        print("❌ Integration image not found!")
        return False
    print("✅ Integration image exists")

    # Test if current container is healthy
    print("2. Testing current container health...")
    try:
        response = requests.get("http://localhost:8080/health", timeout=10)
        if response.status_code == 200:
            print("✅ Current container is healthy")
            health_data = response.json()
            print(f"Health status: {health_data}")
        else:
            print(f"⚠️ Current container returned status {response.status_code}")
    except Exception as e:
        print(f"⚠️ Current container health check failed: {e}")

    # Test a quick integration scenario
    print("3. Testing quick integration scenario...")
    container_name = "ai-quick-test"

    try:
        # Clean up
        subprocess.run(
            ["docker", "stop", container_name], check=False, capture_output=True
        )
        subprocess.run(
            ["docker", "rm", container_name], check=False, capture_output=True
        )

        # Start test container
        print("Starting test container...")
        start_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            "8081:8080",
            "-e",
            "AI_MODEL_TYPE=granite-4.0-micro",
            "-e",
            "AI_LOG_LEVEL=info",
            "quay.io/takinosh/qubinode-ai-assistant:integration",
        ]

        result = subprocess.run(start_cmd, check=True, capture_output=True, text=True)
        print(f"✅ Test container started: {result.stdout.strip()}")

        # Wait for startup (shorter timeout for quick test)
        print("Waiting for test container startup...")
        for i in range(24):  # 2 minutes max
            time.sleep(5)
            try:
                response = requests.get("http://localhost:8081/health", timeout=5)
                if response.status_code == 200:
                    print(f"✅ Test container ready after {(i+1)*5} seconds")
                    return True
                elif response.status_code == 503:
                    print(f"Service starting up... attempt {i+1}")
            except requests.exceptions.RequestException:
                if i % 6 == 0:  # Every 30 seconds
                    print(f"Still waiting... {(i+1)*5} seconds")

        print("❌ Test container failed to start in time")
        # Show logs
        subprocess.run(["docker", "logs", "--tail", "20", container_name], check=False)
        return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        # Cleanup
        subprocess.run(
            ["docker", "stop", container_name], check=False, capture_output=True
        )
        subprocess.run(
            ["docker", "rm", container_name], check=False, capture_output=True
        )


def main():
    """Main entry point"""
    if test_integration_fix():
        print("🎉 Integration fix test passed!")
        return 0
    else:
        print("❌ Integration fix test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
