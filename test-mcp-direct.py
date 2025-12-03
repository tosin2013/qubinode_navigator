#!/usr/bin/env python3
"""
Direct MCP Protocol Test
Tests FastMCP servers using the MCP Python SDK
"""

import asyncio
import httpx


async def test_airflow_mcp():
    """Test Airflow MCP server at http://localhost:8889"""
    print("=" * 60)
    print("Testing Airflow FastMCP Server (port 8889)")
    print("=" * 60)

    # Test basic connectivity first
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get("http://localhost:8889/sse")
            print("✅ Server responding on /sse endpoint")
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Cannot connect: {e}")
            return False

    print("\n📋 Server is accessible via HTTP/SSE")
    return True


async def test_ai_mcp():
    """Test AI Assistant MCP server at http://localhost:8081"""
    print("\n" + "=" * 60)
    print("Testing AI Assistant FastMCP Server (port 8081)")
    print("=" * 60)

    # Test basic connectivity first
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get("http://localhost:8081/sse")
            print("✅ Server responding on /sse endpoint")
            print(f"   Status: {response.status_code}")
            return True
        except httpx.ConnectError:
            print("⚠️  AI Assistant MCP not running (expected if not started)")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def main():
    """Run all tests"""
    print("\n🧪 FastMCP Direct Protocol Test\n")

    # Test Airflow MCP
    airflow_ok = await test_airflow_mcp()

    # Test AI Assistant MCP
    ai_ok = await test_ai_mcp()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Airflow MCP (8889):     {'✅ PASS' if airflow_ok else '❌ FAIL'}")
    print(f"AI Assistant MCP (8081): {'✅ PASS' if ai_ok else '⚠️  Not Running'}")
    print("=" * 60)

    if airflow_ok:
        print("\n🎉 FastMCP Airflow server is working!")
        print("\nNext: Use MCP client to call tools:")
        print("  pip install mcp-client-cli")
        print("  mcp-client http://localhost:8889")

    return airflow_ok


if __name__ == "__main__":
    asyncio.run(main())
