#!/usr/bin/env python3
"""
HTTP/SSE Wrapper for Qubinode AI Assistant MCP Server
Exposes the stdio-based MCP server over HTTP/SSE for remote access
"""

import asyncio
import os
import sys
import logging
from typing import Optional
import json
from datetime import datetime

try:
    from mcp.server import Server
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import Response, JSONResponse
    import uvicorn
except ImportError as e:
    print(f"Error: Missing required dependencies: {e}", file=sys.stderr)
    print("Install with: pip install mcp starlette uvicorn", file=sys.stderr)
    sys.exit(1)

# Import the MCP server implementation
from mcp_server import QuibinodeAIMCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp-http-server")


class MCPHTTPServer:
    """HTTP/SSE server wrapper for MCP"""

    def __init__(
        self, host: str = "0.0.0.0", port: int = 8081, api_key: Optional[str] = None
    ):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.mcp_server = None

    def verify_api_key(self, request) -> bool:
        """Verify API key from request headers"""
        if not self.api_key:
            return True  # No auth required if no key set

        auth_header = request.headers.get("X-API-Key") or request.headers.get(
            "Authorization"
        )
        if not auth_header:
            return False

        # Support both "Bearer <key>" and direct key
        if auth_header.startswith("Bearer "):
            provided_key = auth_header[7:]
        else:
            provided_key = auth_header

        return provided_key == self.api_key

    async def health_check(self, request):
        """Health check endpoint"""
        if not self.verify_api_key(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        return JSONResponse(
            {
                "status": "healthy",
                "server": "qubinode-ai-assistant-mcp",
                "version": "1.0.0",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def sse_handler(self, request):
        """SSE endpoint for MCP communication"""
        if not self.verify_api_key(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        logger.info("New SSE connection from %s", request.client.host)

        # Get base URL from environment
        base_url = os.getenv("AI_SERVICE_URL", "http://localhost:8080")

        # Create MCP server instance
        mcp_server = QuibinodeAIMCPServer(base_url=base_url)

        # Create SSE transport
        async with SseServerTransport("/messages") as (read_stream, write_stream):
            try:
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options(),
                )
            except Exception as e:
                logger.error(f"Error in MCP session: {e}", exc_info=True)
                raise

    def create_app(self):
        """Create Starlette application"""
        routes = [
            Route("/health", self.health_check, methods=["GET"]),
            Route("/sse", self.sse_handler, methods=["GET", "POST"]),
        ]

        app = Starlette(routes=routes)
        return app

    def run(self):
        """Run the HTTP server"""
        logger.info("=" * 60)
        logger.info("Starting Qubinode AI Assistant MCP HTTP Server")
        logger.info(f"Host: {self.host}")
        logger.info(f"Port: {self.port}")
        logger.info(f"API Key Auth: {'Enabled' if self.api_key else 'Disabled'}")
        logger.info("=" * 60)

        app = self.create_app()

        # Use uvicorn Config + Server to avoid event loop conflicts
        config = uvicorn.Config(
            app, host=self.host, port=self.port, log_level="info", loop="asyncio"
        )
        server = uvicorn.Server(config)
        server.run()


def main():
    """Main entry point"""

    # Check if MCP is enabled
    enabled = os.getenv("MCP_SERVER_ENABLED", "false").lower() == "true"

    if not enabled:
        logger.warning("=" * 60)
        logger.warning("MCP HTTP Server is DISABLED")
        logger.warning("To enable: export MCP_SERVER_ENABLED=true")
        logger.warning("=" * 60)
        return

    # Get configuration
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8081"))
    api_key = os.getenv("MCP_API_KEY")

    if not api_key:
        logger.warning(
            "WARNING: No API key set! Server will be accessible without authentication"
        )
        logger.warning("Set MCP_API_KEY environment variable for security")

    # Create and run server
    server = MCPHTTPServer(host=host, port=port, api_key=api_key)
    server.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
