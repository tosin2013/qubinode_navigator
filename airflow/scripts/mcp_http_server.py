#!/usr/bin/env python3
"""
HTTP/SSE Wrapper for Qubinode Airflow MCP Server (Fixed to match official SDK pattern)
Follows the official MCP Python SDK SSE implementation pattern
"""

import os
import sys
import logging
from typing import Optional

try:
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import Response, JSONResponse
    from starlette.requests import Request
    import uvicorn
except ImportError as e:
    print(f"Error: Missing required dependencies: {e}", file=sys.stderr)
    print("Install with: pip install mcp starlette uvicorn sse-starlette", file=sys.stderr)
    sys.exit(1)

# Import the MCP server implementation
from qubinode.mcp_server_plugin import AirflowMCPServer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("airflow-mcp-http-server")


class AirflowMCPHTTPServer:
    """HTTP/SSE server wrapper for Airflow MCP following official SDK pattern"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8889, api_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.api_key = api_key

        # Create MCP server instance
        self.mcp_server = AirflowMCPServer()

        # Create SSE transport (official pattern)
        self.sse = SseServerTransport("/messages/")

    def verify_api_key(self, request: Request) -> bool:
        """Verify API key from request headers"""
        if not self.api_key:
            return True  # No auth required if no key set

        auth_header = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        if not auth_header:
            return False

        # Support both "Bearer <key>" and direct key
        if auth_header.startswith("Bearer "):
            provided_key = auth_header[7:]
        else:
            provided_key = auth_header

        return provided_key == self.api_key

    async def health_check(self, request: Request):
        """Health check endpoint"""
        if not self.verify_api_key(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        return JSONResponse(
            {
                "status": "healthy",
                "server": "qubinode-airflow-mcp",
                "version": "1.0.0",
                "features": {
                    "dag_management": os.getenv("AIRFLOW_MCP_TOOLS_DAG_MGMT", "true"),
                    "vm_operations": os.getenv("AIRFLOW_MCP_TOOLS_VM_OPS", "true"),
                    "log_access": os.getenv("AIRFLOW_MCP_TOOLS_LOG_ACCESS", "true"),
                    "read_only": os.getenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "false"),
                },
            }
        )

    async def handle_sse(self, request: Request):
        """
        SSE endpoint handler (official SDK pattern)
        This follows the official MCP Python SDK example
        """
        # Verify API key
        if not self.verify_api_key(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        logger.info(f"New SSE connection from {request.client.host}")

        # Use official pattern: access ASGI primitives from request
        # request.scope, request.receive, and request._send are the ASGI primitives
        async with self.sse.connect_sse(
            request.scope,
            request.receive,
            request._send,  # Note: This is internal but required by SDK
        ) as (read_stream, write_stream):
            await self.mcp_server.run(
                read_stream,
                write_stream,
                self.mcp_server.create_initialization_options(),
            )

        # MUST return Response (official SDK requirement)
        return Response()

    def create_app(self):
        """Create Starlette application with official MCP SSE pattern"""
        routes = [
            Route("/health", self.health_check, methods=["GET"]),
            Route("/sse", self.handle_sse, methods=["GET"]),
            # Mount messages endpoint for client POST requests (official pattern)
            Mount("/messages/", app=self.sse.handle_post_message),
        ]

        app = Starlette(routes=routes)
        return app

    def run(self):
        """Run the HTTP server"""
        logger.info("=" * 60)
        logger.info("Starting Qubinode Airflow MCP HTTP Server (Official SDK Pattern)")
        logger.info(f"Host: {self.host}")
        logger.info(f"Port: {self.port}")
        logger.info(f"API Key Auth: {'Enabled' if self.api_key else 'Disabled'}")
        logger.info("Endpoints:")
        logger.info("  - GET  /health    - Health check")
        logger.info("  - GET  /sse       - SSE connection")
        logger.info("  - POST /messages/ - Client messages")
        logger.info("=" * 60)

        app = self.create_app()

        # Use uvicorn Config + Server to avoid event loop conflicts
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="info", loop="asyncio")
        server = uvicorn.Server(config)
        server.run()


def main():
    """Main entry point"""

    # Check if MCP is enabled
    enabled = os.getenv("AIRFLOW_MCP_ENABLED", "false").lower() == "true"

    if not enabled:
        logger.warning("=" * 60)
        logger.warning("Airflow MCP HTTP Server is DISABLED")
        logger.warning("To enable: export AIRFLOW_MCP_ENABLED=true")
        logger.warning("=" * 60)
        return

    # Get configuration
    host = os.getenv("AIRFLOW_MCP_HOST", "0.0.0.0")
    port = int(os.getenv("AIRFLOW_MCP_PORT", "8889"))
    api_key = os.getenv("AIRFLOW_MCP_API_KEY")

    if not api_key:
        logger.warning("WARNING: No API key set! Server will be accessible without authentication")
        logger.warning("Set AIRFLOW_MCP_API_KEY environment variable for security")

    # Create and run server
    server = AirflowMCPHTTPServer(host=host, port=port, api_key=api_key)
    server.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
