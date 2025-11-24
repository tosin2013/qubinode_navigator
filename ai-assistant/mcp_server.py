#!/usr/bin/env python3
"""
MCP Server for Qubinode AI Assistant
Exposes RAG and AI chat capabilities to external LLMs via Model Context Protocol
"""

import asyncio
import os
import sys
import logging
from typing import Optional, Any
import httpx

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Warning: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("qubinode-mcp")


class QuibinodeAIMCPServer(Server):
    """MCP Server for AI Assistant"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        super().__init__("qubinode-ai-assistant")
        self.base_url = base_url
        self.enabled = os.getenv("MCP_SERVER_ENABLED", "false").lower() == "true"
        self.api_key = os.getenv("MCP_API_KEY")
        
        logger.info(f"Initializing Qubinode AI MCP Server")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Enabled: {self.enabled}")
        
        if self.enabled and not self.api_key:
            raise ValueError("MCP_API_KEY required when MCP_SERVER_ENABLED=true")
        
        if self.enabled:
            logger.info("MCP Server ENABLED - External LLMs can connect")
        else:
            logger.info("MCP Server DISABLED - Set MCP_SERVER_ENABLED=true to enable")
    
    async def list_tools(self) -> list[Tool]:
        """List available tools for external LLMs"""
        logger.info("Listing available MCP tools")
        
        tools = [
            Tool(
                name="query_documents",
                description="Search the RAG document store for relevant information about Qubinode, Airflow, kcli, or VM management",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for the document store"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                            "description": "Maximum number of results to return"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="chat_with_context",
                description="Send a message to the Qubinode AI assistant with optional context for intelligent responses about infrastructure, VMs, and workflows",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message or question to send to the AI assistant"
                        },
                        "context": {
                            "type": "object",
                            "description": "Additional context (e.g., current task, environment, user role)",
                            "properties": {
                                "task": {"type": "string"},
                                "environment": {"type": "string"},
                                "user_role": {"type": "string"}
                            }
                        }
                    },
                    "required": ["message"]
                }
            ),
            Tool(
                name="get_project_status",
                description="Get current Qubinode project deployment status, including service health and VM count",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]
        
        logger.info(f"Registered {len(tools)} MCP tools")
        return tools
    
    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Execute a tool requested by an external LLM"""
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        
        try:
            if name == "query_documents":
                return await self._query_documents(
                    arguments["query"],
                    arguments.get("max_results", 5)
                )
            
            elif name == "chat_with_context":
                return await self._chat_with_context(
                    arguments["message"],
                    arguments.get("context", {})
                )
            
            elif name == "get_project_status":
                return await self._get_project_status()
            
            else:
                logger.warning(f"Unknown tool requested: {name}")
                return [TextContent(
                    type="text",
                    text=f"Error: Unknown tool '{name}'"
                )]
        
        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error executing tool: {str(e)}"
            )]
    
    async def _query_documents(self, query: str, max_results: int) -> list[TextContent]:
        """Query RAG document store"""
        logger.info(f"Querying documents: '{query}' (max_results: {max_results})")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/query",
                    json={"query": query, "max_results": max_results},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                logger.info(f"Found {len(results)} results")
                
                if not results:
                    return [TextContent(
                        type="text",
                        text=f"No results found for query: '{query}'"
                    )]
                
                text = f"# Document Search Results\n\n"
                text += f"Query: {query}\n"
                text += f"Found {len(results)} results:\n\n"
                
                for i, result in enumerate(results, 1):
                    content = result.get('content', '').strip()
                    score = result.get('score', 0)
                    source = result.get('source', 'Unknown')
                    
                    text += f"## Result {i} (Score: {score:.2f})\n"
                    text += f"**Source:** {source}\n\n"
                    text += f"{content}\n\n"
                    text += "---\n\n"
                
                return [TextContent(type="text", text=text)]
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error querying documents: {str(e)}")
                return [TextContent(
                    type="text",
                    text=f"Error querying documents: {str(e)}\n\nThe AI Assistant service may not be running or accessible at {self.base_url}"
                )]
            except Exception as e:
                logger.error(f"Unexpected error querying documents: {str(e)}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Unexpected error: {str(e)}"
                )]
    
    async def _chat_with_context(self, message: str, context: dict) -> list[TextContent]:
        """Chat with AI assistant"""
        logger.info(f"Chat request: '{message[:50]}...' with context: {context}")
        
        async with httpx.AsyncClient() as client:
            try:
                # Add MCP metadata to context
                context["mcp_integration"] = True
                context["interface"] = "mcp"
                
                response = await client.post(
                    f"{self.base_url}/chat",
                    json={"message": message, "context": context},
                    timeout=90.0
                )
                response.raise_for_status()
                data = response.json()
                
                ai_response = data.get("response", "No response received")
                logger.info("Chat response received successfully")
                
                return [TextContent(
                    type="text",
                    text=ai_response
                )]
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error in chat: {str(e)}")
                return [TextContent(
                    type="text",
                    text=f"Error communicating with AI assistant: {str(e)}\n\nThe AI Assistant service may not be running or accessible at {self.base_url}"
                )]
            except Exception as e:
                logger.error(f"Unexpected error in chat: {str(e)}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Unexpected error: {str(e)}"
                )]
    
    async def _get_project_status(self) -> list[TextContent]:
        """Get project status"""
        logger.info("Fetching project status")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/status",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                status_text = "# Qubinode Navigator Project Status\n\n"
                
                # AI Assistant Status
                ai_status = data.get('ai_status', 'unknown')
                status_text += f"## AI Assistant\n"
                status_text += f"Status: **{ai_status}**\n\n"
                
                # Airflow Status
                airflow_status = data.get('airflow_status', 'unknown')
                status_text += f"## Airflow\n"
                status_text += f"Status: **{airflow_status}**\n\n"
                
                # VM Information
                vm_count = data.get('vm_count', 0)
                status_text += f"## Virtual Machines\n"
                status_text += f"Active VMs: **{vm_count}**\n\n"
                
                # Additional metrics
                if 'metrics' in data:
                    status_text += f"## Metrics\n"
                    for key, value in data['metrics'].items():
                        status_text += f"- {key}: {value}\n"
                    status_text += "\n"
                
                logger.info("Project status retrieved successfully")
                return [TextContent(type="text", text=status_text)]
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error getting status: {str(e)}")
                return [TextContent(
                    type="text",
                    text=f"Error retrieving project status: {str(e)}\n\nThe AI Assistant service may not be running or accessible at {self.base_url}"
                )]
            except Exception as e:
                logger.error(f"Unexpected error getting status: {str(e)}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Unexpected error: {str(e)}"
                )]


async def main():
    """Run MCP server"""
    
    # Check if MCP is enabled
    enabled = os.getenv("MCP_SERVER_ENABLED", "false").lower() == "true"
    
    if not enabled:
        logger.warning("=" * 60)
        logger.warning("MCP Server is DISABLED")
        logger.warning("To enable: export MCP_SERVER_ENABLED=true")
        logger.warning("=" * 60)
        return
    
    logger.info("=" * 60)
    logger.info("Starting Qubinode AI Assistant MCP Server")
    logger.info("=" * 60)
    
    # Get configuration
    base_url = os.getenv("AI_SERVICE_URL", "http://localhost:8080")
    
    try:
        server = QuibinodeAIMCPServer(base_url=base_url)
        
        # Run stdio server for local MCP clients (like Claude Desktop)
        from mcp.server.stdio import stdio_server
        
        logger.info("MCP Server ready for connections via stdio")
        logger.info("Waiting for MCP client to connect...")
        
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure 'mcp' package is installed: pip install mcp")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error starting MCP server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
