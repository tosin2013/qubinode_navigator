#!/usr/bin/env python3
"""
Local Integration Test Script
Test the AI Assistant container integration locally before CI/CD
"""

import subprocess
import time
import requests
import json
import sys
from pathlib import Path

def run_command(cmd, check=True, capture_output=True, text=True):
    """Run command with error handling"""
    try:
        result = subprocess.run(cmd, check=check, capture_output=capture_output, text=text)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}")
        print(f"Error: {e}")
        if capture_output:
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
        return e

def test_container_integration():
    """Test AI Assistant container integration"""
    container_name = 'ai-local-test'
    image_name = 'quay.io/takinosh/qubinode-ai-assistant:test'
    
    print("=== AI Assistant Container Integration Test ===")
    
    # Clean up any existing container
    print("1. Cleaning up existing containers...")
    run_command(['docker', 'stop', container_name], check=False)
    run_command(['docker', 'rm', container_name], check=False)
    
    # Check if image exists
    print("2. Checking if container image exists...")
    result = run_command(['docker', 'images', '-q', image_name], check=False)
    if not result.stdout.strip():
        print(f"❌ Container image {image_name} not found!")
        print("Available images:")
        run_command(['docker', 'images'], check=False)
        return False
    
    print(f"✅ Container image {image_name} found")
    
    # Start container with test configuration
    print("3. Starting container with test configuration...")
    start_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '-p', '8080:8080',
        '-e', 'AI_MODEL_TYPE=test-mode',
        '-e', 'AI_SKIP_MODEL_DOWNLOAD=true',
        '-e', 'AI_TEST_MODE=true',
        '-e', 'AI_LOG_LEVEL=DEBUG',
        image_name
    ]
    
    result = run_command(start_cmd)
    if result.returncode != 0:
        print("❌ Failed to start container")
        return False
    
    container_id = result.stdout.strip()
    print(f"✅ Container started with ID: {container_id}")
    
    try:
        # Wait for container to be ready
        print("4. Waiting for container to be ready...")
        max_attempts = 24  # 2 minutes
        
        for i in range(max_attempts):
            time.sleep(5)
            try:
                response = requests.get('http://localhost:8080/health', timeout=10)
                if response.status_code == 200:
                    print(f"✅ Container ready after {(i+1)*5} seconds")
                    health_data = response.json()
                    print(f"Health status: {json.dumps(health_data, indent=2)}")
                    break
                else:
                    print(f"Health check returned status {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Attempt {i+1}/{max_attempts}: {e}")
                
            if i == max_attempts - 1:
                print("❌ Container failed to become ready")
                print("Container logs:")
                run_command(['docker', 'logs', '--tail', '50', container_name], check=False)
                return False
        
        # Test endpoints
        print("5. Testing endpoints...")
        
        # Test health endpoint
        try:
            response = requests.get('http://localhost:8080/health', timeout=15)
            if response.status_code == 200:
                print("✅ Health endpoint test passed")
            else:
                print(f"❌ Health endpoint returned {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health endpoint test failed: {e}")
            return False
        
        # Test root endpoint
        try:
            response = requests.get('http://localhost:8080/', timeout=15)
            if response.status_code == 200:
                print("✅ Root endpoint test passed")
                data = response.json()
                print(f"Service info: {data.get('service', 'Unknown')}")
            else:
                print(f"❌ Root endpoint returned {response.status_code}")
        except Exception as e:
            print(f"⚠️ Root endpoint test failed: {e}")
        
        # Test chat endpoint (may not work in test mode)
        try:
            response = requests.post('http://localhost:8080/chat',
                json={'message': 'test'}, timeout=30)
            if response.status_code == 200:
                print("✅ Chat endpoint test passed")
            elif response.status_code == 503:
                print("⚠️ Chat endpoint not ready (expected in test mode)")
            else:
                print(f"⚠️ Chat endpoint returned {response.status_code}")
        except Exception as e:
            print(f"⚠️ Chat endpoint test failed: {e}")
        
        # Test diagnostics endpoint
        try:
            response = requests.get('http://localhost:8080/diagnostics/tools', timeout=20)
            if response.status_code == 200:
                print("✅ Diagnostics endpoint test passed")
                data = response.json()
                tools = data.get('available_tools', data.get('tools', []))
                print(f"Available diagnostic tools: {len(tools)}")
            else:
                print(f"⚠️ Diagnostics endpoint returned {response.status_code}")
        except Exception as e:
            print(f"⚠️ Diagnostics endpoint test failed: {e}")
        
        print("✅ Integration test completed successfully!")
        return True
        
    finally:
        # Cleanup
        print("6. Cleaning up...")
        run_command(['docker', 'stop', container_name], check=False)
        run_command(['docker', 'rm', container_name], check=False)
        print("✅ Cleanup completed")

def main():
    """Main entry point"""
    if not test_container_integration():
        print("❌ Integration test failed!")
        sys.exit(1)
    else:
        print("🎉 All tests passed!")

if __name__ == "__main__":
    main()
